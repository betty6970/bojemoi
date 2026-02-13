import asyncpg
import logging

from vigie.config import settings

logger = logging.getLogger(__name__)

pool: asyncpg.Pool | None = None

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS certfr_bulletins (
    id SERIAL PRIMARY KEY,
    ref TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    link TEXT NOT NULL,
    published TIMESTAMPTZ NOT NULL,
    summary TEXT,
    matched_products TEXT[],
    alerted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_certfr_published ON certfr_bulletins (published DESC);
CREATE INDEX IF NOT EXISTS idx_certfr_category ON certfr_bulletins (category);
CREATE INDEX IF NOT EXISTS idx_certfr_alerted ON certfr_bulletins (alerted) WHERE NOT alerted;
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


async def ref_exists(ref: str) -> bool:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM certfr_bulletins WHERE ref = $1)", ref
        )


async def insert_bulletin(
    ref: str,
    category: str,
    title: str,
    link: str,
    published,
    summary: str | None,
    matched_products: list[str],
    alerted: bool,
):
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO certfr_bulletins
               (ref, category, title, link, published, summary, matched_products, alerted)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
               ON CONFLICT (ref) DO NOTHING""",
            ref,
            category,
            title,
            link,
            published,
            summary,
            matched_products,
            alerted,
        )
