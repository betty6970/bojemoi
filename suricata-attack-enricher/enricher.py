"""
Suricata ATT&CK Enricher - Tails eve.json, maps alerts to MITRE ATT&CK, stores in PostgreSQL.
"""

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path

import asyncpg

from bojemoi_mitre_attack.mappings.suricata import map_suricata_alert

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Configuration
EVE_JSON_PATH = os.environ.get('EVE_JSON_PATH', '/var/log/suricata/eve.json')
DB_HOST = os.environ.get('DB_HOST', '192.168.1.76')
DB_PORT = int(os.environ.get('DB_PORT', '5432'))
DB_NAME = os.environ.get('DB_NAME', 'bojemoi_threat_intel')
DB_USER = os.environ.get('DB_USER', 'bojemoi')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
BATCH_SIZE = int(os.environ.get('BATCH_SIZE', '50'))
FLUSH_INTERVAL = float(os.environ.get('FLUSH_INTERVAL', '5.0'))

INIT_SQL = """
CREATE TABLE IF NOT EXISTS suricata_attack_alerts (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    src_ip INET,
    dest_ip INET,
    src_port INT,
    dest_port INT,
    proto VARCHAR(10),
    signature TEXT,
    signature_id INT,
    category TEXT,
    severity INT,
    attack_technique_id VARCHAR(20),
    attack_technique_name TEXT,
    attack_tactic TEXT,
    attack_confidence VARCHAR(10),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_saa_timestamp ON suricata_attack_alerts(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_saa_technique ON suricata_attack_alerts(attack_technique_id);
CREATE INDEX IF NOT EXISTS idx_saa_tactic ON suricata_attack_alerts(attack_tactic);
"""

INSERT_SQL = """
INSERT INTO suricata_attack_alerts (
    timestamp, src_ip, dest_ip, src_port, dest_port, proto,
    signature, signature_id, category, severity,
    attack_technique_id, attack_technique_name, attack_tactic, attack_confidence
) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
"""

shutdown = False


def handle_signal(sig, frame):
    global shutdown
    logger.info(f"Received signal {sig}, shutting down...")
    shutdown = True


signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)


async def init_db(pool: asyncpg.Pool):
    """Create the table and indexes if they don't exist."""
    async with pool.acquire() as conn:
        await conn.execute(INIT_SQL)
    logger.info("Database initialized")


async def flush_batch(pool: asyncpg.Pool, batch: list):
    """Insert a batch of enriched alerts into PostgreSQL."""
    if not batch:
        return
    async with pool.acquire() as conn:
        await conn.executemany(INSERT_SQL, batch)
    logger.info(f"Flushed {len(batch)} enriched alerts to database")


async def tail_eve_json(path: str):
    """
    Async generator that tails eve.json, yielding new lines.
    Starts from the end of the file and follows new writes.
    """
    p = Path(path)

    # Wait for the file to exist
    while not p.exists():
        if shutdown:
            return
        logger.info(f"Waiting for {path} to appear...")
        await asyncio.sleep(5)

    with open(p, 'r') as f:
        # Seek to end
        f.seek(0, 2)
        logger.info(f"Tailing {path} from offset {f.tell()}")

        while not shutdown:
            line = f.readline()
            if line:
                yield line.strip()
            else:
                await asyncio.sleep(0.5)


def parse_alert(line: str) -> dict | None:
    """Parse an eve.json line and return alert data if it's an alert event."""
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None

    if event.get('event_type') != 'alert':
        return None

    alert = event.get('alert', {})
    return {
        'timestamp': event.get('timestamp'),
        'src_ip': event.get('src_ip'),
        'dest_ip': event.get('dest_ip'),
        'src_port': event.get('src_port'),
        'dest_port': event.get('dest_port'),
        'proto': event.get('proto'),
        'signature': alert.get('signature'),
        'signature_id': alert.get('signature_id'),
        'category': alert.get('category', ''),
        'severity': alert.get('severity', 3),
    }


def enrich_alert(alert: dict) -> tuple | None:
    """Map a parsed alert to ATT&CK and return an INSERT-ready tuple."""
    mapping = map_suricata_alert(
        category=alert['category'],
        signature=alert.get('signature', ''),
        severity=alert.get('severity', 3),
    )

    if not mapping:
        return None

    return (
        alert['timestamp'],
        alert['src_ip'],
        alert['dest_ip'],
        alert.get('src_port'),
        alert.get('dest_port'),
        alert.get('proto'),
        alert.get('signature'),
        alert.get('signature_id'),
        alert.get('category'),
        alert.get('severity'),
        mapping.technique_id,
        mapping.technique_name,
        mapping.tactic,
        mapping.confidence,
    )


async def main():
    logger.info("Suricata ATT&CK Enricher starting")
    logger.info(f"EVE path: {EVE_JSON_PATH}, DB: {DB_HOST}:{DB_PORT}/{DB_NAME}")

    # Read DB password from file if available (Docker secrets)
    db_password = DB_PASSWORD
    password_file = os.environ.get('DB_PASSWORD_FILE')
    if password_file and os.path.exists(password_file):
        with open(password_file) as f:
            db_password = f.read().strip()

    pool = await asyncpg.create_pool(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=db_password,
        min_size=1, max_size=3,
    )

    await init_db(pool)

    batch = []
    last_flush = asyncio.get_event_loop().time()
    total_processed = 0
    total_enriched = 0

    async for line in tail_eve_json(EVE_JSON_PATH):
        alert = parse_alert(line)
        if not alert:
            continue

        total_processed += 1
        row = enrich_alert(alert)
        if row:
            batch.append(row)
            total_enriched += 1

        now = asyncio.get_event_loop().time()
        if len(batch) >= BATCH_SIZE or (batch and now - last_flush >= FLUSH_INTERVAL):
            try:
                await flush_batch(pool, batch)
            except Exception as e:
                logger.error(f"Failed to flush batch: {e}")
            batch.clear()
            last_flush = now

            if total_processed % 1000 == 0:
                logger.info(f"Stats: processed={total_processed}, enriched={total_enriched}")

    # Final flush
    if batch:
        try:
            await flush_batch(pool, batch)
        except Exception as e:
            logger.error(f"Failed final flush: {e}")

    await pool.close()
    logger.info(f"Shutdown complete. Total: processed={total_processed}, enriched={total_enriched}")


if __name__ == '__main__':
    asyncio.run(main())
