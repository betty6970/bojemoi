#!/bin/ash
# Import RIPE NCC IPv6 delegated CIDRs into ip2location_db1_v6
# Source: https://ftp.ripe.net/pub/stats/ripencc/delegated-ripencc-latest
# Usage: ./import_ipv6_cidrs.sh [country_code]  (default: RU)

COUNTRY="${1:-RU}"
PGPASSWORD="${PGPASSWORD:-bojemoi}"
PGUSER="${PGUSER:-postgres}"
PGDB="ip2location"
RIPE_URL="https://ftp.ripe.net/pub/stats/ripencc/delegated-ripencc-latest"

# ── Résolution PostgreSQL ────────────────────────────────────────────────────
echo "[INFO] Résolution DNS postgres..."
while true; do
    ip=$(ping -c 1 -W 1 "postgres" 2>/dev/null | head -n 1 | awk '{print $3}')
    sql_ip="${ip:1:-2}"
    if [ -n "$sql_ip" ] && ping -c 1 -W 1 "postgres" &>/dev/null; then
        if pg_isready -h "$sql_ip" -U "$PGUSER" -d "$PGDB" > /dev/null 2>&1; then
            echo "[INFO] PostgreSQL détecté à $sql_ip"
            break
        fi
    fi
    echo "[ATTENTE] PostgreSQL... retry dans 5s"
    sleep 5
done

# ── Créer la table si elle n'existe pas ─────────────────────────────────────
echo "[INFO] Création de ip2location_db1_v6 (si absente)..."
PGPASSWORD="$PGPASSWORD" psql -h "$sql_ip" -U "$PGUSER" -d "$PGDB" << 'EOSQL'
CREATE TABLE IF NOT EXISTS ip2location_db1_v6 (
    cidr_z      cidr        PRIMARY KEY,
    country_code char(2)    NOT NULL,
    country_name varchar(64) NOT NULL,
    nmap        "char"      NOT NULL DEFAULT '0',
    date_nmap   timestamp
);
EOSQL

# ── Télécharger et importer ──────────────────────────────────────────────────
echo "[INFO] Téléchargement RIPE NCC delegated stats (country=$COUNTRY)..."
curl -4 -s "$RIPE_URL" \
  | awk -F'|' -v cc="$COUNTRY" '$2==cc && $3=="ipv6" {print $4"/"$5}' \
  | (
      echo "BEGIN;"
      while read cidr; do
          echo "INSERT INTO ip2location_db1_v6 (cidr_z, country_code, country_name) VALUES ('$cidr', '$COUNTRY', 'Russian Federation') ON CONFLICT DO NOTHING;"
      done
      echo "COMMIT;"
    ) \
  | PGPASSWORD="$PGPASSWORD" psql -h "$sql_ip" -U "$PGUSER" -d "$PGDB" -q

COUNT=$(PGPASSWORD="$PGPASSWORD" psql -h "$sql_ip" -U "$PGUSER" -d "$PGDB" -t -c \
    "SELECT count(*) FROM ip2location_db1_v6;" | tr -d '[:space:]')
echo "[DONE] ip2location_db1_v6 : $COUNT entrées"
