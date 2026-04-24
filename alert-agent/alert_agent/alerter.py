import logging

import httpx

from .config import settings

logger = logging.getLogger("alert_agent.alerter")


async def send_telegram_alert(
    alert_name: str,
    service_name: str | None,
    severity: str | None,
    decision: dict,
    action_taken: str,
    dry_run: bool,
    success: bool,
) -> bool:
    """Send a Telegram notification about the action taken."""
    if not settings.telegram_bot_token or not settings.telegram_alert_chat_id:
        return False

    dry_tag = " [DRY-RUN]" if dry_run else ""
    status_emoji = "\u2705" if success else "\u274c"

    lines = [
        f"\U0001f916 <b>Alert-Agent{dry_tag}</b>",
        "",
        f"\U0001f514 <b>Alert:</b> {alert_name}",
    ]
    if service_name:
        lines.append(f"\u2699\ufe0f <b>Service:</b> {service_name}")
    if severity:
        lines.append(f"\u26a0\ufe0f <b>Severity:</b> {severity}")
    lines.append(f"\U0001f9e0 <b>LLM decision:</b> {decision.get('action', 'unknown')}")
    if decision.get("reason"):
        lines.append(f"\U0001f4ac <b>Reason:</b> {decision['reason']}")
    lines.append(f"{status_emoji} <b>Action:</b> {action_taken}")

    text = "\n".join(lines)

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_alert_chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        logger.info("Telegram alert sent for %s", alert_name)
        return True
    except Exception:
        logger.exception("Failed to send Telegram alert")
        return False
