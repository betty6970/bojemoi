#!/bin/sh
set -e

PG_USER="${PG_USER:-postgres}"
PG_PASSWORD="${PG_PASSWORD:-bojemoi}"
PG_HOST="${PG_HOST:-postgres}"
PG_DBNAME="${PG_DBNAME:-msf}"
MSF_PASS="totototo"
MSF_PORT=55553

# Create msf4 config dir and database.yml for msfrpcd
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

# Wait for msfrpcd to be ready (up to 120s)
echo "[INFO] Waiting for msfrpcd..."
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

echo "[INFO] Launching thearm_uzi..."
exec /usr/bin/thearm_uzi
