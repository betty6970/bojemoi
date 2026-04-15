import asyncio
import logging
import datetime

import httpx

from .config import settings
from . import db
from .metrics import dojo_reports_total

logger = logging.getLogger("medved.defectdojo")

# Severity mapping: honeypot event type → DefectDojo severity
SEVERITY_MAP = {
    "ssh_auth_attempt": "Medium",
    "ftp_auth_attempt": "Medium",
    "telnet_auth_attempt": "Medium",
    "http_auth_attempt": "High",
    "rdp_auth_attempt": "Medium",
    "smb_auth_attempt": "High",
    "connection": "Info",
    "probe": "Low",
    "command": "Medium",
    "payload": "Medium",
    "negotiate": "Info",
    "handshake": "Info",
}

UNREPORTED_EVENTS = """
SELECT source_ip::TEXT, protocol, event_type,
       COUNT(*) as cnt,
       ARRAY_AGG(DISTINCT username) FILTER (WHERE username IS NOT NULL) as usernames,
       ARRAY_AGG(DISTINCT password) FILTER (WHERE password IS NOT NULL) as passwords,
       MIN(id) as min_id, MAX(id) as max_id
FROM honeypot_events
WHERE reported_to_dojo = FALSE
GROUP BY source_ip, protocol, event_type
LIMIT 100
"""

MARK_REPORTED = """
UPDATE honeypot_events
SET reported_to_dojo = TRUE, dojo_finding_id = $1
WHERE source_ip = $2::INET
  AND protocol = $3
  AND event_type = $4
  AND reported_to_dojo = FALSE
"""

# Cache: product/engagement/test IDs pour le product honeypot
_dojo_test_id: int | None = None


def _headers() -> dict:
    token = settings.defectdojo_token
    if token:
        return {"Authorization": f"Token {token}"}
    return {}


async def _ensure_test(client: httpx.AsyncClient) -> int | None:
    """Retourne l'ID du test DefectDojo pour les honeypot findings. Crée la hiérarchie si nécessaire."""
    global _dojo_test_id
    if _dojo_test_id is not None:
        return _dojo_test_id

    base = settings.defectdojo_url
    product_name = settings.defectdojo_product

    try:
        # Get or create product
        r = await client.get(f"{base}/api/v2/products/", params={"name": product_name})
        r.raise_for_status()
        products = r.json().get("results", [])
        if products:
            product_id = products[0]["id"]
        else:
            r2 = await client.get(f"{base}/api/v2/product_types/", params={"limit": 1})
            r2.raise_for_status()
            types = r2.json().get("results", [])
            prod_type_id = types[0]["id"] if types else 1
            r3 = await client.post(f"{base}/api/v2/products/", json={
                "name": product_name,
                "description": "Honeypot events",
                "prod_type": prod_type_id,
            })
            r3.raise_for_status()
            product_id = r3.json()["id"]

        # Get or create engagement
        r = await client.get(f"{base}/api/v2/engagements/",
                              params={"product": product_id, "name": "honeypot"})
        r.raise_for_status()
        engagements = r.json().get("results", [])
        if engagements:
            engagement_id = engagements[0]["id"]
        else:
            today = str(datetime.date.today())
            r2 = await client.post(f"{base}/api/v2/engagements/", json={
                "name": "honeypot",
                "product": product_id,
                "target_start": today,
                "target_end": today,
                "status": "In Progress",
                "engagement_type": "Interactive",
            })
            r2.raise_for_status()
            engagement_id = r2.json()["id"]

        # Get or create test
        r = await client.get(f"{base}/api/v2/tests/",
                              params={"engagement": engagement_id, "title": "honeypot"})
        r.raise_for_status()
        tests = r.json().get("results", [])
        if tests:
            _dojo_test_id = tests[0]["id"]
        else:
            r2 = await client.get(f"{base}/api/v2/test_types/", params={"name": "Manual"})
            r2.raise_for_status()
            types = r2.json().get("results", [])
            test_type_id = types[0]["id"] if types else 1
            today = str(datetime.date.today())
            r3 = await client.post(f"{base}/api/v2/tests/", json={
                "title": "honeypot",
                "engagement": engagement_id,
                "test_type": test_type_id,
                "target_start": today,
                "target_end": today,
            })
            r3.raise_for_status()
            _dojo_test_id = r3.json()["id"]

        return _dojo_test_id

    except Exception:
        logger.exception("Failed to ensure DefectDojo product/engagement/test hierarchy")
        return None


async def report_to_defectdojo():
    if not settings.defectdojo_token:
        return

    if db.pool is None:
        return

    try:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(UNREPORTED_EVENTS)

        if not rows:
            return

        async with httpx.AsyncClient(
            base_url=settings.defectdojo_url,
            headers=_headers(),
            verify=False,
            timeout=30,
        ) as client:
            test_id = await _ensure_test(client)
            if test_id is None:
                logger.warning("Cannot get DefectDojo test_id — skipping report")
                return

            for row in rows:
                ip = row["source_ip"]
                protocol = row["protocol"]
                event_type = row["event_type"]
                count = row["cnt"]
                usernames = [u for u in (row["usernames"] or []) if u]
                passwords = [p for p in (row["passwords"] or []) if p]

                severity_key = f"{protocol}_{event_type}"
                severity = SEVERITY_MAP.get(severity_key, SEVERITY_MAP.get(event_type, "Info"))

                desc_parts = [f"Honeypot {protocol.upper()} {event_type} detected"]
                desc_parts.append(f"Source IP: {ip}")
                desc_parts.append(f"Event count: {count}")
                if usernames:
                    desc_parts.append(f"Usernames: {', '.join(usernames[:20])}")
                if passwords:
                    desc_parts.append(f"Passwords: {', '.join(passwords[:20])}")

                finding_data = {
                    "title": f"Honeypot: {protocol.upper()} {event_type} from {ip}",
                    "description": "\n".join(desc_parts),
                    "severity": severity,
                    "active": True,
                    "verified": False,
                    "false_p": False,
                    "risk_accepted": False,
                    "test": test_id,
                }

                finding_id = 0
                should_mark = False
                try:
                    resp = await client.post("/api/v2/findings/", json=finding_data)
                    if resp.status_code in (200, 201):
                        finding_id = resp.json().get("id", 0)
                        dojo_reports_total.labels(status="success").inc()
                        logger.info("Reported %s %s from %s (finding_id=%d)", protocol, event_type, ip, finding_id)
                        should_mark = True
                    elif resp.status_code == 400:
                        # Possible duplicate — mark as reported anyway
                        dojo_reports_total.labels(status="success").inc()
                        should_mark = True
                    else:
                        logger.warning("DefectDojo POST %s for %s/%s/%s: %s",
                                       resp.status_code, ip, protocol, event_type, resp.text[:100])
                        dojo_reports_total.labels(status="error").inc()
                except Exception:
                    logger.warning("Failed to create finding for %s/%s/%s", ip, protocol, event_type)
                    dojo_reports_total.labels(status="error").inc()

                if should_mark:
                    try:
                        async with db.pool.acquire() as conn:
                            await conn.execute(MARK_REPORTED, finding_id, ip, protocol, event_type)
                    except Exception:
                        logger.exception("Failed to mark events as reported")

    except Exception:
        logger.exception("DefectDojo reporter error")


async def defectdojo_reporter_loop():
    logger.info("DefectDojo reporter started (interval: %ds)", settings.defectdojo_report_interval)
    while True:
        await asyncio.sleep(settings.defectdojo_report_interval)
        try:
            await report_to_defectdojo()
        except Exception:
            logger.exception("DefectDojo reporter loop error")
