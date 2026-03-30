#!/bin/sh
set -e

PG_USER="${PG_USER:-postgres}"
PG_PASSWORD="${PG_PASSWORD:-bojemoi}"
PG_HOST="${PG_HOST:-postgres}"
PG_DBNAME="${PG_DBNAME:-msf}"
MSF_PASS="totototo"
MSF_PORT=55553
MSF_HOST="${MSF_HOST:-127.0.0.1}"

if [ "$MSF_HOST" = "127.0.0.1" ] || [ "$MSF_HOST" = "localhost" ]; then
    # Mode local : démarrer msfrpcd dans ce container
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

    echo "[INFO] Starting msfrpcd on port ${MSF_PORT}..."
    cd /opt/metasploit
    ./msfrpcd -P "${MSF_PASS}" -a 127.0.0.1 -p ${MSF_PORT}

    i=0
    while [ $i -lt 120 ]; do
        if nc -z 127.0.0.1 ${MSF_PORT} 2>/dev/null; then
            echo "[INFO] msfrpcd ready after ${i}s"
            break
        fi
        sleep 1
        i=$((i + 1))
    done

    if ! nc -z 127.0.0.1 ${MSF_PORT} 2>/dev/null; then
        echo "[ERROR] msfrpcd failed to start after 120s"
        exit 1
    fi

    echo "[INFO] Rebuilding module cache (db_rebuild_cache)..."
    cd /opt/metasploit
    ./msfconsole -q -x "db_rebuild_cache; exit" 2>&1 | tail -3
    echo "[INFO] Module cache ready."
else
    # Mode teamserver : attendre que le msfrpcd distant soit prêt
    echo "[INFO] Mode teamserver — attente msfrpcd sur ${MSF_HOST}:${MSF_PORT}..."
    i=0
    while [ $i -lt 300 ]; do
        if nc -z "${MSF_HOST}" ${MSF_PORT} 2>/dev/null; then
            echo "[INFO] msfrpcd teamserver prêt après ${i}s"
            break
        fi
        sleep 2
        i=$((i + 2))
    done

    if ! nc -z "${MSF_HOST}" ${MSF_PORT} 2>/dev/null; then
        echo "[ERROR] msfrpcd teamserver ${MSF_HOST}:${MSF_PORT} inaccessible après 300s"
        exit 1
    fi
fi

echo "[INFO] LHOST=${LHOST} LPORT=${LPORT}"

echo "[INFO] Launching thearm_uzi..."
exec /usr/bin/thearm_uzi
