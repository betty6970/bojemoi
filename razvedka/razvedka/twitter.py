import asyncio
import logging

import tweepy

from .config import settings
from . import db
from .extractor import extract_intelligence
from .metrics import (
    messages_received_total,
    messages_processed_total,
    france_mentions_total,
    intention_score_histogram,
    france_score_histogram,
)

logger = logging.getLogger("razvedka.twitter")


async def process_tweet(text: str, channel_name: str, tweet_id: int | None):
    """Extract intelligence from a tweet and store in DB."""
    if not text:
        return

    messages_received_total.labels(channel=channel_name).inc()

    result = extract_intelligence(text)

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
        message_id=tweet_id,
        raw_entities=result.raw_entities if result.raw_entities else None,
        source="twitter",
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


def _build_query(accounts: list[str], search_queries: list[str]) -> str:
    """Build a single OR query combining account timelines and search terms."""
    parts = []
    for acct in accounts:
        parts.append(f"from:{acct}")
    for q in search_queries:
        parts.append(f"({q})")
    return " OR ".join(parts)


async def twitter_poll_loop():
    """Poll X/Twitter API for new tweets from monitored accounts and searches."""
    if not settings.twitter_bearer_token:
        logger.info("Twitter bearer token not configured, X polling disabled")
        return

    client = tweepy.Client(bearer_token=settings.twitter_bearer_token, wait_on_rate_limit=True)

    accounts = [a.strip() for a in settings.twitter_accounts.split(",") if a.strip()]
    search_queries = [q.strip() for q in settings.twitter_search_queries.split("|") if q.strip()]

    if not accounts and not search_queries:
        logger.warning("No Twitter accounts or search queries configured")
        return

    query = _build_query(accounts, search_queries)
    # Twitter API v2 query max 512 chars
    if len(query) > 512:
        logger.warning("Twitter query truncated from %d to 512 chars", len(query))
        query = query[:512]

    since_id = None
    interval = settings.twitter_poll_interval

    logger.info(
        "Twitter poller started: %d accounts, %d searches, interval=%ds",
        len(accounts), len(search_queries), interval,
    )

    while True:
        try:
            response = await asyncio.to_thread(
                client.search_recent_tweets,
                query=query,
                since_id=since_id,
                max_results=100,
                tweet_fields=["author_id", "created_at"],
                expansions=["author_id"],
                user_fields=["username"],
            )

            if response.data:
                # Build author_id -> username map
                users_map = {}
                if response.includes and "users" in response.includes:
                    for user in response.includes["users"]:
                        users_map[user.id] = user.username

                for tweet in response.data:
                    username = users_map.get(tweet.author_id, str(tweet.author_id))
                    channel_name = f"x:@{username}"
                    await process_tweet(tweet.text, channel_name, tweet.id)

                    if since_id is None or tweet.id > since_id:
                        since_id = tweet.id

                logger.info("Processed %d tweets (since_id=%s)", len(response.data), since_id)

        except tweepy.TooManyRequests:
            logger.warning("Twitter rate limited, backing off 60s")
            await asyncio.sleep(60)
            continue
        except asyncio.CancelledError:
            logger.info("Twitter poller cancelled")
            raise
        except Exception:
            logger.exception("Twitter poll error")

        await asyncio.sleep(interval)
