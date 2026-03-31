#!/usr/bin/env python3
"""
API Nuclei pour l'orchestrateur
Permet de lancer des scans Nuclei via HTTP/Redis
"""

import os
import json
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlparse

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import redis
import requests as http_requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="Nuclei API", version="1.0.0")

# Configuration
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
RESULTS_DIR = Path(os.environ.get('RESULTS_DIR', '/results'))
RESULTS_DIR.mkdir(exist_ok=True)

# Faraday configuration
FARADAY_URL = os.environ.get('FARADAY_URL', 'https://faraday.bojemoi.lab').rstrip('/')
FARADAY_USER = os.environ.get('FARADAY_USER', 'faraday')
FARADAY_PASSWORD = os.environ.get('FARADAY_PASSWORD', 'bojemoi2')
FARADAY_WORKSPACE = os.environ.get('FARADAY_WORKSPACE', 'default')

# Redis client
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


class ScanRequest(BaseModel):
    target: str
    severity: Optional[str] = "critical,high,medium"
    tags: Optional[str] = None
    templates: Optional[List[str]] = None
    timeout: Optional[int] = 600


class ScanResult(BaseModel):
    scan_id: str
    target: str
    status: str
    findings_count: int = 0
    output_file: Optional[str] = None


def _extract_ip(target: str) -> str:
    """Extrait l'IP/hostname d'une URL ou IP brute"""
    if target.startswith(('http://', 'https://')):
        return urlparse(target).hostname or target
    return target.split('/')[0]


_SEVERITY_MAP = {
    'critical': 'critical', 'high': 'high',
    'medium': 'med', 'low': 'low', 'info': 'info'
}


def push_to_faraday(findings: list, target: str) -> int:
    """Pousse les findings Nuclei vers Faraday. Retourne le nombre importé."""
    if not findings:
        return 0

    try:
        session = http_requests.Session()
        session.verify = False

        # Authentification
        resp = session.post(
            f"{FARADAY_URL}/_api/login",
            json={"email": FARADAY_USER, "password": FARADAY_PASSWORD},
            timeout=10
        )
        if resp.status_code != 200:
            return 0

        ip = _extract_ip(target)

        # Créer ou récupérer le host
        resp = session.post(
            f"{FARADAY_URL}/_api/v3/ws/{FARADAY_WORKSPACE}/hosts",
            json={"ip": ip, "hostnames": [], "description": "Nuclei scan"},
            timeout=10
        )
        host_id = None
        if resp.status_code in (200, 201):
            host_id = resp.json().get('id')
        else:
            resp = session.get(
                f"{FARADAY_URL}/_api/v3/ws/{FARADAY_WORKSPACE}/hosts",
                params={"search": ip}, timeout=10
            )
            if resp.status_code == 200:
                for row in resp.json().get('rows', []):
                    if row.get('value', {}).get('ip') == ip:
                        host_id = row.get('id')
                        break

        if not host_id:
            return 0

        imported = 0
        for finding in findings:
            info = finding.get('info', {})
            severity = info.get('severity', 'info').lower()
            vuln = {
                'name': info.get('name', finding.get('template-id', 'Nuclei Finding')),
                'desc': info.get('description', ''),
                'severity': _SEVERITY_MAP.get(severity, 'info'),
                'type': 'Vulnerability',
                'parent': host_id,
                'parent_type': 'Host',
                'path': finding.get('matched-at', ''),
                'refs': info.get('reference', []) if isinstance(info.get('reference'), list) else [],
                'tags': info.get('tags', []) if isinstance(info.get('tags'), list) else [],
                'external_id': finding.get('template-id', '')
            }
            resp = session.post(
                f"{FARADAY_URL}/_api/v3/ws/{FARADAY_WORKSPACE}/vulns",
                json=vuln, timeout=10
            )
            if resp.status_code in (200, 201):
                imported += 1

        return imported

    except Exception:
        return 0


