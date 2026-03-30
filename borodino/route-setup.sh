#!/bin/sh
# route-setup.sh — wrapper de démarrage pour ak47/bm12
# Redirige le trafic internet via wg-gateway (scan_net) avant de lancer le scanner
# Le trafic Docker overlay (postgres, redis) reste sur le gateway backend d'origine

WG_GW_HOST="${SCAN_GATEWAY_HOST:-wg-gateway}"

# Sauvegarder la route par défaut actuelle (backend overlay)
ORIG_GW=$(ip route show default 2>/dev/null | awk 'NR==1 {print $3}')

if [ -z "$ORIG_GW" ]; then
    echo "[WARN] Impossible de détecter la route par défaut — scan sans VPN"
    exec "$@"
fi

# Résoudre l'IP du gateway VPN sur scan_net
WG_IP=$(getent hosts "$WG_GW_HOST" 2>/dev/null | awk 'NR==1 {print $1}')

if [ -z "$WG_IP" ]; then
    echo "[WARN] $WG_GW_HOST non résolvable — scan sans VPN (orig gw: $ORIG_GW)"
    exec "$@"
fi

echo "[INFO] Routage scan via VPN gateway: $WG_IP (orig: $ORIG_GW)"

# Conserver les routes RFC1918 via le gateway backend (postgres, redis, overlay)
ip route add 10.0.0.0/8     via "$ORIG_GW" 2>/dev/null || true
ip route add 172.16.0.0/12  via "$ORIG_GW" 2>/dev/null || true
ip route add 192.168.0.0/16 via "$ORIG_GW" 2>/dev/null || true

# Remplacer la route par défaut par le gateway VPN
ip route del default 2>/dev/null || true
ip route add default via "$WG_IP"

echo "[INFO] Route par défaut → $WG_IP (ProtonVPN via wg-gateway)"

exec "$@"
