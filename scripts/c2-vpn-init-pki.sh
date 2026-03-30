#!/bin/bash
# c2-vpn-init-pki.sh — Initialize EasyRSA PKI for C2 VPN infrastructure
#
# Usage: ./c2-vpn-init-pki.sh [--rebuild]
#   --rebuild  : Wipe existing PKI and start fresh (DESTRUCTIVE)
#
# Output:
#   /opt/bojemoi/volumes/c2-vpn/pki/          — EasyRSA PKI tree
#   /opt/bojemoi/volumes/c2-vpn/server/       — Server certs/keys for bojemoi.me
#   /opt/bojemoi/volumes/c2-vpn/clients/      — Client configs
#   /opt/bojemoi/volumes/c2-vpn/ccd/          — CCD (client-config-dir) entries
#
# After running:
#   1. Copy /opt/bojemoi/volumes/c2-vpn/server/ to bojemoi.me
#   2. Run the OpenVPN server container on bojemoi.me
#   3. Connect lab-manager client: openvpn --config .../clients/lab-manager.ovpn

set -euo pipefail

PKI_DIR="/opt/bojemoi/volumes/c2-vpn"
EASYRSA_BIN="easyrsa"
VPN_SERVER="bojemoi.me"
VPN_PORT="1194"
VPN_PROTO="udp"
VPN_NETWORK="10.8.0.0"
VPN_NETMASK="255.255.0.0"
LAB_NETWORK="192.168.1.0"
LAB_NETMASK="255.255.255.0"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[-]${NC} $*" >&2; }

# Check EasyRSA
if ! command -v easyrsa &>/dev/null; then
    # Try common install locations
    for p in /usr/share/easy-rsa/easyrsa /usr/local/share/easy-rsa/easyrsa \
              /opt/easy-rsa/easyrsa /etc/openvpn/easy-rsa/easyrsa; do
        if [ -x "$p" ]; then
            EASYRSA_BIN="$p"
            break
        fi
    done
fi

if ! command -v "$EASYRSA_BIN" &>/dev/null && [ ! -x "$EASYRSA_BIN" ]; then
    err "EasyRSA not found. Install with: apk add easy-rsa  OR  apt install easy-rsa"
    exit 1
fi
log "Using EasyRSA: $EASYRSA_BIN"

# Handle --rebuild
if [ "${1:-}" = "--rebuild" ]; then
    warn "REBUILD mode: wiping existing PKI at $PKI_DIR/pki"
    rm -rf "$PKI_DIR/pki"
fi

# Create directory structure
mkdir -p "$PKI_DIR/pki" "$PKI_DIR/server" "$PKI_DIR/clients" "$PKI_DIR/ccd"

# Export vars for EasyRSA
export EASYRSA="$PKI_DIR"
export EASYRSA_PKI="$PKI_DIR/pki"
export EASYRSA_KEY_SIZE=4096
export EASYRSA_ALGO=rsa
export EASYRSA_DIGEST=sha256
export EASYRSA_CA_EXPIRE=3650
export EASYRSA_CERT_EXPIRE=825
export EASYRSA_BATCH=1
export EASYRSA_REQ_CN="C2-VPN-CA"

# ── Step 1: Init PKI ────────────────────────────────────────────────────────
if [ ! -f "$EASYRSA_PKI/ca.crt" ]; then
    log "Initializing PKI..."
    "$EASYRSA_BIN" init-pki
    log "Building CA (no passphrase for automation)..."
    "$EASYRSA_BIN" --batch build-ca nopass
    log "CA created: $EASYRSA_PKI/ca.crt"
else
    log "PKI already initialized, skipping init."
fi

# ── Step 2: DH params + TLS-auth key ────────────────────────────────────────
if [ ! -f "$EASYRSA_PKI/dh.pem" ]; then
    log "Generating DH parameters (2048-bit)..."
    "$EASYRSA_BIN" gen-dh
fi

if [ ! -f "$PKI_DIR/server/ta.key" ]; then
    log "Generating TLS-auth key..."
    openvpn --genkey --secret "$PKI_DIR/server/ta.key"
fi

# ── Step 3: Server certificate ──────────────────────────────────────────────
if [ ! -f "$EASYRSA_PKI/issued/c2-server.crt" ]; then
    log "Generating server certificate for bojemoi.me..."
    export EASYRSA_REQ_CN="c2-server"
    "$EASYRSA_BIN" --batch build-server-full c2-server nopass
    log "Server cert: $EASYRSA_PKI/issued/c2-server.crt"
else
    log "Server cert already exists, skipping."
fi

# ── Step 4: lab-manager client cert ─────────────────────────────────────────
if [ ! -f "$EASYRSA_PKI/issued/lab-manager.crt" ]; then
    log "Generating lab-manager client certificate..."
    export EASYRSA_REQ_CN="lab-manager"
    "$EASYRSA_BIN" --batch build-client-full lab-manager nopass
    log "lab-manager cert: $EASYRSA_PKI/issued/lab-manager.crt"
else
    log "lab-manager cert already exists, skipping."
fi

