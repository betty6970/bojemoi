#!/usr/bin/env python3
"""
ZAP Scanner v2
Architecture: Redis queue + zap_scan_log + DefectDojo export
- DbFeeder thread: charge les hosts web non scannés → Redis queue
- ScanWorker: dépile la queue, soumet à ZAP (N scans concurrents),
  enregistre dans zap_scan_log, exporte vers DefectDojo
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


def _read_secret(name, legacy_env=None):
    """Read sensitive value: legacy env var → NAME env var → /run/secrets/name file."""
    if legacy_env:
        v = os.getenv(legacy_env, "")
        if v:
            return v
    v = os.getenv(name.upper(), "")
    if v:
        return v
    try:
        with open(f"/run/secrets/{name}") as f:
            return f.read().strip()
    except OSError:
        return ""


# ── Config ────────────────────────────────────────────────────────────────────

PG_HOST     = os.getenv('DB_HOST', 'postgres')
PG_PORT     = os.getenv('DB_PORT', '5432')
PG_USER     = os.getenv('DB_USER', 'postgres')
PG_PASSWORD = _read_secret("postgres_password", "DB_PASSWORD")
PG_DBNAME   = os.getenv('DB_NAME', 'msf')

REDIS_HOST  = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT  = int(os.getenv('REDIS_PORT', '6379'))
QUEUE_KEY   = 'zap:targets'

ZAP_HOST        = os.getenv('ZAP_HOST', 'zaproxy')
ZAP_PORT        = os.getenv('ZAP_PORT', '8090')
ZAP_API_KEY     = os.getenv('ZAP_API_KEY', '')
ZAP_CONCURRENCY = int(os.getenv('ZAP_CONCURRENCY', '3'))
ZAP_BASE        = f"http://{ZAP_HOST}:{ZAP_PORT}"

DEFECTDOJO_URL      = os.getenv('DEFECTDOJO_URL', '').rstrip('/')
DEFECTDOJO_TOKEN    = _read_secret("dojo_api_token", "DEFECTDOJO_TOKEN")
DEFECTDOJO_PRODUCT  = os.getenv('DEFECTDOJO_PRODUCT', 'zap')

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
                    dojo_ok    BOOLEAN DEFAULT FALSE
                )
            """)
            # Migration idempotente pour tables existantes
            for col, definition in [
                ('critical', 'INT DEFAULT 0'),
                ('high',     'INT DEFAULT 0'),
                ('medium',   'INT DEFAULT 0'),
                ('low',      'INT DEFAULT 0'),
                ('info',     'INT DEFAULT 0'),
                ('dojo_ok',  'BOOLEAN DEFAULT FALSE'),
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
                    h.id, host(h.address::inet) AS address,
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
                 breakdown: Dict = None, dojo_ok: bool = False):
    bd = breakdown or {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO zap_scan_log
                    (host_id, address, scanned_at, alerts, status,
                     critical, high, medium, low, info, dojo_ok)
                VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (host_id) DO UPDATE SET
                    scanned_at = NOW(), alerts = EXCLUDED.alerts, status = EXCLUDED.status,
                    critical = EXCLUDED.critical, high = EXCLUDED.high,
                    medium = EXCLUDED.medium, low = EXCLUDED.low,
                    info = EXCLUDED.info, dojo_ok = EXCLUDED.dojo_ok
            """, (host_id, address, alerts, status,
                  bd['critical'], bd['high'], bd['medium'], bd['low'], bd['info'],
                  dojo_ok))
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


# ── DefectDojo client ─────────────────────────────────────────────────────────

_ZAP_SEV = {3: 'High', 2: 'Medium', 1: 'Low', 0: 'Info'}
_ZAP_NUM_SEV = {3: 'S1', 2: 'S2', 1: 'S3', 0: 'S4'}  # numerical_severity requis par DefectDojo

_dojo_test_cache: Dict[str, int] = {}       # product_name → test_id
_dojo_test_type_cache: Dict[str, int] = {}  # product_name → test_type_id
_dojo_product_cache: Dict[str, int] = {}    # product_name → product_id
_dojo_endpoint_cache: Dict[str, int] = {}   # host → endpoint_id


def _dojo_headers() -> Dict:
    if DEFECTDOJO_TOKEN:
        return {"Authorization": f"Token {DEFECTDOJO_TOKEN}"}
    return {}


def _dojo_get_or_create_test(product_name: str) -> Optional[int]:
    """Retourne l'ID du test DefectDojo pour le product ZAP. Cache en mémoire."""
    if product_name in _dojo_test_cache:
        return _dojo_test_cache[product_name]

    base = DEFECTDOJO_URL
    headers = _dojo_headers()
    import datetime

    try:
        # Product
        r = requests.get(f"{base}/api/v2/products/", headers=headers, params={"name": product_name}, timeout=10)
        r.raise_for_status()
        products = r.json().get("results", [])
        if products:
            product_id = products[0]["id"]
        else:
            r2 = requests.get(f"{base}/api/v2/product_types/", headers=headers, params={"limit": 1}, timeout=10)
            r2.raise_for_status()
            types = r2.json().get("results", [])
            prod_type_id = types[0]["id"] if types else 1
            r3 = requests.post(f"{base}/api/v2/products/", headers=headers, json={
                "name": product_name, "description": "ZAP scans", "prod_type": prod_type_id,
            }, timeout=10)
            r3.raise_for_status()
            product_id = r3.json()["id"]

        # Engagement
        r = requests.get(f"{base}/api/v2/engagements/", headers=headers,
                         params={"product": product_id, "name": "zap"}, timeout=10)
        r.raise_for_status()
        engagements = r.json().get("results", [])
        if engagements:
            engagement_id = engagements[0]["id"]
        else:
            today = str(datetime.date.today())
            r2 = requests.post(f"{base}/api/v2/engagements/", headers=headers, json={
                "name": "zap", "product": product_id,
                "target_start": today, "target_end": today,
                "status": "In Progress", "engagement_type": "Interactive",
            }, timeout=10)
            r2.raise_for_status()
            engagement_id = r2.json()["id"]

        # Test type: préférer "ZAP Scan"
        r2 = requests.get(f"{base}/api/v2/test_types/", headers=headers, params={"name": "ZAP Scan"}, timeout=10)
        r2.raise_for_status()
        types = r2.json().get("results", [])
        if not types:
            r2 = requests.get(f"{base}/api/v2/test_types/", headers=headers, params={"limit": 1}, timeout=10)
            r2.raise_for_status()
            types = r2.json().get("results", [])
        test_type_id = types[0]["id"] if types else 1

        # Test
        r = requests.get(f"{base}/api/v2/tests/", headers=headers,
                         params={"engagement": engagement_id, "title": "zap"}, timeout=10)
        r.raise_for_status()
        tests = r.json().get("results", [])
        if tests:
            test_id = tests[0]["id"]
        else:
            today = str(datetime.date.today())
            r3 = requests.post(f"{base}/api/v2/tests/", headers=headers, json={
                "title": "zap", "engagement": engagement_id, "test_type": test_type_id,
                "target_start": today, "target_end": today,
            }, timeout=10)
            r3.raise_for_status()
            test_id = r3.json()["id"]

        _dojo_test_cache[product_name] = test_id
        _dojo_test_type_cache[product_name] = test_type_id
        _dojo_product_cache[product_name] = product_id
        return test_id

    except Exception as e:
        logger.debug(f"DefectDojo setup failed: {e}")
        return None


def _dojo_get_or_create_endpoint(host: str, product_name: str) -> Optional[int]:
    """Retourne l'ID de l'endpoint DefectDojo pour un host. Crée si nécessaire."""
    if host in _dojo_endpoint_cache:
        return _dojo_endpoint_cache[host]
    product_id = _dojo_product_cache.get(product_name)
    if not product_id:
        return None
    base = DEFECTDOJO_URL
    headers = _dojo_headers()
    try:
        r = requests.get(f"{base}/api/v2/endpoints/", headers=headers,
                         params={"host": host, "product": product_id}, timeout=10)
        r.raise_for_status()
        results = r.json().get("results", [])
        if results:
            eid = results[0]["id"]
        else:
            r2 = requests.post(f"{base}/api/v2/endpoints/", headers=headers,
                               json={"host": host, "product": product_id}, timeout=10)
            if r2.status_code not in (200, 201):
                return None
            eid = r2.json()["id"]
        _dojo_endpoint_cache[host] = eid
        return eid
    except Exception as e:
        logger.debug(f"DefectDojo endpoint failed for {host}: {e}")
        return None


def dojo_post_vulns(address: str, alerts: List[Dict]) -> int:
    if not DEFECTDOJO_URL or not DEFECTDOJO_TOKEN or not alerts:
        return 0

    ip = address.split('/')[0]
    test_id = _dojo_get_or_create_test(DEFECTDOJO_PRODUCT)
    if not test_id:
        logger.debug(f"DefectDojo: cannot get test_id for {ip}")
        return 0

    endpoint_id = _dojo_get_or_create_endpoint(ip, DEFECTDOJO_PRODUCT)
    headers = _dojo_headers()
    posted = 0

    for alert in alerts:
        riskcode = int(alert.get('riskcode', 0))
        severity = _ZAP_SEV.get(riskcode, 'Info')

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
        desc_parts = [alert.get('description', '')]
        if solution:
            desc_parts.append(f"\nSolution: {solution}")
        if evidence_parts:
            desc_parts.append('\n'.join(evidence_parts))

        test_type_id = _dojo_test_type_cache.get(DEFECTDOJO_PRODUCT, 1)
        finding = {
            'title': alert.get('name', 'ZAP finding'),
            'description': '\n\n'.join(filter(None, desc_parts)) or "No description",
            'severity': severity,
            'numerical_severity': _ZAP_NUM_SEV.get(riskcode, 'S4'),
            'found_by': [test_type_id],
            'active': True,
            'verified': False,
            'false_p': False,
            'risk_accepted': False,
            'test': test_id,
        }
        if endpoint_id:
            finding['endpoints'] = [endpoint_id]
        try:
            r = requests.post(
                f"{DEFECTDOJO_URL}/api/v2/findings/",
                headers=headers, json=finding, timeout=10,
            )
            if r.status_code in (200, 201):
                posted += 1
            else:
                logger.debug(f"DefectDojo POST {r.status_code} for {ip}: {r.text[:100]}")
        except Exception as e:
            logger.debug(f"DefectDojo POST failed for {ip}: {e}")
        time.sleep(0.15)

    if posted:
        logger.info(f"[DEFECTDOJO] {ip} → {posted}/{len(alerts)} findings posted")
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
                        dojo_ok = dojo_post_vulns(scan.address, alerts) > 0
                        significant = bd['critical'] + bd['high'] + bd['medium'] + bd['low']
                        status = 'done' if alerts else 'no_findings'
                        mark_scanned(scan.host_id, scan.address, significant, status,
                                     breakdown=bd, dojo_ok=dojo_ok)
                        logger.info(f"[DONE] {url} — {len(alerts)} alertes "
                                    f"(h={bd['high']} m={bd['medium']} l={bd['low']}) "
                                    f"dojo={'ok' if dojo_ok else 'no'}")
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

    for attempt in range(1, 11):
        try:
            ensure_zap_scan_log()
            break
        except psycopg2.OperationalError as e:
            logger.warning(f"Postgres indisponible (tentative {attempt}/10): {e}")
            if attempt == 10:
                logger.error("Postgres inaccessible après 10 tentatives — abandon")
                sys.exit(1)
            time.sleep(10)

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
