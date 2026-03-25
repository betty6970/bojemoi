#!/bin/sh
set -e

# Read Docker secrets into env vars
if [ -f /run/secrets/telegram_bot_token ]; then
    export TELEGRAM_BOT_TOKEN=$(cat /run/secrets/telegram_bot_token)
fi
if [ -f /run/secrets/discovery_db_password ]; then
    export DB_PASS=$(cat /run/secrets/discovery_db_password)
fi

# Start Tor in background
echo "[entrypoint] Starting Tor..."
tor &
TOR_PID=$!
sleep 10

# Verify Tor is alive
if ! kill -0 "$TOR_PID" 2>/dev/null; then
    echo "[entrypoint] WARNING: Tor failed to start, running without proxy"
    unset PROXY_URL
fi

# Discovery loop
INTERVAL=${SCHEDULE_INTERVAL:-3600}
echo "[entrypoint] Starting discovery loop (interval: ${INTERVAL}s)"

while true; do
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Running discovery sweep..."
    python /app/breachforum_onion_discovery.pyc || echo "[entrypoint] Sweep exited with error, will retry"
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Next run in ${INTERVAL}s"
    sleep "${INTERVAL}"
done
