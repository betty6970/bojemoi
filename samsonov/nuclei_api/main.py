#!/usr/bin/env python3
"""
API Nuclei pour l'orchestrateur
Permet de lancer des scans Nuclei via HTTP/Redis
"""

import os
import re
import json
import shutil
import subprocess
import tempfile
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlparse

from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
import redis
from nuclei_ai import NucleiAI
import requests as http_requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="Nuclei API", version="1.0.0")


def _read_secret(name, legacy_env=None):
    """Read sensitive value: legacy env var → NAME env var → /run/secrets/name file."""
    if legacy_env:
        v = os.environ.get(legacy_env, "")
        if v:
            return v
    v = os.environ.get(name.upper(), "")
    if v:
        return v
    try:
        with open(f"/run/secrets/{name}") as f:
            return f.read().strip()
    except OSError:
        return ""


# Configuration
REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
RESULTS_DIR = Path(os.environ.get('RESULTS_DIR', '/results'))
RESULTS_DIR.mkdir(exist_ok=True)

# Nym Mixnet proxy (SOCKS5) — optionnel, activé via NYM_PROXY env var
NUCLEI_PROXY = os.environ.get('NUCLEI_PROXY', '') or os.environ.get('NYM_PROXY', '')

# DefectDojo configuration
DEFECTDOJO_URL = os.environ.get('DEFECTDOJO_URL', 'http://defectdojo-nginx:8080').rstrip('/')
DEFECTDOJO_TOKEN = _read_secret("dojo_api_token", "DEFECTDOJO_TOKEN")
DEFECTDOJO_PRODUCT = os.environ.get('DEFECTDOJO_PRODUCT', 'nuclei')

# Redis client
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

ai = NucleiAI()


class ScanRequest(BaseModel):
    target: str
    severity: Optional[str] = "critical,high,medium"
    tags: Optional[str] = None
    templates: Optional[List[str]] = None
    timeout: Optional[int] = 600
    scan_details: Optional[dict] = None


class ScanResult(BaseModel):
    scan_id: str
    target: str
    status: str
    findings_count: int = 0
    dojo_imported: int = 0
    output_file: Optional[str] = None


def _extract_ip(target: str) -> str:
    """Extrait l'IP/hostname d'une URL ou IP brute"""
    if target.startswith(('http://', 'https://')):
        return urlparse(target).hostname or target
    return target.split('/')[0]


_SEVERITY_MAP = {
    'critical': 'critical', 'high': 'high',
    'medium': 'medium', 'low': 'low', 'info': 'info'
}

_NUCLEI_NUM_SEV = {
    'critical': 'S0', 'high': 'S1', 'medium': 'S2', 'low': 'S3', 'info': 'S4'
}

_CVE_RE = re.compile(r'CVE-\d{4}-\d+', re.I)


def _dojo_headers() -> dict:
    if DEFECTDOJO_TOKEN:
        return {"Authorization": f"Token {DEFECTDOJO_TOKEN}"}
    return {}


