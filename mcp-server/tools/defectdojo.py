"""
defectdojo.py — Client DefectDojo API v2 pour le MCP server.
Auth: Token {token} (plus simple que les cookies Faraday)
"""

import os
import datetime
import httpx


def _secret(name: str, env_var: str, default: str = "") -> str:
    try:
        with open(f"/run/secrets/{name}") as f:
            return f.read().strip()
    except FileNotFoundError:
        return os.getenv(env_var, default)


DOJO_URL = os.getenv("DEFECTDOJO_URL", "http://defectdojo-nginx:8080").rstrip("/")
DOJO_TOKEN = _secret("mcp_dojo_token", "DEFECTDOJO_TOKEN")


def _headers() -> dict:
    if DOJO_TOKEN:
        return {"Authorization": f"Token {DOJO_TOKEN}"}
    return {}


async def _get(path: str, params: dict = None) -> dict:
    async with httpx.AsyncClient(verify=False) as client:
        r = await client.get(f"{DOJO_URL}{path}", headers=_headers(), params=params or {}, timeout=15)
        r.raise_for_status()
        return r.json()


async def _post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(verify=False) as client:
        r = await client.post(f"{DOJO_URL}{path}", headers=_headers(), json=payload, timeout=15)
        r.raise_for_status()
        return r.json()


async def list_products() -> list[dict]:
    """Liste les products DefectDojo avec leur nombre de findings."""
    data = await _get("/api/v2/products/", {"limit": 100})
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "findings_count": p.get("findings_count", 0),
            "description": (p.get("description") or "")[:100],
        }
        for p in data.get("results", [])
    ]


async def get_findings(
    product_id: int = None,
    severity: str = None,
    limit: int = 50,
) -> list[dict]:
    """Récupère les findings DefectDojo. Filtre optionnel: product_id, severity."""
    params = {"limit": limit, "active": "true"}
    if product_id:
        params["product"] = product_id
    if severity:
        params["severity"] = severity.capitalize()
    data = await _get("/api/v2/findings/", params)
    return [
        {
            "id": f["id"],
            "title": f["title"],
            "severity": f["severity"],
            "active": f["active"],
            "risk_accepted": f["risk_accepted"],
            "false_positive": f.get("false_p", False),
            "product": f.get("test_object", {}).get("engagement", {}).get("product_name", ""),
            "endpoint_count": f.get("endpoint_count", 0),
            "description": (f.get("description") or "")[:200],
        }
        for f in data.get("results", [])[:limit]
    ]


async def _get_or_create_product(client: httpx.AsyncClient, product_name: str) -> int:
    """Retourne l'ID du product, le crée si nécessaire."""
    r = await client.get(f"{DOJO_URL}/api/v2/products/", headers=_headers(), params={"name": product_name})
    r.raise_for_status()
    results = r.json().get("results", [])
    if results:
        return results[0]["id"]
    # Récupérer le premier product type disponible
    r2 = await client.get(f"{DOJO_URL}/api/v2/product_types/", headers=_headers(), params={"limit": 1})
    r2.raise_for_status()
    types = r2.json().get("results", [])
    prod_type_id = types[0]["id"] if types else 1
    r3 = await client.post(f"{DOJO_URL}/api/v2/products/", headers=_headers(), json={
        "name": product_name,
        "description": product_name,
        "prod_type": prod_type_id,
    })
    r3.raise_for_status()
    return r3.json()["id"]


async def _get_or_create_engagement(client: httpx.AsyncClient, product_id: int, name: str = "manual") -> int:
    """Retourne l'ID de l'engagement, le crée si nécessaire."""
    r = await client.get(f"{DOJO_URL}/api/v2/engagements/", headers=_headers(),
                         params={"product": product_id, "name": name})
    r.raise_for_status()
    results = r.json().get("results", [])
    if results:
        return results[0]["id"]
    today = str(datetime.date.today())
    r2 = await client.post(f"{DOJO_URL}/api/v2/engagements/", headers=_headers(), json={
        "name": name,
        "product": product_id,
        "target_start": today,
        "target_end": today,
        "status": "In Progress",
        "engagement_type": "Interactive",
    })
    r2.raise_for_status()
    return r2.json()["id"]


async def _get_or_create_test(client: httpx.AsyncClient, engagement_id: int, name: str = "manual") -> int:
    """Retourne l'ID du test, le crée si nécessaire."""
    r = await client.get(f"{DOJO_URL}/api/v2/tests/", headers=_headers(),
                         params={"engagement": engagement_id, "title": name})
    r.raise_for_status()
    results = r.json().get("results", [])
    if results:
        return results[0]["id"]
    # Chercher un test type "Manual Code Review" ou similaire
    r2 = await client.get(f"{DOJO_URL}/api/v2/test_types/", headers=_headers(), params={"name": "Manual"})
    r2.raise_for_status()
    types = r2.json().get("results", [])
    test_type_id = types[0]["id"] if types else 1
    today = str(datetime.date.today())
    r3 = await client.post(f"{DOJO_URL}/api/v2/tests/", headers=_headers(), json={
        "title": name,
        "engagement": engagement_id,
        "test_type": test_type_id,
        "target_start": today,
        "target_end": today,
    })
    r3.raise_for_status()
    return r3.json()["id"]


async def add_finding(
    product_name: str,
    host: str,
    port: int,
    name: str,
    description: str,
    severity: str = "Medium",
) -> dict:
    """
    Ajoute un finding dans DefectDojo.
    Crée le product/engagement/test si nécessaire.
    severity: Critical|High|Medium|Low|Info
    """
    async with httpx.AsyncClient(verify=False, timeout=20) as client:
        product_id = await _get_or_create_product(client, product_name)
        engagement_id = await _get_or_create_engagement(client, product_id, "manual")
        test_id = await _get_or_create_test(client, engagement_id, "manual")

        r = await client.post(f"{DOJO_URL}/api/v2/findings/", headers=_headers(), json={
            "title": name,
            "description": f"{description}\n\nHost: {host}:{port}",
            "severity": severity.capitalize(),
            "active": True,
            "verified": False,
            "false_p": False,
            "risk_accepted": False,
            "test": test_id,
        })
        r.raise_for_status()
        result = r.json()
        return {"id": result["id"], "title": result["title"], "severity": result["severity"]}


async def get_status() -> dict:
    try:
        products = await list_products()
        return {"status": "connected", "products": len(products)}
    except Exception as e:
        return {"status": "error", "error": str(e)}
