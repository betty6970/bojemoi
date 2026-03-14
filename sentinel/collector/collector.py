"""
Bojemoi Lab — Sentinel Collector
Consomme les messages MQTT des ESP32 et les stocke en PostgreSQL.
Expose des métriques Prometheus sur /metrics (port 9101).
Multi-ESP32 : triangulation par zone (RSSI max = zone la plus proche).
"""

import json
import os
import logging
import threading
import time
import math
from collections import defaultdict
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import psycopg2
import psycopg2.extras
from prometheus_client import Counter, Gauge, start_http_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sentinel")

# ─── Config ──────────────────────────────────────────────────────────────────
def _secret(name: str, env_var: str, default: str = "") -> str:
    """Read from Docker secret file, fall back to env var, then default."""
    secret_path = f"/run/secrets/{name}"
    if os.path.exists(secret_path):
        return open(secret_path).read().strip()
    return os.getenv(env_var, default)

MQTT_HOST  = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT  = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USER  = os.getenv("MQTT_USER", "sentinel")
MQTT_PASS  = _secret("sentinel_mqtt_pass", "MQTT_PASS", "changeme")

PG_DSN = (
    f"host={os.getenv('POSTGRES_HOST', 'postgres')} "
    f"port={os.getenv('POSTGRES_PORT', '5432')} "
    f"dbname={os.getenv('POSTGRES_DB', 'sentinel')} "
    f"user={os.getenv('POSTGRES_USER', 'sentinel')} "
    f"password={_secret('sentinel_pg_pass', 'POSTGRES_PASS', 'changeme')}"
)

METRICS_PORT          = int(os.getenv("METRICS_PORT", "9101"))
RSSI_ALERT_THRESHOLD  = int(os.getenv("RSSI_ALERT_THRESHOLD", "-65"))
ZONE_WINDOW_SECS      = int(os.getenv("ZONE_WINDOW_SECS", "10"))  # fenêtre aggregation zones
ZONE_UPDATE_INTERVAL  = int(os.getenv("ZONE_UPDATE_INTERVAL", "5"))

# Modèle path-loss pour estimation distance :
# d = 10^((TX_POWER - RSSI) / (10 * PATH_LOSS_N))
TX_POWER    = float(os.getenv("TX_POWER", "-65"))   # RSSI à 1 mètre (dBm)
PATH_LOSS_N = float(os.getenv("PATH_LOSS_N", "3.0")) # 2=espace libre, 3-4=indoor

# ─── Prometheus metrics ───────────────────────────────────────────────────────
detections_total = Counter(
    "sentinel_detections_total",
    "Total probe/BLE detections",
    ["esp32_id", "type", "known"],
)
unknown_close_total = Counter(
    "sentinel_unknown_close_total",
    "Unknown devices detected within alert RSSI threshold",
    ["esp32_id", "type"],
)
active_devices = Gauge(
    "sentinel_active_devices",
    "Devices seen in the last 5 minutes",
    ["known"],
)
device_zone_gauge = Gauge(
    "sentinel_device_in_zone",
    "Number of unknown active devices per zone",
    ["zone"],
)
estimated_distance = Gauge(
    "sentinel_estimated_distance_meters",
    "Estimated distance to closest ESP32 (path-loss model)",
    ["esp32_id"],
)

# ─── Buffer multi-ESP32 (aggregation par fenêtre de temps) ───────────────────
# Structure : {mac: {esp32_id: (rssi, zone, ts)}}
_zone_buffer: dict[str, dict[str, tuple]] = defaultdict(dict)
_zone_lock = threading.Lock()

# ─── Database ─────────────────────────────────────────────────────────────────
_db_conn = None

def get_db():
    global _db_conn
    if _db_conn is None or _db_conn.closed:
        _db_conn = psycopg2.connect(PG_DSN)
        _db_conn.autocommit = False
    return _db_conn

