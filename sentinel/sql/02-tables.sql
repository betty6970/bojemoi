-- Bojemoi Lab — Sentinel
-- Script 02 : Création des tables
-- À exécuter connecté à la base sentinel (en tant que sentinel ou postgres)

\c sentinel

-- ─── Table : détections brutes ─────────────────────────────────────────────
-- Chaque détection WiFi probe ou BLE reçue par un ESP32
CREATE TABLE IF NOT EXISTS perimeter_detections (
    id             SERIAL       PRIMARY KEY,
    mac            VARCHAR(17)  NOT NULL,
    mac_randomized BOOLEAN      NOT NULL DEFAULT FALSE,
    rssi           INTEGER,
    detection_type VARCHAR(10)  NOT NULL,   -- 'wifi' | 'ble'
    extra          TEXT,                    -- champ libre (SSID, nom BLE, etc.)
    esp32_id       VARCHAR(50),             -- identifiant du capteur ESP32
    is_known       BOOLEAN      NOT NULL DEFAULT FALSE,
    first_seen     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_seen      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    seen_count     INTEGER      NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_pd_mac
    ON perimeter_detections(mac);

CREATE INDEX IF NOT EXISTS idx_pd_last_seen
    ON perimeter_detections(last_seen DESC);

CREATE INDEX IF NOT EXISTS idx_pd_is_known
    ON perimeter_detections(is_known);

CREATE INDEX IF NOT EXISTS idx_pd_esp32_id
    ON perimeter_detections(esp32_id);

CREATE INDEX IF NOT EXISTS idx_pd_mac_type_date
    ON perimeter_detections(mac, detection_type, DATE(first_seen AT TIME ZONE 'UTC'));

COMMENT ON TABLE perimeter_detections IS
    'Détections brutes WiFi/BLE reçues depuis les capteurs ESP32 via MQTT';
COMMENT ON COLUMN perimeter_detections.mac IS
    'Adresse MAC du device détecté (lower case, format aa:bb:cc:dd:ee:ff)';
COMMENT ON COLUMN perimeter_detections.mac_randomized IS
    'True si l''adresse MAC est aléatoire (iOS/Android privacy mode)';
COMMENT ON COLUMN perimeter_detections.rssi IS
    'Signal strength en dBm (ex: -55 = proche, -90 = loin)';
COMMENT ON COLUMN perimeter_detections.detection_type IS
    'Type de détection : wifi (probe request) ou ble (advertising)';
COMMENT ON COLUMN perimeter_detections.extra IS
    'Données complémentaires : SSID sondé (WiFi) ou nom BLE';
COMMENT ON COLUMN perimeter_detections.esp32_id IS
    'Identifiant du capteur ESP32 source (ex: sentinel-01)';
COMMENT ON COLUMN perimeter_detections.is_known IS
    'True si le device appartient à la liste blanche';


-- ─── Table : positions par zone ────────────────────────────────────────────
-- Résultat de la triangulation multi-ESP32 : une ligne par MAC connue
-- Zone = nom de la zone de l'ESP32 ayant le RSSI le plus fort
CREATE TABLE IF NOT EXISTS perimeter_positions (
    id          SERIAL       PRIMARY KEY,
    mac         VARCHAR(17)  NOT NULL,
    zone        VARCHAR(100) NOT NULL,    -- zone de l'ESP32 avec RSSI max
    rssi_max    INTEGER,                  -- RSSI le plus fort observé
    rssi_by_esp JSONB,                   -- {"sentinel-01": -55, "sentinel-02": -72}
    esp32_count INTEGER      DEFAULT 1,  -- nombre de capteurs qui voient ce device
    est_dist_m  FLOAT,                   -- distance estimée via modèle path-loss (mètres)
    is_known    BOOLEAN      NOT NULL DEFAULT FALSE,
    first_seen  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    last_seen   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE(mac)
);

CREATE INDEX IF NOT EXISTS idx_pp_zone
    ON perimeter_positions(zone);

CREATE INDEX IF NOT EXISTS idx_pp_last_seen
    ON perimeter_positions(last_seen DESC);

CREATE INDEX IF NOT EXISTS idx_pp_is_known
    ON perimeter_positions(is_known);

COMMENT ON TABLE perimeter_positions IS
    'Position courante de chaque device — résultat de l''agrégation multi-ESP32';
COMMENT ON COLUMN perimeter_positions.mac IS
    'Adresse MAC (clé unique — une seule position courante par device)';
COMMENT ON COLUMN perimeter_positions.zone IS
    'Zone assignée = zone de l''ESP32 avec le RSSI le plus fort sur la fenêtre récente';
COMMENT ON COLUMN perimeter_positions.rssi_by_esp IS
    'RSSI par capteur sur la dernière fenêtre d''agrégation (JSONB)';
COMMENT ON COLUMN perimeter_positions.esp32_count IS
    'Nombre de capteurs ayant détecté ce device simultanément';
COMMENT ON COLUMN perimeter_positions.est_dist_m IS
    'Distance estimée en mètres via modèle log-distance path-loss';
