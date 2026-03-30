#!/bin/sh
# start_msf_server.sh — Démarre msfrpcd en mode teamserver partagé (0.0.0.0)
# Utilisé par le service msf-teamserver (un seul par cluster)
set -e

PG_USER="${PG_USER:-postgres}"
PG_PASSWORD="${PG_PASSWORD:-bojemoi}"
PG_HOST="${PG_HOST:-postgres}"
PG_DBNAME="${PG_DBNAME:-msf}"
MSF_PASS="totototo"
MSF_PORT=55553

mkdir -p /opt/metasploit/.msf4
cat > /opt/metasploit/.msf4/database.yml <<EOF
production:
  adapter: postgresql
  database: ${PG_DBNAME}
  username: ${PG_USER}
  password: ${PG_PASSWORD}
  host: ${PG_HOST}
  port: 5432
  pool: 75
  timeout: 5
EOF

echo "[INFO] Starting msfrpcd teamserver on 0.0.0.0:${MSF_PORT}..."
cd /opt/metasploit
./msfrpcd -P "${MSF_PASS}" -a 0.0.0.0 -p ${MSF_PORT}

# Attendre que msfrpcd soit prêt
i=0
while [ $i -lt 180 ]; do
    if nc -z 127.0.0.1 ${MSF_PORT} 2>/dev/null; then
        echo "[INFO] msfrpcd ready after ${i}s"
        break
    fi
    sleep 1
    i=$((i + 1))
done

if ! nc -z 127.0.0.1 ${MSF_PORT} 2>/dev/null; then
    echo "[ERROR] msfrpcd failed to start after 180s"
    exit 1
fi

echo "[INFO] Rebuilding module cache (once at startup)..."
./msfconsole -q -x "db_rebuild_cache; exit" 2>&1 | tail -3
echo "[INFO] Module cache ready. Teamserver running."

# Garder le container vivant (msfrpcd tourne en arrière-plan)
tail -f /dev/null
