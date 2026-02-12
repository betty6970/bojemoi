import asyncio
import logging
import signal
import sys

from prometheus_client import start_http_server
from telethon import TelegramClient, events

from .config import settings
from . import db
from .extractor import extract_intelligence
from .scorer import buzz_scorer_loop
from .metrics import (
    messages_received_total,
    messages_processed_total,
    france_mentions_total,
    intention_score_histogram,
    france_score_histogram,
    active_channels,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("razvedka.main")

_shutdown = asyncio.Event()


def _handle_signal():
    logger.info("Shutdown signal received")
    _shutdown.set()


async def process_message(event, channel_name: str):
    """Extract intelligence from a message and store in DB."""
    text = event.raw_text
    if not text:
        return

    messages_received_total.labels(channel=channel_name).inc()

    result = extract_intelligence(text)

    # Skip messages with no signal
    if result.score_intention == 0 and result.score_france == 0 and not result.entities_targets:
        return

    messages_processed_total.labels(
        channel=channel_name,
        language=result.language or "unknown",
    ).inc()
    intention_score_histogram.observe(result.score_intention)
    france_score_histogram.observe(result.score_france)

    if result.score_france > 0:
        france_mentions_total.labels(channel=channel_name).inc()

    row_id = await db.insert_buzz(
        channel=channel_name,
        langue=result.language,
        entites_cibles=result.entities_targets,
        pays=result.countries,
        mots_intention=result.intention_keywords,
        temporalite=result.temporality,
        score_intention=result.score_intention,
        score_france=result.score_france,
        message_id=event.message.id if event.message else None,
        raw_entities=result.raw_entities if result.raw_entities else None,
    )

    if row_id and result.score_france > 0.5:
        logger.info(
            "HIGH SIGNAL [%s] lang=%s france=%.2f intention=%.1f targets=%s",
            channel_name,
            result.language,
            result.score_france,
            result.score_intention,
            result.entities_targets[:5],
        )


async def main():
    settings.load_secrets()

    if not settings.telegram_api_id or not settings.telegram_api_hash:
        logger.error("Telegram API credentials not configured")
        sys.exit(1)

    # Start Prometheus metrics server
    start_http_server(settings.metrics_port)
    logger.info("Prometheus metrics on :%d", settings.metrics_port)

    # Initialize database
    await db.init_db()

    # Create Telegram client
    client = TelegramClient(
        "/data/razvedka",
        settings.telegram_api_id,
        settings.telegram_api_hash,
    )
    # Non-interactive auth: if TELEGRAM_CODE is set, use it; otherwise prompt
    import os
    telegram_code = os.environ.get("TELEGRAM_CODE", "")

    if telegram_code:
        await client.start(
            phone=settings.telegram_phone,
            code_callback=lambda: telegram_code,
        )
    else:
        await client.start(phone=settings.telegram_phone)
    logger.info("Telegram client connected")

    # Resolve and join channels
    channel_names = [c.strip() for c in settings.telegram_channels.split(",") if c.strip()]
    channel_entities = {}

    for name in channel_names:
        try:
            entity = await client.get_entity(name)
            channel_entities[entity.id] = name
            logger.info("Monitoring channel: %s (id=%d)", name, entity.id)
        except Exception:
            logger.warning("Failed to resolve channel: %s", name)

    active_channels.set(len(channel_entities))

    if not channel_entities:
        logger.error("No channels resolved, exiting")
        await client.disconnect()
        await db.close_db()
        sys.exit(1)

    # Register message handler
    @client.on(events.NewMessage(chats=list(channel_entities.keys())))
    async def handler(event):
        chat_id = event.chat_id
        channel_name = channel_entities.get(chat_id, str(chat_id))
        try:
            await process_message(event, channel_name)
        except Exception:
            logger.exception("Error processing message from %s", channel_name)

    # Start scorer
    scorer_task = asyncio.create_task(buzz_scorer_loop())

    # Register signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal)

    logger.info("Razvedka running - monitoring %d channels", len(channel_entities))

    # Wait for shutdown
    await _shutdown.wait()

    logger.info("Shutting down...")
    scorer_task.cancel()
    try:
        await scorer_task
    except asyncio.CancelledError:
        pass
    await client.disconnect()
    await db.close_db()
    logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
