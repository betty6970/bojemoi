from __future__ import annotations

import asyncio
import logging
import signal
import time

from prometheus_client import start_http_server

from .config import settings
from .feeds import download_feeds
from .metrics import last_update_timestamp
from .rules import generate_rules, reload_suricata, write_rules

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("dozor")

_shutdown = asyncio.Event()


def _handle_signal() -> None:
    log.info("shutdown signal received")
    _shutdown.set()


async def poll_once() -> None:
    """Download feeds, generate rules, write file, reload Suricata."""
    feeds = settings.get_feeds()
    feed_data = await download_feeds(feeds)

    if not feed_data:
        log.warning("no feeds returned data — skipping rule generation")
        return

    rules_text = generate_rules(feed_data)
    write_rules(rules_text, settings.rules_output_path)
    last_update_timestamp.set(time.time())

    reload_suricata(settings.suricata_socket_path)


async def main() -> None:
    log.info("dozor starting — poll_interval=%ds", settings.poll_interval)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal)

    start_http_server(settings.metrics_port)
    log.info("prometheus metrics on :%d", settings.metrics_port)

    while not _shutdown.is_set():
        try:
            await poll_once()
        except Exception:
            log.exception("poll cycle failed")

        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=settings.poll_interval)
        except asyncio.TimeoutError:
            pass

    log.info("dozor stopped")
