import logging
import asyncio
from datetime import datetime, timezone

import httpx

from .config import settings
from .metrics import alerts_sent_total

logger = logging.getLogger("razvedka.alerter")


def format_alert(
    target: str,
    mention_count: int,
    channel_count: int,
    channels: list[str],
    avg_intention: float,
    avg_france: float,
    time_markers: list[str],
) -> dict:
    """Format a buzz alert into a structured dict."""
    return {
        "target": target,
        "mention_count": mention_count,
        "channel_count": channel_count,
        "channels": channels,
        "avg_intention_score": round(avg_intention, 2),
        "avg_france_score": round(avg_france, 2),
        "time_markers": time_markers,
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }


def _format_telegram_text(alert: dict) -> str:
    """Format alert as Telegram message text."""
    lines = [
        "🚨 <b>RAZVEDKA BUZZ ALERT</b>",
        "",
        f"🎯 <b>Target:</b> {alert['target']}",
        f"📊 <b>Mentions:</b> {alert['mention_count']} across {alert['channel_count']} channels",
        f"📡 <b>Channels:</b> {', '.join(alert['channels'])}",
        f"⚡ <b>Intention score:</b> {alert['avg_intention_score']}",
        f"🇫🇷 <b>France score:</b> {alert['avg_france_score']}",
    ]
    if alert["time_markers"]:
        lines.append(f"🕐 <b>Time indicators:</b> {', '.join(alert['time_markers'])}")
    lines.append(f"\n🕐 {alert['detected_at']}")
    return "\n".join(lines)


async def send_telegram_alert(alert: dict) -> bool:
    """Send alert via Telegram Bot API."""
    if not settings.telegram_bot_token or not settings.telegram_alert_chat_id:
        return False
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_alert_chat_id,
        "text": _format_telegram_text(alert),
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        alerts_sent_total.labels(channel_type="telegram", status="success").inc()
        logger.info("Telegram alert sent for %s", alert["target"])
        return True
    except Exception:
        alerts_sent_total.labels(channel_type="telegram", status="error").inc()
        logger.exception("Failed to send Telegram alert")
        return False


async def send_alertmanager_alert(alert: dict) -> bool:
    """Send alert to Alertmanager webhook."""
    if not settings.alertmanager_webhook_url:
        return False
    payload = [{
        "labels": {
            "alertname": "RazvedkaBuzz",
            "severity": "warning",
            "target": alert["target"],
            "service": "razvedka",
        },
        "annotations": {
            "summary": f"DDoS buzz detected for {alert['target']}",
            "description": (
                f"{alert['mention_count']} mentions across "
                f"{alert['channel_count']} channels. "
                f"Intention: {alert['avg_intention_score']}, "
                f"France: {alert['avg_france_score']}"
            ),
        },
        "generatorURL": "http://razvedka:9300/metrics",
    }]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(settings.alertmanager_webhook_url, json=payload)
            resp.raise_for_status()
        alerts_sent_total.labels(channel_type="alertmanager", status="success").inc()
        logger.info("Alertmanager alert sent for %s", alert["target"])
        return True
    except Exception:
        alerts_sent_total.labels(channel_type="alertmanager", status="error").inc()
        logger.exception("Failed to send Alertmanager alert")
        return False


async def send_webhook_alert(alert: dict) -> bool:
    """Send alert to custom webhook."""
    if not settings.custom_webhook_url:
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(settings.custom_webhook_url, json=alert)
            resp.raise_for_status()
        alerts_sent_total.labels(channel_type="webhook", status="success").inc()
        logger.info("Webhook alert sent for %s", alert["target"])
        return True
    except Exception:
        alerts_sent_total.labels(channel_type="webhook", status="error").inc()
        logger.exception("Failed to send webhook alert")
        return False


async def send_alerts(alert: dict):
    """Send alert to all configured channels."""
    await asyncio.gather(
        send_telegram_alert(alert),
        send_alertmanager_alert(alert),
        send_webhook_alert(alert),
        return_exceptions=True,
    )
