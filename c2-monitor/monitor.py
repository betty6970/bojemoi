#!/usr/bin/env python3
"""C2 Session Monitor — polls msfrpcd, exposes Prometheus metrics, sends Telegram alerts, creates DefectDojo findings."""
import os
import time
import logging
from pathlib import Path

import requests
from prometheus_client import start_http_server, Gauge, Counter
from pymetasploit3.msfrpc import MsfRpcClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("c2-monitor")


def _read_secret(name: str) -> str:
    v = os.getenv(name.upper(), "")
    if v:
        return v
    try:
        return Path(f"/run/secrets/{name}").read_text().strip()
    except OSError:
        return ""


def _read_config(name: str) -> str:
    try:
        return Path(f"/run/configs/{name}").read_text().strip()
    except OSError:
        return ""


# ── Config ──────────────────────────────────────────────────────────────────
MSF_HOST       = os.getenv("MSF_HOST", "msf-teamserver")
MSF_PORT       = int(os.getenv("MSF_PORT", "55553"))
POLL_INTERVAL  = int(os.getenv("POLL_INTERVAL", "30"))
METRICS_PORT   = int(os.getenv("METRICS_PORT", "9305"))
DEFECTDOJO_URL = os.getenv("DEFECTDOJO_URL", "http://defectdojo-nginx:8080")

MSF_PASSWORD        = _read_secret("msf_rpc_password")
TELEGRAM_TOKEN      = _read_secret("telegram_bot_token")
TELEGRAM_CHAT_ID    = _read_secret("telegram_alert_chat_id")
DOJO_TOKEN          = _read_secret("dojo_api_token")
PTAAS_SERIAL        = _read_config("ptaas_serial") or "c2-monitor"

# ── Prometheus metrics ───────────────────────────────────────────────────────
msf_sessions_active = Gauge(
    "msf_c2_sessions_active",
    "Number of currently active MSF sessions",
)
msf_sessions_total = Counter(
    "msf_c2_sessions_total",
    "Total MSF sessions observed since startup",
    ["payload", "target"],
)
msf_msfrpcd_up = Gauge(
    "msf_c2_msfrpcd_up",
    "1 if msfrpcd is reachable, 0 otherwise",
)


# ── Helpers ──────────────────────────────────────────────────────────────────
def send_telegram(text: str) -> None:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram credentials not configured — skipping alert")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        if not resp.ok:
            log.warning("Telegram sendMessage failed: %s", resp.text)
    except Exception as exc:
        log.warning("Telegram send error: %s", exc)


def create_dojo_finding(session_info: dict) -> None:
    if not DOJO_TOKEN:
        log.warning("DefectDojo token not configured — skipping finding")
        return
    target_ip = session_info.get("target_host", "unknown")
    payload   = session_info.get("via_payload", "unknown")
    platform  = session_info.get("platform", "unknown")
    sid       = session_info.get("id", "?")

    headers = {
        "Authorization": f"Token {DOJO_TOKEN}",
        "Content-Type": "application/json",
    }

    # Resolve engagement for product serial
    try:
        resp = requests.get(
            f"{DEFECTDOJO_URL}/api/v2/engagements/",
            headers=headers,
            params={"product__name": PTAAS_SERIAL, "status": "In Progress", "limit": 1},
            timeout=10,
        )
        results = resp.json().get("results", [])
        if not results:
            log.warning("No active engagement found for product '%s'", PTAAS_SERIAL)
            return
        engagement_id = results[0]["id"]
    except Exception as exc:
        log.warning("Failed to fetch engagement: %s", exc)
        return

    finding = {
        "title": f"C2 Session — {target_ip}",
        "description": (
            f"Active Meterpreter/MSF session opened.\n"
            f"Session ID: {sid}\n"
            f"Target: {target_ip}\n"
            f"Payload: {payload}\n"
            f"Platform: {platform}"
        ),
        "severity": "Critical",
        "engagement": engagement_id,
        "active": True,
        "verified": False,
        "numerical_severity": "S0",
        "found_by": [1],
    }
    try:
        resp = requests.post(
            f"{DEFECTDOJO_URL}/api/v2/findings/",
            headers=headers,
            json=finding,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            log.info("DefectDojo finding created for session %s → %s", sid, target_ip)
        else:
            log.warning("DefectDojo POST failed (%s): %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        log.warning("DefectDojo request error: %s", exc)


# ── Main loop ────────────────────────────────────────────────────────────────
def run() -> None:
    log.info(
        "Starting c2-monitor | MSF=%s:%s | metrics=:%s | poll=%ss",
        MSF_HOST, MSF_PORT, METRICS_PORT, POLL_INTERVAL,
    )
    start_http_server(METRICS_PORT)
    log.info("Prometheus metrics server started on :%s", METRICS_PORT)

    seen_sessions: set = set()

    while True:
        try:
            client = MsfRpcClient(MSF_PASSWORD, server=MSF_HOST, port=MSF_PORT, ssl=True)
            sessions: dict = client.sessions.list  # {id: {...}}
            msf_msfrpcd_up.set(1)

            msf_sessions_active.set(len(sessions))

            current_ids = set(sessions.keys())
            new_ids = current_ids - seen_sessions

            for sid in new_ids:
                info = sessions[sid]
                info["id"] = sid
                target_ip = info.get("target_host", "unknown")
                payload   = info.get("via_payload", "unknown")
                platform  = info.get("platform", "unknown")

                log.info(
                    "NEW SESSION %s | target=%s payload=%s platform=%s",
                    sid, target_ip, payload, platform,
                )

                # Prometheus counter
                msf_sessions_total.labels(payload=payload, target=target_ip).inc()

                # Telegram alert
                send_telegram(
                    f"🎯 <b>Nouvelle session C2</b>\n"
                    f"Session ID: <code>{sid}</code>\n"
                    f"Target: <code>{target_ip}</code>\n"
                    f"Payload: <code>{payload}</code>\n"
                    f"Platform: <code>{platform}</code>"
                )

                # DefectDojo finding
                create_dojo_finding(info)

            seen_sessions = current_ids

        except Exception as exc:
            log.warning("msfrpcd unreachable: %s", exc)
            msf_msfrpcd_up.set(0)
            msf_sessions_active.set(0)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run()
