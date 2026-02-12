import asyncpg
import json
import logging
from datetime import datetime, timezone

from .config import settings

logger = logging.getLogger("razvedka.db")

pool: asyncpg.Pool | None = None

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS buzz_log (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    channel TEXT NOT NULL,
    langue TEXT,
    entites_cibles TEXT[],
    pays TEXT[],
    mots_intention TEXT[],
    temporalite TEXT,
    score_intention FLOAT NOT NULL DEFAULT 0,
    score_france FLOAT NOT NULL DEFAULT 0,
    message_id BIGINT,
    raw_entities JSONB
);

CREATE INDEX IF NOT EXISTS idx_buzz_timestamp ON buzz_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_buzz_france ON buzz_log (score_france)
    WHERE score_france > 0;
CREATE INDEX IF NOT EXISTS idx_buzz_intention ON buzz_log (score_intention)
    WHERE score_intention > 0;
CREATE INDEX IF NOT EXISTS idx_buzz_channel ON buzz_log (channel);
"""

INSERT_BUZZ = """
INSERT INTO buzz_log
    (timestamp, channel, langue, entites_cibles, pays, mots_intention,
     temporalite, score_intention, score_france, message_id, raw_entities)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
RETURNING id
"""


async def _ensure_database():
    """Create the razvedka database if it doesn't exist."""
    try:
        sys_conn = await asyncpg.connect(
            host=settings.pg_host,
            port=settings.pg_port,
            user=settings.pg_user,
            password=settings.pg_password,
            database="postgres",
        )
        try:
            exists = await sys_conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                settings.pg_database,
            )
            if not exists:
                await sys_conn.execute(
                    f'CREATE DATABASE "{settings.pg_database}"'
                )
                logger.info("Created database %s", settings.pg_database)
        finally:
            await sys_conn.close()
    except Exception:
        logger.exception("Failed to ensure database exists")
        raise


async def init_db():
    global pool
    await _ensure_database()
    pool = await asyncpg.create_pool(
        host=settings.pg_host,
        port=settings.pg_port,
        user=settings.pg_user,
        password=settings.pg_password,
        database=settings.pg_database,
        min_size=2,
        max_size=10,
    )
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLE)
    logger.info("Database initialized (host=%s, db=%s)", settings.pg_host, settings.pg_database)


async def close_db():
    global pool
    if pool:
        await pool.close()
        pool = None


async def insert_buzz(
    channel: str,
    langue: str | None,
    entites_cibles: list[str],
    pays: list[str],
    mots_intention: list[str],
    temporalite: str | None,
    score_intention: float,
    score_france: float,
    message_id: int | None,
    raw_entities: dict | None = None,
) -> int | None:
    if pool is None:
        logger.warning("DB pool not initialized")
        return None
    try:
        raw_json = json.dumps(raw_entities) if raw_entities else None
        async with pool.acquire() as conn:
            row_id = await conn.fetchval(
                INSERT_BUZZ,
                datetime.now(timezone.utc),
                channel,
                langue,
                entites_cibles,
                pays,
                mots_intention,
                temporalite,
                score_intention,
                score_france,
                message_id,
                raw_json,
            )
        return row_id
    except Exception:
        logger.exception("Failed to insert buzz")
        return None
