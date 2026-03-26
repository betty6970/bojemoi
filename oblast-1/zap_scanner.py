#!/usr/bin/env python3
"""
ZAP Scanner v2
Architecture: Redis queue + zap_scan_log + Faraday export
- DbFeeder thread: charge les hosts web non scannés → Redis queue
- ScanWorker: dépile la queue, soumet à ZAP (N scans concurrents),
  enregistre dans zap_scan_log, exporte vers Faraday
"""
import os
import sys
import time
import json
import logging
import threading
import psycopg2
import psycopg2.extras
import redis
import requests
from typing import Dict, List, Optional

logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

PG_HOST     = os.getenv('DB_HOST', 'postgres')
PG_PORT     = os.getenv('DB_PORT', '5432')
PG_USER     = os.getenv('DB_USER', 'postgres')
PG_PASSWORD = os.getenv('DB_PASSWORD', '')
PG_DBNAME   = os.getenv('DB_NAME', 'msf')

REDIS_HOST  = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT  = int(os.getenv('REDIS_PORT', '6379'))
QUEUE_KEY   = 'zap:targets'

ZAP_HOST        = os.getenv('ZAP_HOST', 'zaproxy')
ZAP_PORT        = os.getenv('ZAP_PORT', '8090')
ZAP_API_KEY     = os.getenv('ZAP_API_KEY', '')
ZAP_CONCURRENCY = int(os.getenv('ZAP_CONCURRENCY', '3'))
ZAP_BASE        = f"http://{ZAP_HOST}:{ZAP_PORT}"

FARADAY_URL   = os.getenv('FARADAY_URL', '').rstrip('/')
FARADAY_TOKEN = os.getenv('FARADAY_TOKEN', '')
FARADAY_WS    = os.getenv('FARADAY_WORKSPACE', 'default')

FEED_INTERVAL = int(os.getenv('FEED_INTERVAL_SECONDS', '300'))
BATCH_SIZE    = int(os.getenv('BATCH_SIZE', '50'))

WEB_PORTS    = {80, 443, 8080, 8443, 8000, 8008, 9000, 3000, 5000}
WEB_SERVICES = {'http', 'https', 'http-proxy', 'http-alt', 'web', 'www'}

# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT,
        user=PG_USER, password=PG_PASSWORD,
        dbname=PG_DBNAME
    )


def ensure_zap_scan_log():
    """Crée la table zap_scan_log si elle n'existe pas."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS zap_scan_log (
                    host_id    INT PRIMARY KEY,
                    address    TEXT NOT NULL,
                    scanned_at TIMESTAMP DEFAULT NOW(),
                    alerts     INT DEFAULT 0,
                    status     TEXT DEFAULT 'done'
                )
            """)
        conn.commit()
    logger.info("zap_scan_log prête")


def fetch_unscanned_hosts(batch: int) -> List[Dict]:
    """Retourne des hosts avec services web non encore dans zap_scan_log."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT ON (h.id)
                    h.id, h.address::text,
                    s.port, s.name AS svc_name
                FROM hosts h
                JOIN services s ON s.host_id = h.id
                WHERE (
                    s.port = ANY(%s)
                    OR lower(s.name) = ANY(%s)
                )
                AND h.id NOT IN (SELECT host_id FROM zap_scan_log)
                AND h.state = 'alive'
                ORDER BY h.id, s.port
                LIMIT %s
            """, (
                list(WEB_PORTS),
                list(WEB_SERVICES),
                batch
            ))
            return cur.fetchall()


