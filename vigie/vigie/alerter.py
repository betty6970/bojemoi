import asyncio
import html
import logging

import httpx

from vigie.config import settings
from vigie.metrics import alerts_sent_total

logger = logging.getLogger(__name__)

SEVERITY_MAP = {
    "alerte": "critical",
    "avis": "warning",
    "ioc": "info",
}

EMOJI_MAP = {
    "alerte": "\U0001f6a8",  # 🚨
    "avis": "\U0001f6e1\ufe0f",  # 🛡️
    "ioc": "\U0001f50d",  # 🔍
}


async def send_telegram_alert(item: dict, matched: list[str]) -> bool:
    if not settings.telegram_bot_token or not settings.telegram_alert_chat_id:
        return False

    emoji = EMOJI_MAP.get(item["category"], "\U0001f4cb")
    products_str = ", ".join(matched) if matched else "\u2014"
    title = html.escape(item["title"])
    text = (
        f"{emoji} <b>CERT-FR {item['category'].upper()}</b>\n"
        f"\U0001f4cb {item['ref']}\n"
        f"\U0001f3f7\ufe0f Produits : {products_str}\n"
        f"\U0001f4dd {title}\n"
        f"\U0001f517 {item['link']}"
    )

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
        alerts_sent_total.labels(channel="telegram", status="success").inc()
        return True
    except Exception:
        logger.exception("Telegram alert failed for %s", item["ref"])
        alerts_sent_total.labels(channel="telegram", status="error").inc()
        return False


async def send_alertmanager_alert(item: dict, matched: list[str]) -> bool:
    if not settings.alertmanager_webhook_url:
        return False

    severity = SEVERITY_MAP.get(item["category"], "info")
    payload = [
        {
            "labels": {
                "alertname": "CertFR",
                "severity": severity,
                "ref": item["ref"],
                "category": item["category"],
                "service": "vigie",
            },
            "annotations": {
                "summary": item["title"],
                "description": (
                    f"CERT-FR {item['category']} {item['ref']}: {item['title']}"
                ),
                "products": ", ".join(matched) if matched else "",
                "link": item["link"],
            },
            "generatorURL": f"http://vigie:{settings.metrics_port}/metrics",
        }
    ]

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                settings.alertmanager_webhook_url, json=payload
            )
            resp.raise_for_status()
        alerts_sent_total.labels(channel="alertmanager", status="success").inc()
        return True
    except Exception:
        logger.exception("Alertmanager alert failed for %s", item["ref"])
        alerts_sent_total.labels(channel="alertmanager", status="error").inc()
        return False


async def send_alerts(item: dict, matched: list[str]):
    await asyncio.gather(
        send_telegram_alert(item, matched),
        send_alertmanager_alert(item, matched),
        return_exceptions=True,
    )