def init_db():
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS perimeter_detections (
            id             SERIAL PRIMARY KEY,
            mac            VARCHAR(17)  NOT NULL,
            mac_randomized BOOLEAN      NOT NULL DEFAULT FALSE,
            rssi           INTEGER,
            detection_type VARCHAR(10)  NOT NULL,
            extra          TEXT,
            esp32_id       VARCHAR(50),
            is_known       BOOLEAN      NOT NULL DEFAULT FALSE,
            first_seen     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            last_seen      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            seen_count     INTEGER      NOT NULL DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_pd_mac       ON perimeter_detections(mac);
        CREATE INDEX IF NOT EXISTS idx_pd_last_seen ON perimeter_detections(last_seen);
        CREATE INDEX IF NOT EXISTS idx_pd_is_known  ON perimeter_detections(is_known);

        -- Table de positions par zone (résultat de la triangulation)
        CREATE TABLE IF NOT EXISTS perimeter_positions (
            id          SERIAL PRIMARY KEY,
            mac         VARCHAR(17)  NOT NULL,
            zone        VARCHAR(100) NOT NULL,   -- nom de la zone (zone de l'ESP32 avec RSSI le plus fort)
            rssi_max    INTEGER,                 -- RSSI le plus fort observé
            rssi_by_esp JSONB,                  -- {"sentinel-01": -55, "sentinel-02": -72, ...}
            esp32_count INTEGER DEFAULT 1,       -- nombre de capteurs qui voient ce device
            est_dist_m  FLOAT,                   -- distance estimée (path-loss)
            is_known    BOOLEAN NOT NULL DEFAULT FALSE,
            first_seen  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_seen   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(mac)
        );
        CREATE INDEX IF NOT EXISTS idx_pp_zone      ON perimeter_positions(zone);
        CREATE INDEX IF NOT EXISTS idx_pp_last_seen ON perimeter_positions(last_seen);
        CREATE INDEX IF NOT EXISTS idx_pp_is_known  ON perimeter_positions(is_known);
        """)
    conn.commit()
    log.info("DB schema ready")

def upsert_detection(mac, mac_randomized, rssi, det_type, extra, esp32_id, is_known):
    conn = get_db()
    with conn.cursor() as cur:
        # Upsert sur (mac, detection_type, date)
        cur.execute("""
        INSERT INTO perimeter_detections
            (mac, mac_randomized, rssi, detection_type, extra, esp32_id, is_known)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        """, (mac, mac_randomized, rssi, det_type, extra, esp32_id, is_known))

        cur.execute("""
        UPDATE perimeter_detections
        SET last_seen  = NOW(),
            seen_count = seen_count + 1,
            rssi       = %s
        WHERE mac = %s AND detection_type = %s AND DATE(first_seen) = CURRENT_DATE
        """, (rssi, mac, det_type))
    conn.commit()

def upsert_position(mac, zone, rssi_max, rssi_by_esp, esp32_count, est_dist, is_known):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO perimeter_positions
            (mac, zone, rssi_max, rssi_by_esp, esp32_count, est_dist_m, is_known)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (mac) DO UPDATE SET
            zone        = EXCLUDED.zone,
            rssi_max    = EXCLUDED.rssi_max,
            rssi_by_esp = EXCLUDED.rssi_by_esp,
            esp32_count = EXCLUDED.esp32_count,
            est_dist_m  = EXCLUDED.est_dist_m,
            last_seen   = NOW()
        """, (mac, zone, rssi_max, json.dumps(rssi_by_esp), esp32_count, est_dist, is_known))
    conn.commit()

def refresh_active_gauge():
    try:
        conn = get_db()
        with conn.cursor() as cur:
            cur.execute("""
            SELECT is_known, COUNT(DISTINCT mac)
            FROM perimeter_detections
            WHERE last_seen > NOW() - INTERVAL '5 minutes'
            GROUP BY is_known
            """)
            rows = cur.fetchall()
            active_devices.labels(known="true").set(next((r[1] for r in rows if r[0]), 0))
            active_devices.labels(known="false").set(next((r[1] for r in rows if not r[0]), 0))
    except Exception as e:
        log.warning(f"gauge refresh error: {e}")

# ─── Calcul distance path-loss ────────────────────────────────────────────────
def rssi_to_distance(rssi: int) -> float:
    """Estime la distance en mètres via le modèle log-distance path-loss."""
    try:
        d = 10 ** ((TX_POWER - rssi) / (10 * PATH_LOSS_N))
        return round(d, 1)
    except Exception:
        return -1.0

# ─── Worker zone aggregation ──────────────────────────────────────────────────
def zone_aggregation_worker():
    """
    Toutes les ZONE_UPDATE_INTERVAL secondes :
    - Parcourt le buffer {mac: {esp32_id: (rssi, zone, ts)}}
    - Pour chaque MAC, choisit la zone du capteur avec le RSSI le plus fort
    - Met à jour perimeter_positions
    - Nettoie les entrées > ZONE_WINDOW_SECS * 3
    """
    while True:
        time.sleep(ZONE_UPDATE_INTERVAL)
        now = time.time()
        zone_counts: dict[str, int] = defaultdict(int)

        with _zone_lock:
            macs = list(_zone_buffer.keys())

        for mac in macs:
            with _zone_lock:
                entries = dict(_zone_buffer.get(mac, {}))

            # Filtrer les entrées trop vieilles
            fresh = {
                esp32_id: v
                for esp32_id, v in entries.items()
                if now - v[2] < ZONE_WINDOW_SECS * 3
            }

            if not fresh:
                with _zone_lock:
                    _zone_buffer.pop(mac, None)
                continue

            # Zone = ESP32 avec RSSI max
            best_esp32 = max(fresh, key=lambda k: fresh[k][0])
            best_rssi, best_zone, _ = fresh[best_esp32]

            rssi_by_esp = {k: v[0] for k, v in fresh.items()}
            esp32_count = len(fresh)
            est_dist = rssi_to_distance(best_rssi)
            # is_known : on ne stocke pas dans le buffer, récupérer depuis la détection récente
            is_known = False  # conservatif — la table detections fait foi

            try:
                upsert_position(mac, best_zone, best_rssi, rssi_by_esp,
                                esp32_count, est_dist, is_known)
            except Exception as e:
                log.warning(f"zone upsert error for {mac}: {e}")
                global _db_conn; _db_conn = None

            zone_counts[best_zone] += 1

        # Mise à jour gauge Prometheus par zone
        for zone, count in zone_counts.items():
            device_zone_gauge.labels(zone=zone).set(count)

        if macs:
            log.debug(f"Zones updated: {dict(zone_counts)}")

# ─── MQTT callbacks ───────────────────────────────────────────────────────────
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info("MQTT connected")
        client.subscribe("bojemoi/perimeter/#")
    else:
        log.error(f"MQTT connect failed rc={rc}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
    except json.JSONDecodeError:
        log.warning(f"Invalid JSON: {msg.payload}")
        return

    mac        = data.get("mac", "").lower().strip()
    rssi       = int(data.get("rssi", -100))
    randomized = bool(data.get("randomized", False))
    det_type   = data.get("type", "wifi")
    extra      = data.get("extra", "")
    esp32_id   = data.get("esp32_id", "unknown")
    zone       = data.get("zone", esp32_id)   # si pas de zone, on utilise l'ID capteur
    is_known   = bool(data.get("known", False))

    if not mac:
        return

    log.info(f"[{esp32_id}/{zone}] {det_type} {mac} rssi={rssi} known={is_known} rnd={randomized}")

    # Métriques Prometheus
    detections_total.labels(esp32_id=esp32_id, type=det_type, known=str(is_known).lower()).inc()

    if not is_known and rssi >= RSSI_ALERT_THRESHOLD:
        unknown_close_total.labels(esp32_id=esp32_id, type=det_type).inc()
        dist = rssi_to_distance(rssi)
        log.warning(
            f"ALERT: unknown {det_type} {mac} close (rssi={rssi}, ~{dist}m) via {esp32_id}/{zone}"
        )
        # Mettre à jour le gauge distance
        estimated_distance.labels(esp32_id=esp32_id).set(dist)

    # Buffer zone pour aggregation multi-ESP32
    with _zone_lock:
        _zone_buffer[mac][esp32_id] = (rssi, zone, time.time())

    # Stockage détection brute
    try:
        upsert_detection(mac, randomized, rssi, det_type, extra, esp32_id, is_known)
    except Exception as e:
        log.error(f"DB upsert error: {e}")
        global _db_conn; _db_conn = None

    refresh_active_gauge()

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    log.info(f"Sentinel collector starting — metrics port {METRICS_PORT}")
    log.info(f"Path-loss model: TX={TX_POWER} dBm, n={PATH_LOSS_N}")
    start_http_server(METRICS_PORT)

    # Init DB (retry)
    for attempt in range(10):
        try:
            init_db()
            break
        except Exception as e:
            log.warning(f"DB init attempt {attempt+1}/10: {e}")
            try:
                get_db().rollback()
            except Exception:
                pass
            time.sleep(5)

    # Démarrer le worker de zone aggregation en background
    t = threading.Thread(target=zone_aggregation_worker, daemon=True)
    t.start()
    log.info("Zone aggregation worker started")

    # MQTT
    client = mqtt.Client(client_id="sentinel-collector")
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.loop_forever()

if __name__ == "__main__":
    main()
