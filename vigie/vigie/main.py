import asyncio
import logging
import signal
import sys

from prometheus_client import start_http_server

from vigie.config import settings
from vigie import db, feeds, matcher, alerter, metrics as _  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("vigie")

_shutdown = asyncio.Event()


def _handle_signal():
    logger.info("Shutdown signal received")
    _shutdown.set()


async def poll_loop():
    while not _shutdown.is_set():
        try:
            items = await feeds.poll_all_feeds()
            for item in items:
                matched = matcher.match_products(item)
                should = matcher.should_alert(item, matched)

                await db.insert_bulletin(
                    ref=item["ref"],
                    category=item["category"],
                    title=item["title"],
                    link=item["link"],
                    published=item["published"],
                    summary=item["summary"],
                    matched_products=matched,
                    alerted=should,
                )

                if should:
                    metrics_mod = __import__("vigie.metrics", fromlist=["matches_total"])
                    metrics_mod.matches_total.labels(category=item["category"]).inc()
                    await alerter.send_alerts(item, matched)
                    logger.info(
                        "Alerted: %s (%s) — products: %s",
                        item["ref"],
                        item["category"],
                        matched,
                    )
        except Exception:
            logger.exception("Error in poll loop")

        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=settings.poll_interval)
            break  # shutdown signalled
        except asyncio.TimeoutError:
            pass  # timeout = time to poll again


async def main():
    settings.load_secrets()

    start_http_server(settings.metrics_port)
    logger.info("Prometheus metrics on :%d", settings.metrics_port)

    await db.init_db()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal)

    poll_task = asyncio.create_task(poll_loop())
    await _shutdown.wait()

    poll_task.cancel()
    try:
        await poll_task
    except asyncio.CancelledError:
        pass

    await db.close_db()
    logger.info("Shutdown complete")
