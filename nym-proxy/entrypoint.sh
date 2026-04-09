#!/bin/sh
set -e

NYM_ID="${NYM_ID:-bojemoi-lab}"
NYM_PROVIDER="${NYM_PROVIDER:?NYM_PROVIDER is required — set a Nym Network Requester address}"
NYM_PORT="${NYM_PORT:-1080}"

CONFIG_FILE="/root/.nym/socks5-clients/${NYM_ID}/config/config.toml"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "[nym-proxy] Init identité '${NYM_ID}'..."
    nym-socks5-client init \
        --id "$NYM_ID" \
        --provider "$NYM_PROVIDER"

    # Bind sur 0.0.0.0 pour accepter les connexions des autres conteneurs Docker
    sed -i "s/127\.0\.0\.1:${NYM_PORT}/0.0.0.0:${NYM_PORT}/g" "$CONFIG_FILE"
    sed -i "s/host = \"127\.0\.0\.1\"/host = \"0.0.0.0\"/g" "$CONFIG_FILE"

    echo "[nym-proxy] Config écrite : $CONFIG_FILE"
fi

echo "[nym-proxy] Démarrage SOCKS5 sur 0.0.0.0:${NYM_PORT} via Nym Mixnet..."
exec nym-socks5-client run --id "$NYM_ID"