def _dojo_get_or_create_test(session: http_requests.Session) -> tuple[int, int, int] | tuple[None, None, None]:
    """Retourne (test_id, test_type_id, product_id) pour le product nuclei. Crée la hiérarchie si nécessaire."""
    base = DEFECTDOJO_URL
    headers = _dojo_headers()

    try:
        import datetime
        # Product
        r = session.get(f"{base}/api/v2/products/", headers=headers, params={"name": DEFECTDOJO_PRODUCT}, timeout=10)
        r.raise_for_status()
        products = r.json().get("results", [])
        if products:
            product_id = products[0]["id"]
        else:
            r2 = session.get(f"{base}/api/v2/product_types/", headers=headers, params={"limit": 1}, timeout=10)
            r2.raise_for_status()
            types = r2.json().get("results", [])
            prod_type_id = types[0]["id"] if types else 1
            r3 = session.post(f"{base}/api/v2/products/", headers=headers, json={
                "name": DEFECTDOJO_PRODUCT, "description": "Nuclei scans", "prod_type": prod_type_id,
            }, timeout=10)
            r3.raise_for_status()
            product_id = r3.json()["id"]

        # Engagement
        r = session.get(f"{base}/api/v2/engagements/", headers=headers,
                        params={"product": product_id, "name": "nuclei"}, timeout=10)
        r.raise_for_status()
        engagements = r.json().get("results", [])
        if engagements:
            engagement_id = engagements[0]["id"]
        else:
            today = str(datetime.date.today())
            r2 = session.post(f"{base}/api/v2/engagements/", headers=headers, json={
                "name": "nuclei", "product": product_id,
                "target_start": today, "target_end": today,
                "status": "In Progress", "engagement_type": "Interactive",
            }, timeout=10)
            r2.raise_for_status()
            engagement_id = r2.json()["id"]

        # Test type (Nuclei Scan ou Manual)
        r2 = session.get(f"{base}/api/v2/test_types/", headers=headers, params={"name": "Nuclei Scan"}, timeout=10)
        r2.raise_for_status()
        types = r2.json().get("results", [])
        if not types:
            r2 = session.get(f"{base}/api/v2/test_types/", headers=headers, params={"name": "Manual"}, timeout=10)
            r2.raise_for_status()
            types = r2.json().get("results", [])
        test_type_id = types[0]["id"] if types else 1

        # Test
        r = session.get(f"{base}/api/v2/tests/", headers=headers,
                        params={"engagement": engagement_id, "title": "nuclei"}, timeout=10)
        r.raise_for_status()
        tests = r.json().get("results", [])
        if tests:
            return tests[0]["id"], test_type_id, product_id
        today = str(datetime.date.today())
        r3 = session.post(f"{base}/api/v2/tests/", headers=headers, json={
            "title": "nuclei", "engagement": engagement_id, "test_type": test_type_id,
            "target_start": today, "target_end": today,
        }, timeout=10)
        r3.raise_for_status()
        return r3.json()["id"], test_type_id, product_id

    except Exception:
        return None, None, None


def _dojo_get_or_create_endpoint(session: http_requests.Session, host: str, product_id: int) -> int | None:
    """Retourne l'ID de l'endpoint DefectDojo pour un host/product. Crée si nécessaire."""
    base = DEFECTDOJO_URL
    headers = _dojo_headers()
    try:
        r = session.get(f"{base}/api/v2/endpoints/", headers=headers,
                        params={"host": host, "product": product_id}, timeout=10)
        r.raise_for_status()
        results = r.json().get("results", [])
        if results:
            return results[0]["id"]
        r2 = session.post(f"{base}/api/v2/endpoints/", headers=headers,
                          json={"host": host, "product": product_id}, timeout=10)
        if r2.status_code in (200, 201):
            return r2.json()["id"]
    except Exception:
        pass
    return None


def push_to_defectdojo(findings: list, target: str) -> int:
    """Pousse les findings Nuclei vers DefectDojo. Retourne le nombre importé."""
    if not findings or not DEFECTDOJO_TOKEN:
        return 0

    try:
        session = http_requests.Session()
        session.verify = False
        headers = _dojo_headers()

        test_id, test_type_id, product_id = _dojo_get_or_create_test(session)
        if not test_id:
            return 0

        ip = _extract_ip(target)
        endpoint_id = _dojo_get_or_create_endpoint(session, ip, product_id)
        imported = 0

        for finding in findings:
            info = finding.get('info', {})
            severity = info.get('severity', 'info').lower()

            desc = info.get('description', '')
            remediation = info.get('remediation', '')
            if remediation:
                desc = f"{desc}\n\nRemediation: {remediation}".strip()

            req = finding.get('request', '')
            resp_raw = finding.get('response', '')
            evidence_parts = []
            if req:
                evidence_parts.append(f"Request:\n{req[:2000]}")
            if resp_raw:
                evidence_parts.append(f"Response:\n{resp_raw[:1000]}")
            if evidence_parts:
                desc = f"{desc}\n\n{'---'.join(evidence_parts)}"

            raw_refs = info.get('reference', [])
            if isinstance(raw_refs, str):
                raw_refs = [raw_refs]
            cve_ids = [m for ref in raw_refs for m in _CVE_RE.findall(ref)]

            vuln_data = {
                'title': info.get('name', finding.get('template-id', 'Nuclei Finding')),
                'description': desc or "No description",
                'severity': _SEVERITY_MAP.get(severity, 'info').capitalize(),
                'numerical_severity': _NUCLEI_NUM_SEV.get(severity, 'S4'),
                'found_by': [test_type_id],
                'active': True,
                'verified': False,
                'false_p': False,
                'risk_accepted': False,
                'test': test_id,
            }
            if endpoint_id:
                vuln_data['endpoints'] = [endpoint_id]
            if cve_ids:
                vuln_data['cve'] = cve_ids[0]

            resp = session.post(
                f"{DEFECTDOJO_URL}/api/v2/findings/",
                headers=headers, json=vuln_data, timeout=10
            )
            if resp.status_code in (200, 201):
                imported += 1

        return imported

    except Exception:
        return 0


