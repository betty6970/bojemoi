#!/bin/bash
set -euo pipefail

MSF_VPN_IP="${MSF_VPN_IP:-10.8.0.6}"
MSF_VPN_PORT="${MSF_VPN_PORT:-4444}"

log()  { echo "[+] $*"; }
warn() { echo "[!] $*" >&2; }

# ── TUN device ──────────────────────────────────────────────────────────────
mkdir -p /dev/net
[ -c /dev/net/tun ] || mknod /dev/net/tun c 10 200
chmod 666 /dev/net/tun
log "TUN device ready"

# ── VPN config ──────────────────────────────────────────────────────────────
mkdir -p /etc/openvpn
if [ -n "${VPN_CONFIG:-}" ]; then
    echo "$VPN_CONFIG" | base64 -d > /etc/openvpn/client.ovpn
elif [ -f "/etc/openvpn/client.ovpn" ]; then
    log "Using existing /etc/openvpn/client.ovpn"
else
    warn "VPN_CONFIG env var not set and no client.ovpn found"
    exit 1
fi

# ── TLS cert : Let's Encrypt via acme.sh, fallback self-signed amélioré ─────
mkdir -p /etc/nginx/ssl /var/www/acme

_gen_fallback_cert() {
    # Self-signed avec CN plausible au lieu de "localhost"
    openssl req -x509 -nodes -newkey ec -pkeyopt ec_paramgen_curve:P-256 \
        -days 365 \
        -keyout /etc/nginx/ssl/server.key \
        -out /etc/nginx/ssl/server.crt \
        -subj "/C=US/ST=Washington/L=Redmond/O=Microsoft Corporation/CN=api.microsoft.com" \
        -addext "subjectAltName=DNS:api.microsoft.com" \
        -addext "keyUsage=digitalSignature,keyEncipherment" \
        -addext "extendedKeyUsage=serverAuth" 2>/dev/null
    log "Fallback TLS certificate generated (CN=api.microsoft.com)"
}

if [ ! -f /etc/nginx/ssl/server.crt ]; then
    # Tenter d'obtenir un certificat Let's Encrypt via acme.sh
    APP_DOMAIN="${FLY_APP_NAME:-redirector-1}.fly.dev"
    log "Attempting Let's Encrypt cert for ${APP_DOMAIN}..."

    # Démarrer nginx temporairement pour servir le challenge ACME sur port 80
    envsubst '${MSF_VPN_IP} ${MSF_VPN_PORT}' \
        < /etc/nginx/nginx.conf > /etc/nginx/nginx.conf.tmp
    _gen_fallback_cert  # cert provisoire pour que nginx:443 démarre
    cp /etc/nginx/nginx.conf.tmp /etc/nginx/nginx.conf
    nginx -g 'daemon on;' 2>/dev/null
    sleep 8  # laisser Fly.io router le port 80 avant le challenge ACME

    ACME_HOME=/etc/acme.sh
    # Enregistrer le compte ACME d'abord (évite le problème d'email vide)
    acme.sh --home "$ACME_HOME" --register-account -m noreply@example.com 2>/dev/null || true
    if acme.sh --home "$ACME_HOME" \
               --issue -d "${APP_DOMAIN}" \
               --webroot /var/www/acme \
               --server letsencrypt \
               --keylength ec-256 2>&1 | tee /tmp/acme.log | grep -E "Cert|error|invalid|rate|Verif" >&2; then
        acme.sh --home "$ACME_HOME" \
                --install-cert -d "${APP_DOMAIN}" \
                --cert-file  /etc/nginx/ssl/server.crt \
                --key-file   /etc/nginx/ssl/server.key \
                --reloadcmd  "" 2>/dev/null
        log "Let's Encrypt cert installed for ${APP_DOMAIN}"
    else
        warn "Let's Encrypt failed (see /tmp/acme.log) — keeping fallback self-signed cert"
    fi

    nginx -s stop 2>/dev/null; sleep 1
fi

# ── nginx config with substituted MSF target ────────────────────────────────
export MSF_VPN_IP MSF_VPN_PORT
envsubst '${MSF_VPN_IP} ${MSF_VPN_PORT}' \
    < /etc/nginx/nginx.conf \
    > /etc/nginx/nginx.conf.rendered
mv /etc/nginx/nginx.conf.rendered /etc/nginx/nginx.conf

# ── Start OpenVPN ────────────────────────────────────────────────────────────
sysctl -w net.ipv4.ip_forward=1 2>/dev/null || true

openvpn --config /etc/openvpn/client.ovpn \
    --daemon \
    --log /var/log/openvpn.log \
    --writepid /run/openvpn.pid

# ── Wait for VPN tunnel ──────────────────────────────────────────────────────
log "Waiting for VPN tunnel (tun0)..."
for i in $(seq 1 30); do
    if ip link show tun0 >/dev/null 2>&1; then
        log "VPN tunnel up"
        break
    fi
    [ $i -eq 30 ] && { warn "VPN tunnel did not come up"; cat /var/log/openvpn.log; exit 1; }
    sleep 2
done

VPN_PEER_IP=$(ip route show | awk '/tun0/ {print $1}' | head -1 || echo "unknown")
log "VPN route: $VPN_PEER_IP via tun0"
log "MSF target: ${MSF_VPN_IP}:${MSF_VPN_PORT}"

# ── Test nginx config ────────────────────────────────────────────────────────
nginx -t

# ── Nginx logs → real file (for Loki shipper) + tail to stdout (fly logs) ───
mkdir -p /var/log/nginx
touch /var/log/nginx/access.log /var/log/nginx/error.log
tail -F /var/log/nginx/access.log &
tail -F /var/log/nginx/error.log >&2 &

# ── Start Loki log shipper (via VPN) ─────────────────────────────────────────
if [ -n "${LOKI_URL:-}" ] || ip link show tun0 >/dev/null 2>&1; then
    log "Starting Loki log shipper → ${LOKI_URL:-http://192.168.1.121:3100/loki/api/v1/push}"
    python3 /usr/bin/loki-shipper.pyc &
fi

# ── Start nginx (foreground) ─────────────────────────────────────────────────
log "Starting nginx..."
nginx -g 'daemon off;'
