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

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import redis

app = FastAPI(title="Nuclei API", version="1.0.0")

# Configuration
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
RESULTS_DIR = Path(os.environ.get('RESULTS_DIR', '/results'))
RESULTS_DIR.mkdir(exist_ok=True)

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
                for line in f:
                    if line.strip():
                        findings_count += 1

        # Met à jour le statut final
        r.hset(f'nuclei:scan:{scan_id}', mapping={
            'status': 'completed',
            'findings_count': findings_count,
            'output_file': str(output_file),
            'completed_at': datetime.now().isoformat()
        })

        # Publie le résultat
        r.publish('pentest:results', json.dumps({
            'tool': 'nuclei',
            'scan_id': scan_id,
            'target': target,
            'status': 'completed',
            'findings_count': findings_count
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
