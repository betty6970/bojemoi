import asyncpg
import logging
from datetime import datetime, timezone

from .config import settings

logger = logging.getLogger("medved.db")

pool: asyncpg.Pool | None = None

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS honeypot_events (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_ip INET NOT NULL,
    source_port INTEGER,
    dest_port INTEGER NOT NULL,
    protocol VARCHAR(16) NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    username TEXT,
    password TEXT,
    payload TEXT,
    user_agent TEXT,
    session_id VARCHAR(64),
    geo_country VARCHAR(4),
    reported_to_faraday BOOLEAN DEFAULT FALSE,
    faraday_vuln_id INTEGER,
    raw_data JSONB
);

CREATE INDEX IF NOT EXISTS idx_honeypot_source_ip ON honeypot_events (source_ip);
CREATE INDEX IF NOT EXISTS idx_honeypot_timestamp ON honeypot_events (timestamp);
CREATE INDEX IF NOT EXISTS idx_honeypot_protocol ON honeypot_events (protocol);
CREATE INDEX IF NOT EXISTS idx_honeypot_reported ON honeypot_events (reported_to_faraday)
    WHERE reported_to_faraday = FALSE;
"""

INSERT_EVENT = """
INSERT INTO honeypot_events
    (timestamp, source_ip, source_port, dest_port, protocol,
     event_type, username, password, payload, user_agent,
     session_id, raw_data)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
RETURNING id
"""


async def init_db():
    global pool
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
    logger.info("Database initialized")


async def close_db():
    global pool
    if pool:
        await pool.close()
        pool = None


async def log_event(
    source_ip: str,
    source_port: int,
    dest_port: int,
    protocol: str,
    event_type: str,
    username: str | None = None,
    password: str | None = None,
    payload: str | None = None,
    user_agent: str | None = None,
    session_id: str | None = None,
    raw_data: dict | None = None,
) -> int | None:
    if settings.is_ignored(source_ip):
        return None
    if pool is None:
        logger.warning("DB pool not initialized")
        return None
    try:
        import json
        raw_json = json.dumps(raw_data) if raw_data else None
        async with pool.acquire() as conn:
            row_id = await conn.fetchval(
                INSERT_EVENT,
                datetime.now(timezone.utc),
                source_ip,
                source_port,
                dest_port,
                protocol,
                event_type,
                username,
                password,
                payload,
                user_agent,
                session_id,
                raw_json,
            )
        return row_id
    except Exception:
        logger.exception("Failed to log event")
        return None
