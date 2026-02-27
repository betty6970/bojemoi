"""
faraday.py — Client Faraday API pour le MCP server.
"""

import os
import httpx

def _secret(name: str, env_var: str, default: str = "") -> str:
    path = f"/run/secrets/{name}"
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        return os.getenv(env_var, default)


FARADAY_URL = os.getenv("FARADAY_URL", "http://faraday:5985")
FARADAY_USER = os.getenv("FARADAY_USERNAME", "faraday")
FARADAY_PASS = _secret("mcp_faraday_password", "FARADAY_PASSWORD")

_session_cookie: str | None = None


async def _login(client: httpx.AsyncClient) -> bool:
    global _session_cookie
    r = await client.post(
        f"{FARADAY_URL}/_api/login",
        json={"email": FARADAY_USER, "password": FARADAY_PASS},
        timeout=10,
    )
    if r.status_code == 200:
        _session_cookie = r.cookies.get("session")
        return True
    return False


def _headers() -> dict:
    if _session_cookie:
        return {"Cookie": f"session={_session_cookie}"}
    return {}


async def _get(path: str) -> dict | list:
    async with httpx.AsyncClient(verify=False) as client:
        r = await client.get(f"{FARADAY_URL}{path}", headers=_headers(), timeout=15)
        if r.status_code == 401:
            await _login(client)
            r = await client.get(f"{FARADAY_URL}{path}", headers=_headers(), timeout=15)
        r.raise_for_status()
        return r.json()


async def _post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(verify=False) as client:
        r = await client.post(
            f"{FARADAY_URL}{path}", json=payload, headers=_headers(), timeout=15
        )
        if r.status_code == 401:
            await _login(client)
            r = await client.post(
                f"{FARADAY_URL}{path}", json=payload, headers=_headers(), timeout=15
            )
        r.raise_for_status()
        return r.json()


async def list_workspaces() -> list[dict]:
    data = await _get("/_api/v3/ws")
    rows = data if isinstance(data, list) else data.get("rows", [])
    return [
        {
            "name": w.get("name"),
            "host_count": w.get("stats", {}).get("hosts", 0),
            "vuln_count": w.get("stats", {}).get("total_vulns", 0),
        }
        for w in rows
    ]


async def get_vulns(workspace: str, severity: str = None, limit: int = 50) -> list[dict]:
    params = f"?limit={limit}"
    if severity:
        params += f"&severity={severity}"
    data = await _get(f"/_api/v3/ws/{workspace}/vulns{params}")
    vulns = data if isinstance(data, list) else data.get("vulnerabilities", [])
    return [
        {
            "id": v.get("id"),
            "name": v.get("name"),
            "severity": v.get("severity"),
            "status": v.get("status"),
            "host": v.get("host_ip") or v.get("target"),
            "service": v.get("service"),
            "description": (v.get("desc") or "")[:200],
        }
        for v in vulns[:limit]
    ]


async def add_vuln(
    workspace: str,
    host: str,
    port: int,
    name: str,
    description: str,
    severity: str = "medium",
) -> dict:
    """Ajoute une vulnérabilité dans Faraday. severity: critical|high|medium|low|info"""
    payload = {
        "name": name,
        "desc": description,
        "severity": severity,
        "status": "open",
        "type": "Vulnerability",
        "target": host,
        "service": {"port": port, "protocol": "tcp"},
    }
    return await _post(f"/_api/v3/ws/{workspace}/vulns", payload)


async def get_status() -> dict:
    try:
        workspaces = await list_workspaces()
        return {"status": "connected", "workspaces": len(workspaces)}
    except Exception as e:
        return {"status": "error", "error": str(e)}
