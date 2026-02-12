import asyncio
import logging

from .config import settings
from . import db
from .alerter import format_alert, send_alerts
from .metrics import buzz_clusters_detected_total

logger = logging.getLogger("razvedka.scorer")

BUZZ_QUERY = """
SELECT
    target,
    COUNT(*) AS mention_count,
    COUNT(DISTINCT channel) AS channel_count,
    ARRAY_AGG(DISTINCT channel) AS channels,
    AVG(score_intention) AS avg_intention,
    AVG(score_france) AS avg_france,
    ARRAY_AGG(DISTINCT temporalite) FILTER (WHERE temporalite IS NOT NULL) AS time_markers
FROM (
    SELECT
        UNNEST(entites_cibles) AS target,
        channel,
        score_intention,
        score_france,
        temporalite
    FROM buzz_log
    WHERE timestamp > NOW() - INTERVAL '6 hours'
      AND score_france > 0.5
      AND score_intention > 5
) sub
GROUP BY target
HAVING COUNT(DISTINCT channel) >= $1
   AND COUNT(*) >= $2
ORDER BY mention_count DESC
LIMIT 20
"""


async def check_buzz() -> list[dict]:
    """Query for buzz clusters and return alerts."""
    if db.pool is None:
        return []

    try:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                BUZZ_QUERY,
                settings.alert_channel_threshold,
                settings.alert_mention_threshold,
            )

        alerts = []
        for row in rows:
            alert = format_alert(
                target=row["target"],
                mention_count=row["mention_count"],
                channel_count=row["channel_count"],
                channels=list(row["channels"]),
                avg_intention=float(row["avg_intention"]),
                avg_france=float(row["avg_france"]),
                time_markers=[t for t in (row["time_markers"] or []) if t],
            )
            alerts.append(alert)

        return alerts

    except Exception:
        logger.exception("Buzz query failed")
        return []


async def buzz_scorer_loop():
    """Periodic loop to check for buzz clusters and send alerts."""
    logger.info(
        "Buzz scorer started (interval=%dm, channel_threshold=%d, mention_threshold=%d)",
        settings.buzz_check_interval,
        settings.alert_channel_threshold,
        settings.alert_mention_threshold,
    )
    while True:
        await asyncio.sleep(settings.buzz_check_interval * 60)
        try:
            alerts = await check_buzz()
            if alerts:
                buzz_clusters_detected_total.inc(len(alerts))
                logger.warning("Detected %d buzz clusters", len(alerts))
                for alert in alerts:
                    await send_alerts(alert)
            else:
                logger.debug("No buzz clusters detected")
        except Exception:
            logger.exception("Buzz scorer loop error")
