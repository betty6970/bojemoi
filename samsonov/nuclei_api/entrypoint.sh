#!/bin/sh
set -e

# Update nuclei templates
nuclei -update-templates 2>/dev/null || true

# Route setup: RFC1918 via original GW, internet via wg-gateway (ProtonVPN)
ORIG_GW=$(ip route show default 2>/dev/null | head -1 | cut -d' ' -f3)
WG_GW=${SCAN_GATEWAY_HOST:-wg-gateway}
WG_IP=$(getent hosts "$WG_GW" 2>/dev/null | head -1 | cut -d' ' -f1)
if [ -n "$ORIG_GW" ] && [ -n "$WG_IP" ]; then
    ip route add 10.0.0.0/8     via "$ORIG_GW" 2>/dev/null || true
    ip route add 172.16.0.0/12  via "$ORIG_GW" 2>/dev/null || true
    ip route add 192.168.0.0/16 via "$ORIG_GW" 2>/dev/null || true
    ip route del default 2>/dev/null || true
    ip route add default via "$WG_IP"
    echo "[INFO] Nuclei scan via ProtonVPN: $WG_IP"
else
    echo "[WARN] VPN gateway not found (ORIG_GW=$ORIG_GW WG_IP=$WG_IP) — scan without VPN"
fi

# Nym Mixnet proxy pour les scans nuclei (SOCKS5 — HTTP uniquement, non nmap)
if [ -n "$NYM_PROXY" ]; then
    echo "[INFO] Nuclei proxy Nym activé: $NYM_PROXY"
    export NUCLEI_PROXY="$NYM_PROXY"
fi

exec python -m uvicorn main:app --host 0.0.0.0 --port 8001