# ── Step 5: Copy server bundle ───────────────────────────────────────────────
log "Assembling server bundle in $PKI_DIR/server/..."
cp "$EASYRSA_PKI/ca.crt"              "$PKI_DIR/server/ca.crt"
cp "$EASYRSA_PKI/issued/c2-server.crt" "$PKI_DIR/server/server.crt"
cp "$EASYRSA_PKI/private/c2-server.key" "$PKI_DIR/server/server.key"
cp "$EASYRSA_PKI/dh.pem"              "$PKI_DIR/server/dh.pem"
chmod 600 "$PKI_DIR/server/server.key" "$PKI_DIR/server/ta.key"

# ── Step 6: Server openvpn.conf ──────────────────────────────────────────────
cat > "$PKI_DIR/server/openvpn.conf" << EOF
# OpenVPN server config — bojemoi.me C2 hub
port $VPN_PORT
proto $VPN_PROTO
dev tun

ca   /etc/openvpn/server/ca.crt
cert /etc/openvpn/server/server.crt
key  /etc/openvpn/server/server.key
dh   /etc/openvpn/server/dh.pem

tls-auth /etc/openvpn/server/ta.key 0

server $VPN_NETWORK $VPN_NETMASK
ifconfig-pool-persist /var/log/openvpn/ipp.txt
client-config-dir /etc/openvpn/ccd

# Push lab LAN route to all clients
push "route $LAB_NETWORK $LAB_NETMASK"
push "dhcp-option DNS 8.8.8.8"

# Allow lab-manager to route 192.168.1.0/24
route $LAB_NETWORK $LAB_NETMASK

duplicate-cn
keepalive 10 120
cipher AES-256-GCM
auth SHA256
tls-version-min 1.2
tls-cipher TLS-ECDHE-RSA-WITH-AES-256-GCM-SHA384

compress lz4-v2
push "compress lz4-v2"
max-clients 100
user nobody
group nogroup
persist-key
persist-tun

status /var/log/openvpn/status.log
log-append /var/log/openvpn/openvpn.log
verb 3
EOF

# ── Step 7: CCD for lab-manager ──────────────────────────────────────────────
cat > "$PKI_DIR/ccd/lab-manager" << EOF
# CCD for lab-manager — routes 192.168.1.0/24 through this client
iroute $LAB_NETWORK $LAB_NETMASK
EOF
log "CCD entry created: $PKI_DIR/ccd/lab-manager"

# ── Step 8: Generate lab-manager .ovpn ───────────────────────────────────────
generate_ovpn() {
    local CLIENT="$1"
    local OVPN="$PKI_DIR/clients/${CLIENT}.ovpn"

    CA=$(cat "$EASYRSA_PKI/ca.crt")
    CERT=$(openssl x509 -in "$EASYRSA_PKI/issued/${CLIENT}.crt" 2>/dev/null)
    KEY=$(cat "$EASYRSA_PKI/private/${CLIENT}.key")
    TA=$(cat "$PKI_DIR/server/ta.key")

    cat > "$OVPN" << OVPNEOF
client
dev tun
proto $VPN_PROTO
remote $VPN_SERVER $VPN_PORT
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-GCM
auth SHA256
tls-version-min 1.2
compress lz4-v2
verb 3

<ca>
${CA}
</ca>
<cert>
${CERT}
</cert>
<key>
${KEY}
</key>
<tls-auth>
${TA}
</tls-auth>
key-direction 1
OVPNEOF

    chmod 600 "$OVPN"
    log "Generated: $OVPN"
}

generate_ovpn "lab-manager"

# ── Step 9: Docker run command for bojemoi.me ─────────────────────────────────
log "─────────────────────────────────────────────────────────"
log "PKI initialized. Next steps:"
echo ""
echo "1. Copy server bundle to bojemoi.me:"
echo "   scp -r $PKI_DIR/server/ ec2-user@bojemoi.me:/opt/openvpn/"
echo "   scp -r $PKI_DIR/ccd/   ec2-user@bojemoi.me:/opt/openvpn/ccd/"
echo ""
echo "2. On bojemoi.me — run OpenVPN server:"
echo "   ssh -i /home/docker/LightsailDefaultKey-eu-central-1.pem ec2-user@bojemoi.me"
echo "   sudo docker run -d --name openvpn-c2 \\"
echo "     --cap-add=NET_ADMIN \\"
echo "     --device=/dev/net/tun \\"
echo "     -p 1194:1194/udp \\"
echo "     -v /opt/openvpn/server:/etc/openvpn/server:ro \\"
echo "     -v /opt/openvpn/ccd:/etc/openvpn/ccd:ro \\"
echo "     -v openvpn-logs:/var/log/openvpn \\"
echo "     --restart unless-stopped \\"
echo "     --sysctl net.ipv4.ip_forward=1 \\"
echo "     --sysctl net.ipv4.conf.all.accept_redirects=0 \\"
echo "     kylemanna/openvpn \\"
echo "     ovpn_run --config /etc/openvpn/server/openvpn.conf"
echo ""
echo "3. Start lab-manager VPN client (on meta-76):"
echo "   openvpn --config $PKI_DIR/clients/lab-manager.ovpn --daemon"
echo ""
echo "4. Provision first redirector:"
echo "   /opt/bojemoi/scripts/provision-redirector.sh redirector-1 hetzner hel1"
echo "─────────────────────────────────────────────────────────"
