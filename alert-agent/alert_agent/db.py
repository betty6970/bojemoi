import asyncpg
import json
import logging

from .config import settings

logger = logging.getLogger("alert_agent.db")

pool: asyncpg.Pool | None = None

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS alert_agent_actions (
    id SERIAL PRIMARY KEY,
    alert_name TEXT NOT NULL,
    service_name TEXT,
    severity TEXT,
    llm_decision JSONB,
    action_taken TEXT,
    dry_run BOOLEAN DEFAULT TRUE,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_alert_agent_created
    ON alert_agent_actions (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_agent_service
    ON alert_agent_actions (service_name, created_at DESC);
"""


async def _ensure_database():
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
    logger.info("Database initialized")


async def close_db():
    global pool
    if pool:
        await pool.close()
        pool = None


async def log_action(
    alert_name: str,
    service_name: str | None,
    severity: str | None,
    llm_decision: dict | None,
    action_taken: str,
    dry_run: bool,
    success: bool,
    error_message: str | None = None,
):
    if not pool:
        logger.warning("DB pool not initialized, skipping log")
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO alert_agent_actions
                   (alert_name, service_name, severity, llm_decision,
                    action_taken, dry_run, success, error_message)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                alert_name,
                service_name,
                severity,
                json.dumps(llm_decision) if llm_decision else None,
                action_taken,
                dry_run,
                success,
                error_message,
            )
    except Exception:
        logger.exception("Failed to log action to DB")
