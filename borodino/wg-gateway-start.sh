#!/bin/bash
# wg-gateway-start.sh — OpenVPN gateway pour scan sortant
# Connecte à ProtonVPN et NAT le trafic scan_net via le tunnel
set -e

OVPN_SECRET=/run/secrets/protonvpn_ovpn
AUTH_SECRET=/run/secrets/protonvpn_auth

if [ ! -f "$OVPN_SECRET" ]; then
    echo "[ERROR] Secret 'protonvpn_ovpn' introuvable — crée le avec:"
    echo "  docker secret create protonvpn_ovpn /chemin/vers/fr.protonvpn.tcp.ovpn"
    exit 1
fi

if [ ! -f "$AUTH_SECRET" ]; then
    echo "[ERROR] Secret 'protonvpn_auth' introuvable — crée le avec:"
    echo "  printf 'USERNAME\\nPASSWORD\\n' | docker secret create protonvpn_auth -"
    echo "  (credentials OpenVPN/IKEv2 depuis account.protonvpn.com)"
    exit 1
fi

# Créer le device tun si absent
mkdir -p /dev/net
[ -c /dev/net/tun ] || mknod /dev/net/tun c 10 200
chmod 666 /dev/net/tun

mkdir -p /etc/openvpn
cp "$OVPN_SECRET" /etc/openvpn/client.ovpn
chmod 600 /etc/openvpn/client.ovpn

# Activer l'IP forwarding (déjà configuré via sysctls: dans le service YAML)
sysctl -w net.ipv4.ip_forward=1 2>/dev/null || true

echo "[INFO] Démarrage du tunnel OpenVPN ProtonVPN..."
openvpn --config /etc/openvpn/client.ovpn \
    --auth-user-pass "$AUTH_SECRET" \
    --daemon \
    --log /var/log/openvpn.log \
    --writepid /run/openvpn.pid

# Attendre que tun0 monte (max 45s)
echo "[INFO] Attente interface tun0..."
i=0
while [ $i -lt 45 ]; do
    ip link show tun0 >/dev/null 2>&1 && break
    sleep 1
    i=$((i+1))
done

if ! ip link show tun0 >/dev/null 2>&1; then
    echo "[ERROR] tun0 non monté après 45s — logs OpenVPN:"
    cat /var/log/openvpn.log 2>/dev/null || true
    exit 1
fi

echo "[INFO] Tunnel OpenVPN UP"
ip addr show tun0

# NAT : tout le trafic arrivant de scan_net sort via tun0
iptables -t nat -A POSTROUTING -o tun0 -j MASQUERADE
iptables -A FORWARD -i eth0 -o tun0 -j ACCEPT
iptables -A FORWARD -i tun0 -o eth0 -m state --state RELATED,ESTABLISHED -j ACCEPT

VPN_EXIT=$(curl -4 -s --max-time 10 https://api.ipify.org 2>/dev/null || echo "inconnu")
echo "[INFO] Gateway prêt — IP de sortie VPN: ${VPN_EXIT}"

exec tail -f /dev/null