def mark_scanned(host_id: int, address: str, alerts: int, status: str = 'done'):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO zap_scan_log (host_id, address, scanned_at, alerts, status)
                VALUES (%s, %s, NOW(), %s, %s)
                ON CONFLICT (host_id) DO UPDATE
                    SET scanned_at = NOW(), alerts = EXCLUDED.alerts, status = EXCLUDED.status
            """, (host_id, address, alerts, status))
        conn.commit()


# ── Redis ─────────────────────────────────────────────────────────────────────

def get_redis() -> redis.Redis:
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


# ── ZAP client ────────────────────────────────────────────────────────────────

def zap_get(path: str, params: dict = None) -> Optional[dict]:
    p = params or {}
    if ZAP_API_KEY:
        p['apikey'] = ZAP_API_KEY
    try:
        r = requests.get(f"{ZAP_BASE}{path}", params=p, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.debug(f"ZAP {path}: {e}")
    return None


def zap_ready(timeout: int = 300) -> bool:
    logger.info(f"Attente ZAP sur {ZAP_BASE}...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        data = zap_get('/JSON/core/view/version/')
        if data:
            logger.info(f"ZAP prêt — version {data.get('version', '?')}")
            return True
        time.sleep(5)
    logger.error("ZAP non disponible après timeout")
    return False


def zap_spider(url: str) -> Optional[str]:
    data = zap_get('/JSON/spider/action/scan/', {'url': url})
    if data and 'scan' in data:
        return data['scan']
    return None


def zap_active_scan(url: str) -> Optional[str]:
    data = zap_get('/JSON/ascan/action/scan/', {'url': url})
    if data and 'scan' in data:
        return data['scan']
    return None


def zap_spider_status(scan_id: str) -> Optional[int]:
    data = zap_get('/JSON/spider/view/status/', {'scanId': scan_id})
    if not data or data.get('code') == 'DOES_NOT_EXIST':
        return None
    try:
        return int(data.get('status', 0))
    except (ValueError, TypeError):
        return None


def zap_ascan_status(scan_id: str) -> Optional[int]:
    data = zap_get('/JSON/ascan/view/status/', {'scanId': scan_id})
    if not data or data.get('code') == 'DOES_NOT_EXIST':
        return None
    try:
        return int(data.get('status', 0))
    except (ValueError, TypeError):
        return None


def zap_alerts(url: str) -> List[Dict]:
    data = zap_get('/JSON/core/view/alerts/', {'baseurl': url})
    if data and 'alerts' in data:
        return data['alerts']
    return []


# ── Faraday client ────────────────────────────────────────────────────────────

def faraday_post_vulns(address: str, alerts: List[Dict]):
    if not FARADAY_URL or not FARADAY_TOKEN or not alerts:
        return
    headers = {'Authorization': f'Token {FARADAY_TOKEN}', 'Content-Type': 'application/json'}
    for alert in alerts:
        risk = alert.get('riskdesc', '')
        severity = 'critical' if 'High' in risk else 'med' if 'Medium' in risk else 'low'
        vuln = {
            'name': alert.get('name', 'ZAP finding'),
            'desc': alert.get('description', ''),
            'severity': severity,
            'refs': [alert.get('reference', '')],
            'target': address,
            'tool': 'zaproxy',
            'data': alert.get('solution', ''),
        }
        try:
            requests.post(
                f"{FARADAY_URL}/api/v3/ws/{FARADAY_WS}/vulns/",
                headers=headers, json=vuln, timeout=10
            )
        except Exception as e:
            logger.debug(f"Faraday POST failed for {address}: {e}")


# ── DB Feeder thread ──────────────────────────────────────────────────────────

class DbFeeder(threading.Thread):
    """Charge périodiquement les hosts web non scannés dans la queue Redis."""
    def __init__(self, rdb: redis.Redis):
        super().__init__(daemon=True)
        self.rdb = rdb

    def run(self):
        while True:
            try:
                queue_len = self.rdb.llen(QUEUE_KEY)
                if queue_len < BATCH_SIZE:
                    hosts = fetch_unscanned_hosts(BATCH_SIZE)
                    if hosts:
                        pipe = self.rdb.pipeline()
                        for h in hosts:
                            pipe.rpush(QUEUE_KEY, json.dumps({
                                'host_id': h['id'],
                                'address': h['address'],
                                'port':    h['port'],
                                'svc':     h['svc_name'],
                            }))
                        pipe.execute()
                        logger.info(f"Feeder: {len(hosts)} hosts ajoutés (queue={queue_len + len(hosts)})")
                    else:
                        logger.info("Feeder: aucun host non scanné disponible")
                else:
                    logger.debug(f"Feeder: queue suffisamment remplie ({queue_len})")
            except Exception as e:
                logger.error(f"Feeder error: {e}")
            time.sleep(FEED_INTERVAL)


# ── Scan Worker ───────────────────────────────────────────────────────────────

def build_url(address: str, port: int, svc: str) -> str:
    if port == 443 or 'https' in (svc or '').lower():
        proto = 'https'
    else:
        proto = 'http'
    if (proto == 'http' and port == 80) or (proto == 'https' and port == 443):
        return f"{proto}://{address}"
    return f"{proto}://{address}:{port}"


class ActiveScan:
    """Représente un scan ZAP en cours (spider + active scan)."""
    def __init__(self, host_id: int, address: str, url: str):
        self.host_id  = host_id
        self.address  = address
        self.url      = url
        self.phase    = 'spider'  # spider → active → done
        self.spider_id: Optional[str] = None
        self.ascan_id:  Optional[str] = None
        self.started_at = time.time()
        self.timeout    = 3600

    def timed_out(self) -> bool:
        return time.time() - self.started_at > self.timeout


def run_scanner(rdb: redis.Redis):
    """Boucle principale — gère N scans ZAP concurrents."""
    active: Dict[str, ActiveScan] = {}  # url → ActiveScan

    while True:
        # ── Avancer les scans actifs ──────────────────────────────────────
        for url in list(active.keys()):
            scan = active[url]

            if scan.timed_out():
                logger.warning(f"[TIMEOUT] {url}")
                mark_scanned(scan.host_id, scan.address, 0, 'timeout')
                del active[url]
                continue

            if scan.phase == 'spider':
                if scan.spider_id is None:
                    sid = zap_spider(url)
                    if sid:
                        scan.spider_id = sid
                        logger.info(f"[SPIDER] {url} → id={sid}")
                    else:
                        logger.warning(f"[SPIDER] échec soumission {url}")
                        mark_scanned(scan.host_id, scan.address, 0, 'error')
                        del active[url]
                else:
                    pct = zap_spider_status(scan.spider_id)
                    if pct is None:
                        logger.warning(f"[SPIDER] scan {scan.spider_id} disparu — abandon")
                        mark_scanned(scan.host_id, scan.address, 0, 'error')
                        del active[url]
                    elif pct >= 100:
                        logger.info(f"[SPIDER] {url} terminé")
                        scan.phase = 'active'

            elif scan.phase == 'active':
                if scan.ascan_id is None:
                    aid = zap_active_scan(url)
                    if aid:
                        scan.ascan_id = aid
                        logger.info(f"[ASCAN] {url} → id={aid}")
                    else:
                        logger.warning(f"[ASCAN] échec soumission {url}")
                        mark_scanned(scan.host_id, scan.address, 0, 'error')
                        del active[url]
                else:
                    pct = zap_ascan_status(scan.ascan_id)
                    if pct is None:
                        logger.warning(f"[ASCAN] scan {scan.ascan_id} disparu — abandon")
                        mark_scanned(scan.host_id, scan.address, 0, 'error')
                        del active[url]
                    elif pct >= 100:
                        logger.info(f"[ASCAN] {url} terminé — récupération alertes")
                        alerts = zap_alerts(url)
                        mark_scanned(scan.host_id, scan.address, len(alerts), 'done')
                        faraday_post_vulns(scan.address, alerts)
                        logger.info(f"[DONE] {url} — {len(alerts)} alertes")
                        del active[url]
                    else:
                        logger.debug(f"[ASCAN] {url} {pct}%")

        # ── Remplir les slots libres ──────────────────────────────────────
        try:
            while len(active) < ZAP_CONCURRENCY:
                item = rdb.blpop(QUEUE_KEY, timeout=2)
                if not item:
                    break
                target = json.loads(item[1])
                url = build_url(target['address'], target['port'], target['svc'])

                if url in active:
                    continue  # déjà en cours

                active[url] = ActiveScan(target['host_id'], target['address'], url)
                logger.info(f"[QUEUE→ZAP] {url} (host_id={target['host_id']})")
        except Exception as e:
            logger.warning(f"Redis indisponible: {e} — retry dans 10s")
            time.sleep(10)
            continue

        time.sleep(5)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    logger.info("ZAP Scanner v2 démarrage")

    ensure_zap_scan_log()

    if not zap_ready():
        sys.exit(1)

    rdb = get_redis()
    logger.info(f"Redis connecté ({REDIS_HOST}:{REDIS_PORT})")

    feeder = DbFeeder(rdb)
    feeder.start()
    logger.info(f"DbFeeder démarré (interval={FEED_INTERVAL}s, batch={BATCH_SIZE})")
    logger.info(f"ScanWorker démarré (concurrency={ZAP_CONCURRENCY})")

    run_scanner(rdb)


if __name__ == '__main__':
    main()