def run_nuclei_scan(scan_id: str, target: str, severity: str, tags: str = None, scan_details: dict = None):
    """Exécute un scan Nuclei en arrière-plan"""
    output_file = RESULTS_DIR / f"{scan_id}.json"

    # Pre-scan: generate AI custom templates
    tmpl_dir = None
    ai_templates = ai.generate_templates(scan_details) if scan_details else []
    if ai_templates:
        tmpl_dir = Path(tempfile.mkdtemp(prefix='nuclei-ai-'))
        for i, yaml_str in enumerate(ai_templates):
            (tmpl_dir / f'ai-template-{i}.yaml').write_text(yaml_str)

    cmd = [
        'nuclei',
        '-u', target,
        '-severity', severity,
        '-json-export', str(output_file),
        '-silent',
        '-nc'
    ]

    if NUCLEI_PROXY:
        cmd.extend(['-proxy', NUCLEI_PROXY])

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

        # Run AI template scan and append results to output_file
        if tmpl_dir:
            try:
                ai_out = RESULTS_DIR / f"{scan_id}-ai.json"
                ai_cmd = ['nuclei', '-u', target, '-t', str(tmpl_dir),
                          '-json-export', str(ai_out), '-silent', '-nc']
                if NUCLEI_PROXY:
                    ai_cmd.extend(['-proxy', NUCLEI_PROXY])
                subprocess.run(
                    ai_cmd,
                    capture_output=True, text=True, timeout=300
                )
                if ai_out.exists():
                    with open(output_file, 'a') as fout:
                        with open(ai_out) as fin:
                            for line in fin:
                                stripped = line.strip()
                                if stripped and stripped not in ('[]', '{}', '[][]'):
                                    fout.write(line)
                    ai_out.unlink(missing_ok=True)
            except Exception as e:
                log.warning(f'AI template scan failed: {e}')
            finally:
                shutil.rmtree(str(tmpl_dir), ignore_errors=True)
                tmpl_dir = None

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
                            stripped = line.strip()
                            if stripped and stripped not in ('[]', '{}', '[][]'):
                                try:
                                    json.loads(stripped)
                                    findings_count += 1
                                except json.JSONDecodeError:
                                    pass

        # Import vers DefectDojo
        dojo_imported = 0
        ai_json = ''
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
            dojo_imported = push_to_defectdojo(all_findings, target)
            # AI triage (fire-and-forget, does not block import)
            severity_counts = {}
            for f in all_findings:
                sev = f.get('info', {}).get('severity', 'info').lower()
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            ai_result = ai.analyze_findings(_extract_ip(target), all_findings, severity_counts)
            ai_json = json.dumps(ai_result) if ai_result else ''

        # Met à jour le statut final
        r.hset(f'nuclei:scan:{scan_id}', mapping={
            'status': 'completed',
            'findings_count': findings_count,
            'output_file': str(output_file),
            'completed_at': datetime.now().isoformat(),
            'dojo_imported': dojo_imported,
            'dojo_product': DEFECTDOJO_PRODUCT,
            'ai_analysis': ai_json
        })

        # Publie le résultat
        r.publish('pentest:results', json.dumps({
            'tool': 'nuclei',
            'scan_id': scan_id,
            'target': target,
            'status': 'completed',
            'findings_count': findings_count,
            'dojo_imported': dojo_imported
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
        request.tags,
        request.scan_details
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
        dojo_imported=int(scan_data.get('dojo_imported', 0)),
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
