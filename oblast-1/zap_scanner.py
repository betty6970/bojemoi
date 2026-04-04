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

FARADAY_URL      = os.getenv('FARADAY_URL', '').rstrip('/')
FARADAY_USER     = os.getenv('FARADAY_USER', 'faraday')
FARADAY_PASSWORD = os.getenv('FARADAY_PASSWORD', '')
FARADAY_WS       = os.getenv('FARADAY_WORKSPACE', 'default')

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
    """Crée/migre la table zap_scan_log."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS zap_scan_log (
                    host_id    INT PRIMARY KEY,
                    address    TEXT NOT NULL,
                    scanned_at TIMESTAMP DEFAULT NOW(),
                    alerts     INT DEFAULT 0,
                    status     TEXT DEFAULT 'done',
                    critical   INT DEFAULT 0,
                    high       INT DEFAULT 0,
                    medium     INT DEFAULT 0,
                    low        INT DEFAULT 0,
                    info       INT DEFAULT 0,
                    faraday_ok BOOLEAN DEFAULT FALSE
                )
            """)
            # Migration idempotente pour tables existantes
            for col, definition in [
                ('critical',   'INT DEFAULT 0'),
                ('high',       'INT DEFAULT 0'),
                ('medium',     'INT DEFAULT 0'),
                ('low',        'INT DEFAULT 0'),
                ('info',       'INT DEFAULT 0'),
                ('faraday_ok', 'BOOLEAN DEFAULT FALSE'),
            ]:
                cur.execute(f"""
                    ALTER TABLE zap_scan_log
                    ADD COLUMN IF NOT EXISTS {col} {definition}
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


def severity_breakdown(alerts: List[Dict]) -> Dict:
    counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
    for a in alerts:
        sev = _ZAP_SEV.get(int(a.get('riskcode', 0)), 'info')
        if sev in counts:
            counts[sev] += 1
    return counts


def mark_scanned(host_id: int, address: str, alerts: int, status: str = 'done',
                 breakdown: Dict = None, faraday_ok: bool = False):
    bd = breakdown or {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO zap_scan_log
                    (host_id, address, scanned_at, alerts, status,
                     critical, high, medium, low, info, faraday_ok)
                VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (host_id) DO UPDATE SET
                    scanned_at = NOW(), alerts = EXCLUDED.alerts, status = EXCLUDED.status,
                    critical = EXCLUDED.critical, high = EXCLUDED.high,
                    medium = EXCLUDED.medium, low = EXCLUDED.low,
                    info = EXCLUDED.info, faraday_ok = EXCLUDED.faraday_ok
            """, (host_id, address, alerts, status,
                  bd['critical'], bd['high'], bd['medium'], bd['low'], bd['info'],
                  faraday_ok))
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
            # Réduire le timeout HTTP de ZAP pour rejeter les hôtes morts plus vite
            zap_get('/JSON/core/action/setOptionTimeoutInSecs/', {'Integer': '5'})
            logger.info("ZAP HTTP timeout → 5s")
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


def zap_urls_found(url: str) -> int:
    """Returns number of URLs found by spider for a given base URL."""
    data = zap_get('/JSON/core/view/urls/', {'baseurl': url})
    if data and 'urls' in data:
        return len(data['urls'])
    return 0


def zap_alerts(url: str) -> List[Dict]:
    data = zap_get('/JSON/core/view/alerts/', {'baseurl': url})
    if data and 'alerts' in data:
        return data['alerts']
    return []


# ── Faraday client ────────────────────────────────────────────────────────────

def faraday_get_or_create_host(ip: str, auth: tuple) -> Optional[int]:
    """Crée le host dans Faraday si nécessaire, retourne son ID."""
    base = f"{FARADAY_URL}/_api/v3/ws/{FARADAY_WS}"
    # Créer (ignore 409 si déjà existant)
    requests.post(f"{base}/hosts", auth=auth, json={"ip": ip, "description": "ZAP scan target"}, timeout=10)
    # Récupérer l'ID
    try:
        r = requests.get(f"{base}/hosts", auth=auth, params={"search": ip}, timeout=10)
        if r.status_code == 200:
            rows = r.json().get("rows", [])
            if rows:
                return rows[0]["id"]
    except Exception as e:
        logger.debug(f"Faraday host lookup failed for {ip}: {e}")
    return None


_ZAP_SEV = {3: 'high', 2: 'medium', 1: 'low', 0: 'info'}


