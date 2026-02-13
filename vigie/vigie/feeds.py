import re
import logging
from datetime import datetime, timezone
from time import mktime

import feedparser

from vigie.config import settings
from vigie import db, metrics

logger = logging.getLogger(__name__)

REF_PATTERN = re.compile(r"(CERTFR-\d{4}-(?:ALE|AVI|IOC)-\d{3,})")


def _extract_ref(link: str, title: str) -> str | None:
    m = REF_PATTERN.search(link) or REF_PATTERN.search(title)
    return m.group(1) if m else None


def _extract_category(ref: str) -> str:
    if "-ALE-" in ref:
        return "alerte"
    if "-AVI-" in ref:
        return "avis"
    if "-IOC-" in ref:
        return "ioc"
    return "unknown"


def _parse_published(entry) -> datetime:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime.fromtimestamp(
            mktime(entry.published_parsed), tz=timezone.utc
        )
    return datetime.now(timezone.utc)


async def poll_feed(feed_url: str) -> list[dict]:
    """Poll a single RSS feed and return new (unseen) items."""
    feed_label = feed_url.rstrip("/").rsplit("/", 2)[-2]  # alerte, avis, ioc
    metrics.polls_total.labels(feed=feed_label).inc()
    metrics.last_poll_timestamp.labels(feed=feed_label).set(
        datetime.now(timezone.utc).timestamp()
    )

    try:
        parsed = feedparser.parse(feed_url)
    except Exception:
        logger.exception("Failed to parse feed %s", feed_url)
        return []

    if parsed.bozo and not parsed.entries:
        logger.warning("Feed %s returned no entries (bozo=%s)", feed_url, parsed.bozo_exception)
        return []

    new_items = []
    for entry in parsed.entries:
        ref = _extract_ref(entry.get("link", ""), entry.get("title", ""))
        if not ref:
            continue

        if await db.ref_exists(ref):
            continue

        category = _extract_category(ref)
        summary = entry.get("summary", "") or ""
        # Strip HTML tags from summary
        summary = re.sub(r"<[^>]+>", "", summary).strip()

        item = {
            "ref": ref,
            "category": category,
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "published": _parse_published(entry),
            "summary": summary[:2000],
        }
        new_items.append(item)
        metrics.items_total.labels(feed=feed_label, category=category).inc()

    logger.info("Feed %s: %d new items", feed_label, len(new_items))
    return new_items


async def poll_all_feeds() -> list[dict]:
    all_items = []
    for url in settings.get_feed_urls():
        items = await poll_feed(url)
        all_items.extend(items)
    return all_items
