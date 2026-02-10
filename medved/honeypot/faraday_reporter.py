import asyncio
import logging

import httpx

from .config import settings
from .db import pool
from .metrics import faraday_reports_total

logger = logging.getLogger("medved.faraday")

# Severity mapping
SEVERITY_MAP = {
    "ssh_auth_attempt": "med",
    "ftp_auth_attempt": "med",
    "telnet_auth_attempt": "med",
    "http_auth_attempt": "high",
    "rdp_auth_attempt": "med",
    "smb_auth_attempt": "high",
    "connection": "info",
    "probe": "low",
    "command": "med",
    "payload": "med",
    "negotiate": "info",
    "handshake": "info",
}

UNREPORTED_EVENTS = """
SELECT source_ip::TEXT, protocol, event_type,
       COUNT(*) as cnt,
       ARRAY_AGG(DISTINCT username) FILTER (WHERE username IS NOT NULL) as usernames,
       ARRAY_AGG(DISTINCT password) FILTER (WHERE password IS NOT NULL) as passwords,
       MIN(id) as min_id, MAX(id) as max_id
FROM honeypot_events
WHERE reported_to_faraday = FALSE
GROUP BY source_ip, protocol, event_type
LIMIT 100
"""

MARK_REPORTED = """
UPDATE honeypot_events
SET reported_to_faraday = TRUE, faraday_vuln_id = $1
WHERE source_ip = $2::INET
  AND protocol = $3
  AND event_type = $4
  AND reported_to_faraday = FALSE
"""


async def report_to_faraday():
    if not settings.faraday_token:
        return

    if pool is None:
        return

    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(UNREPORTED_EVENTS)

        if not rows:
            return

        headers = {"Authorization": f"Token {settings.faraday_token}"}
        async with httpx.AsyncClient(base_url=settings.faraday_url, headers=headers, timeout=30) as client:
            ws = settings.faraday_workspace

            for row in rows:
                ip = row["source_ip"]
                protocol = row["protocol"]
                event_type = row["event_type"]
                count = row["cnt"]
                usernames = [u for u in (row["usernames"] or []) if u]
                passwords = [p for p in (row["passwords"] or []) if p]

                severity_key = f"{protocol}_{event_type}"
                severity = SEVERITY_MAP.get(severity_key, SEVERITY_MAP.get(event_type, "info"))

                # Ensure host exists
                try:
                    await client.post(f"/_api/v3/ws/{ws}/hosts/", json={"ip": ip})
                except httpx.HTTPStatusError:
                    pass  # host may already exist

                # Get host ID
                try:
                    resp = await client.get(f"/_api/v3/ws/{ws}/hosts/", params={"search": ip})
                    resp.raise_for_status()
                    hosts = resp.json().get("rows", [])
                    if not hosts:
                        continue
                    host_id = hosts[0]["id"]
                except Exception:
                    logger.warning("Could not find/create host %s in Faraday", ip)
                    continue

                # Build vuln description
                desc_parts = [f"Honeypot {protocol.upper()} {event_type} detected"]
                desc_parts.append(f"Count: {count}")
                if usernames:
                    desc_parts.append(f"Usernames: {', '.join(usernames[:20])}")
                if passwords:
                    desc_parts.append(f"Passwords: {', '.join(passwords[:20])}")

                vuln_data = {
                    "name": f"Honeypot: {protocol.upper()} {event_type}",
                    "desc": "\n".join(desc_parts),
                    "severity": severity,
                    "type": "Vulnerability",
                    "parent": host_id,
                    "parent_type": "Host",
                }

                try:
                    resp = await client.post(f"/_api/v3/ws/{ws}/vulns/", json=vuln_data)
                    resp.raise_for_status()
                    vuln_id = resp.json().get("id", 0)
                    faraday_reports_total.labels(status="success").inc()
                except Exception:
                    logger.warning("Failed to create vuln for %s/%s/%s", ip, protocol, event_type)
                    faraday_reports_total.labels(status="error").inc()
                    vuln_id = 0

                # Mark events as reported
                if vuln_id:
                    try:
                        async with pool.acquire() as conn:
                            await conn.execute(MARK_REPORTED, vuln_id, ip, protocol, event_type)
                    except Exception:
                        logger.exception("Failed to mark events as reported")

    except Exception:
        logger.exception("Faraday reporter error")


async def faraday_reporter_loop():
    logger.info("Faraday reporter started (interval: %ds)", settings.faraday_report_interval)
    while True:
        await asyncio.sleep(settings.faraday_report_interval)
        try:
            await report_to_faraday()
        except Exception:
            logger.exception("Faraday reporter loop error")