def run_nuclei_scan(scan_id: str, target: str, severity: str, tags: str = None):
    """Exécute un scan Nuclei en arrière-plan"""
    output_file = RESULTS_DIR / f"{scan_id}.json"

    cmd = [
        'nuclei',
        '-u', target,
        '-severity', severity,
        '-json-export', str(output_file),
        '-silent',
        '-nc'
    ]

    if tags:
        cmd.extend(['-tags', tags])

    try:
        # Met à jour le statut
        r.hset(f'nuclei:scan:{scan_id}', mapping={
            'status': 'running',
            'target': target,
            'started_at': datetime.now().isoformat()
        })

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800
        )

        # Compte les findings
        findings_count = 0
        if output_file.exists():
            with open(output_file, 'r') as f:
                content = f.read().strip()
                if content:
                    try:
                        data = json.loads(content)
                        if isinstance(data, list):
                            findings_count = len(data)
                        else:
                            findings_count = 1
                    except json.JSONDecodeError:
                        # JSONL format (one JSON per line)
                        for line in content.split('\n'):
                            if line.strip() and line.strip() not in ('[]', '{}'):
                                findings_count += 1

        # Import vers Faraday
        faraday_imported = 0
        if findings_count > 0:
            all_findings = []
            if output_file.exists():
                with open(output_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            try:
                                all_findings.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
            faraday_imported = push_to_faraday(all_findings, target)

        # Met à jour le statut final
        r.hset(f'nuclei:scan:{scan_id}', mapping={
            'status': 'completed',
            'findings_count': findings_count,
            'output_file': str(output_file),
            'completed_at': datetime.now().isoformat(),
            'faraday_imported': faraday_imported,
            'faraday_workspace': FARADAY_WORKSPACE
        })

        # Publie le résultat
        r.publish('pentest:results', json.dumps({
            'tool': 'nuclei',
            'scan_id': scan_id,
            'target': target,
            'status': 'completed',
            'findings_count': findings_count,
            'faraday_imported': faraday_imported
        }))

    except subprocess.TimeoutExpired:
        r.hset(f'nuclei:scan:{scan_id}', mapping={
            'status': 'timeout',
            'error': 'Scan timeout (30 min)'
        })
    except Exception as e:
        r.hset(f'nuclei:scan:{scan_id}', mapping={
            'status': 'error',
            'error': str(e)
        })


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "nuclei-api"}


@app.post("/scan", response_model=ScanResult)
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """Lance un scan Nuclei"""
    scan_id = f"nuclei_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Enregistre le scan
    r.hset(f'nuclei:scan:{scan_id}', mapping={
        'status': 'pending',
        'target': request.target,
        'created_at': datetime.now().isoformat()
    })

    # Lance le scan en arrière-plan
    background_tasks.add_task(
        run_nuclei_scan,
        scan_id,
        request.target,
        request.severity,
        request.tags
    )

    return ScanResult(
        scan_id=scan_id,
        target=request.target,
        status="pending"
    )


@app.get("/scan/{scan_id}", response_model=ScanResult)
async def get_scan_status(scan_id: str):
    """Récupère le statut d'un scan"""
    scan_data = r.hgetall(f'nuclei:scan:{scan_id}')

    if not scan_data:
        raise HTTPException(status_code=404, detail="Scan not found")

    return ScanResult(
        scan_id=scan_id,
        target=scan_data.get('target', ''),
        status=scan_data.get('status', 'unknown'),
        findings_count=int(scan_data.get('findings_count', 0)),
        output_file=scan_data.get('output_file')
    )


@app.get("/scan/{scan_id}/results")
async def get_scan_results(scan_id: str):
    """Récupère les résultats d'un scan"""
    scan_data = r.hgetall(f'nuclei:scan:{scan_id}')

    if not scan_data:
        raise HTTPException(status_code=404, detail="Scan not found")

    output_file = scan_data.get('output_file')
    if not output_file or not Path(output_file).exists():
        raise HTTPException(status_code=404, detail="Results not available")

    findings = []
    with open(output_file, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    findings.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    return {
        "scan_id": scan_id,
        "target": scan_data.get('target'),
        "findings": findings
    }


@app.get("/scans")
async def list_scans():
    """Liste tous les scans"""
    scan_keys = r.keys('nuclei:scan:*')
    scans = []

    for key in scan_keys:
        scan_id = key.replace('nuclei:scan:', '')
        scan_data = r.hgetall(key)
        scans.append({
            'scan_id': scan_id,
            'target': scan_data.get('target'),
            'status': scan_data.get('status'),
            'created_at': scan_data.get('created_at')
        })

    return scans


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