def faraday_post_vulns(address: str, alerts: List[Dict]) -> int:
    if not FARADAY_URL or not FARADAY_PASSWORD or not alerts:
        return 0
    auth = (FARADAY_USER, FARADAY_PASSWORD)
    ip = address.split('/')[0]
    host_id = faraday_get_or_create_host(ip, auth)
    if not host_id:
        logger.debug(f"Faraday: impossible de récupérer host_id pour {ip}")
        return
    posted = 0
    for alert in alerts:
        riskcode = int(alert.get('riskcode', 0))
        severity = _ZAP_SEV.get(riskcode, 'info')

        # HTTP evidence from first instance
        instances = alert.get('instances', [])
        first_inst = instances[0] if instances else {}
        evidence_parts = []
        if first_inst.get('method'):
            evidence_parts.append(f"Method: {first_inst['method']}")
        if first_inst.get('uri'):
            evidence_parts.append(f"URI: {first_inst['uri']}")
        if first_inst.get('evidence'):
            evidence_parts.append(f"Evidence: {first_inst['evidence']}")

        solution = alert.get('solution', '')
        data_parts = []
        if solution:
            data_parts.append(f"Solution: {solution}")
        if evidence_parts:
            data_parts.append('\n'.join(evidence_parts))

        # Refs: split multi-line reference field
        ref_str = alert.get('reference', '')
        refs = [{'name': r.strip(), 'type': 'other'} for r in ref_str.split('\n') if r.strip()]

        vuln = {
            'name': alert.get('name', 'ZAP finding'),
            'desc': alert.get('description', ''),
            'severity': severity,
            'refs': refs,
            'data': '\n\n'.join(data_parts),
            'type': 'Vulnerability',
            'parent': host_id,
            'parent_type': 'Host',
            'status': 'open',
            'confirmed': False,
            'tags': ['zap'],
        }
        try:
            r = requests.post(
                f"{FARADAY_URL}/_api/v3/ws/{FARADAY_WS}/vulns",
                auth=auth, json=vuln, timeout=10
            )
            if r.status_code in (200, 201):
                posted += 1
            elif r.status_code == 409:
                posted += 1  # déjà existant = OK
            else:
                logger.debug(f"Faraday POST {r.status_code} for {ip}: {r.text[:100]}")
        except Exception as e:
            logger.debug(f"Faraday POST failed for {ip}: {e}")
        time.sleep(0.15)  # throttle: max ~6 req/s pour ne pas saturer Faraday
    if posted:
        logger.info(f"[FARADAY] {ip} → {posted}/{len(alerts)} vulns postées")
    return posted


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
    # Strip CIDR mask if present (e.g. "5.8.8.2/32" → "5.8.8.2")
    host = address.split('/')[0]
    if port == 443 or 'https' in (svc or '').lower():
        proto = 'https'
    else:
        proto = 'http'
    if (proto == 'http' and port == 80) or (proto == 'https' and port == 443):
        return f"{proto}://{host}"
    return f"{proto}://{host}:{port}"


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
                        n = zap_urls_found(url)
                        if n == 0:
                            logger.info(f"[SPIDER] {url} terminé — 0 URL trouvées (host injoignable)")
                            mark_scanned(scan.host_id, scan.address, 0, 'no_web')
                            del active[url]
                        else:
                            logger.info(f"[SPIDER] {url} terminé — {n} URLs")
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
                        bd = severity_breakdown(alerts)
                        faraday_ok = faraday_post_vulns(scan.address, alerts) > 0
                        status = 'done' if alerts else 'no_findings'
                        mark_scanned(scan.host_id, scan.address, len(alerts), status,
                                     breakdown=bd, faraday_ok=faraday_ok)
                        logger.info(f"[DONE] {url} — {len(alerts)} alertes "
                                    f"(h={bd['high']} m={bd['medium']} l={bd['low']}) "
                                    f"faraday={'ok' if faraday_ok else 'no'}")
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

                # Pre-check HTTP rapide (3s) — évite 25s de timeout ZAP sur hosts morts
                try:
                    requests.get(url, timeout=3, verify=False, allow_redirects=True)
                except Exception:
                    logger.info(f"[SKIP] {url} — pas de réponse HTTP (host_id={target['host_id']})")
                    mark_scanned(target['host_id'], target['address'], 0, 'no_web')
                    continue

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
