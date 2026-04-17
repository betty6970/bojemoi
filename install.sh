#!/bin/bash
# =============================================================================
# Bojemoi Lab — Bootstrap Installer
# =============================================================================
# Usage:
#   ./install.sh           Interactive setup → generates .env → deploys stacks
#   ./install.sh --env-only   Generate .env only, no deployment
#   ./install.sh --deploy-only  Deploy using existing .env
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"

# -----------------------------------------------------------------------------
# Colors
# -----------------------------------------------------------------------------
RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC}  $*" >&2; }
header()  { echo -e "\n${BOLD}$*${NC}"; echo "$(printf '=%.0s' {1..60})"; }

# -----------------------------------------------------------------------------
# Argument parsing
# -----------------------------------------------------------------------------
ENV_ONLY=false
DEPLOY_ONLY=false
for arg in "$@"; do
  case "$arg" in
    --env-only)    ENV_ONLY=true ;;
    --deploy-only) DEPLOY_ONLY=true ;;
    --help|-h)
      echo "Usage: $0 [--env-only | --deploy-only]"
      echo "  --env-only     Generate .env without deploying"
      echo "  --deploy-only  Deploy using existing .env (skip interactive setup)"
      exit 0 ;;
  esac
done

# -----------------------------------------------------------------------------
# Helper: prompt with default
# ask VAR "Question" "default"
# -----------------------------------------------------------------------------
ask() {
  local var="$1" question="$2" default="${3:-}"
  local prompt
  if [ -n "$default" ]; then
    prompt="$question [${default}]: "
  else
    prompt="$question: "
  fi
  read -rp "$(echo -e "${YELLOW}?${NC} $prompt")" value
  value="${value:-$default}"
  eval "$var='$value'"
}

ask_secret() {
  local var="$1" question="$2"
  read -rsp "$(echo -e "${RED}*${NC} $question: ")" value
  echo
  eval "$var='$value'"
}

# -----------------------------------------------------------------------------
# Step 1: Interactive configuration
# -----------------------------------------------------------------------------
interactive_setup() {
  header "Bojemoi Lab — Configuration"
  echo "This wizard generates your .env file."
  echo "Press Enter to accept defaults shown in [brackets]."
  echo

  # --- Network & Domains ---
  header "Network & Domains"
  ask LAB_DOMAIN     "Internal lab domain (Traefik labels, DNS search)" "bojemoi.lab"
  ask PUBLIC_DOMAIN  "External public domain (C2 VPN, Lightsail)" "bojemoi.me"
  ask MANAGER_IP     "Swarm manager IP address" "192.168.1.121"
  ask SCAN_NET_CIDR  "Scan overlay network subnet" "10.11.0.0/24"

  # --- Registry ---
  header "Docker Registry"
  ask IMAGE_REGISTRY "Local registry (host:port)" "localhost:5000"

  # --- Paths ---
  header "Paths"
  ask BOJEMOI_BASE_PATH "Project root path on disk" "/opt/bojemoi"

  # --- Passwords ---
  header "Passwords (will be written to .env — keep it secret)"
  ask_secret POSTGRES_PASSWORD  "PostgreSQL password"
  ask_secret GRAFANA_ADMIN_PASSWORD "Grafana admin password"
  ask_secret PGADMIN_PASSWORD   "PgAdmin password"
  ask_secret DEFECTDOJO_ADMIN_PASSWORD "DefectDojo admin password"
  ask_secret MSF_RPC_PASSWORD   "Metasploit RPC password"
  ask_secret KARACHO_SECRET_KEY "Karacho secret key"

  # --- Emails ---
  header "Misc"
  ask PGADMIN_EMAIL   "PgAdmin login email" "admin@admin.com"
  ask TELEGRAM_CHAT_ID "Telegram alert chat ID" ""
  ask TZ              "Timezone" "Europe/Paris"

  # --- C2 / Redirectors ---
  header "C2 / Redirectors (leave empty if not used)"
  ask C2_REDIRECTORS      "Redirector public IPs (comma-separated)" ""
  ask LIGHTSAIL_HOST      "Lightsail / VPN server hostname" "$PUBLIC_DOMAIN"
  ask LIGHTSAIL_USER      "Lightsail SSH user" "ec2-user"
  ask LIGHTSAIL_KEY_PATH  "Lightsail SSH key path" "/home/docker/LightsailDefaultKey-eu-central-1.pem"
  ask FLY_CLI_PATH        "Fly.io CLI path" "/home/docker/.fly/bin/fly"
  ask FLY_APP             "Fly.io redirector app name" "redirector-1"

  # --- OSINT API keys (optional) ---
  header "Optional OSINT API Keys (press Enter to skip)"
  ask ABUSEIPDB_API_KEY  "AbuseIPDB API key" ""
  ask VIRUSTOTAL_API_KEY "VirusTotal API key" ""
  ask SHODAN_API_KEY     "Shodan API key" ""
  ask ANTHROPIC_API_KEY  "Anthropic API key" ""

  # --- Swarm node labels ---
  header "Swarm Node Hostnames"
  ask SWARM_MANAGER_HOSTNAME   "Manager node hostname" "meta-76"
  ask SURICATA_NODE_HOSTNAME   "Node running Suricata" "meta-70"
  ask LOGPULL_NODE_HOSTNAME    "Node running logpull" "meta-76"
}

# -----------------------------------------------------------------------------
# Step 2: Write .env
# -----------------------------------------------------------------------------
write_env() {
  info "Writing $ENV_FILE ..."

  # Derive dependent values
  local pg_exporter_dsn="postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD}@postgres:5432/postgres?sslmode=disable"

  cat > "$ENV_FILE" <<EOF
# =============================================================================
# Bojemoi Lab — Runtime Configuration
# Generated by install.sh on $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# DO NOT commit this file to git.
# =============================================================================

# Network / Domains
LAB_DOMAIN=${LAB_DOMAIN:-bojemoi.lab}
PUBLIC_DOMAIN=${PUBLIC_DOMAIN:-bojemoi.me}
MANAGER_IP=${MANAGER_IP:-192.168.1.121}
SCAN_NET_CIDR=${SCAN_NET_CIDR:-10.11.0.0/24}

# Docker Registry
IMAGE_REGISTRY=${IMAGE_REGISTRY:-localhost:5000}

# Paths
BOJEMOI_BASE_PATH=${BOJEMOI_BASE_PATH:-/opt/bojemoi}

# PostgreSQL
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_USER=${POSTGRES_USER:-postgres}
MSF_DBNAME=${MSF_DBNAME:-msf}
GRAFANA_DBNAME=${GRAFANA_DBNAME:-grafana}
IP2LOC_DBNAME=${IP2LOC_DBNAME:-ip2location}
KARACHO_DBNAME=${KARACHO_DBNAME:-karacho}
FARADAY_DBNAME=${FARADAY_DBNAME:-faraday}
ML_THREAT_DBNAME=${ML_THREAT_DBNAME:-bojemoi_threat_intel}
PG_EXPORTER_DSN=${pg_exporter_dsn}

# Grafana
GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
SENTINEL_PG_PASS=${SENTINEL_PG_PASS:-changeme}

# PgAdmin
PGADMIN_EMAIL=${PGADMIN_EMAIL:-admin@admin.com}
PGADMIN_PASSWORD=${PGADMIN_PASSWORD}

# DefectDojo
DEFECTDOJO_URL=${DEFECTDOJO_URL:-http://defectdojo:8080}
DEFECTDOJO_ADMIN_USER=${DEFECTDOJO_ADMIN_USER:-admin}
DEFECTDOJO_ADMIN_PASSWORD=${DEFECTDOJO_ADMIN_PASSWORD}
DEFECTDOJO_PRODUCT_ZAP=${DEFECTDOJO_PRODUCT_ZAP:-ZAP Scans}
DEFECTDOJO_PRODUCT_NUCLEI=${DEFECTDOJO_PRODUCT_NUCLEI:-Nuclei Scans}
DEFECTDOJO_PRODUCT_UZI=${DEFECTDOJO_PRODUCT_UZI:-MSF Exploitation}

# Metasploit
MSF_RPC_PORT=${MSF_RPC_PORT:-55553}
MSF_RPC_PASSWORD=${MSF_RPC_PASSWORD}
MSF_HOST=${MSF_HOST:-msf-teamserver}
MSF_LPORT=${MSF_LPORT:-4444}
MSF_LPORT_BIND=${MSF_LPORT_BIND:-24444}

# C2 / Redirectors
C2_REDIRECTORS=${C2_REDIRECTORS:-}
RELAY_PORT=${RELAY_PORT:-8443}
VPN_SERVER=${VPN_SERVER:-${PUBLIC_DOMAIN:-bojemoi.me}}
VPN_NETWORK=${VPN_NETWORK:-10.8.0.0}
VPN_NETMASK=${VPN_NETMASK:-255.255.0.0}
DECOY_REDIRECT=${DECOY_REDIRECT:-https://www.google.com}
ALLOWED_COUNTRIES=${ALLOWED_COUNTRIES:-FR,DE,BE,NL,IT,ES,GB,CH,AT,PL,SE,DK,NO,FI,PT,IE,CZ,SK,HU,RO}
C2_VPN_DIR=${C2_VPN_DIR:-${BOJEMOI_BASE_PATH:-/opt/bojemoi}/volumes/c2-vpn}

# Lightsail / External VPS
LIGHTSAIL_HOST=${LIGHTSAIL_HOST:-${PUBLIC_DOMAIN:-bojemoi.me}}
LIGHTSAIL_USER=${LIGHTSAIL_USER:-ec2-user}
LIGHTSAIL_KEY_PATH=${LIGHTSAIL_KEY_PATH:-/home/docker/LightsailDefaultKey-eu-central-1.pem}

# Fly.io
FLY_CLI_PATH=${FLY_CLI_PATH:-/home/docker/.fly/bin/fly}
FLY_APP=${FLY_APP:-redirector-1}
FLY_LOG_LINES=${FLY_LOG_LINES:-2000}
LIGHTSAIL_LOG_LINES=${LIGHTSAIL_LOG_LINES:-5000}

# Telegram
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-}

# Ollama / AI
OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://ollama:11434}
OLLAMA_MODEL=${OLLAMA_MODEL:-mistral:7b-instruct}
OLLAMA_ENABLED=${OLLAMA_ENABLED:-true}
OLLAMA_TIMEOUT=${OLLAMA_TIMEOUT:-30}

# Optional OSINT API Keys
ABUSEIPDB_API_KEY=${ABUSEIPDB_API_KEY:-}
VIRUSTOTAL_API_KEY=${VIRUSTOTAL_API_KEY:-}
SHODAN_API_KEY=${SHODAN_API_KEY:-}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}

# Karacho
KARACHO_SECRET_KEY=${KARACHO_SECRET_KEY}

# Mail
MAIL_DOMAIN=${MAIL_DOMAIN:-${LAB_DOMAIN:-bojemoi.lab}}

# Swarm node labels
SWARM_MANAGER_HOSTNAME=${SWARM_MANAGER_HOSTNAME:-meta-76}
SURICATA_NODE_HOSTNAME=${SURICATA_NODE_HOSTNAME:-meta-70}
LOGPULL_NODE_HOSTNAME=${LOGPULL_NODE_HOSTNAME:-meta-76}

# ZAP
TARGET_URL=${TARGET_URL:-https://zap.${LAB_DOMAIN:-bojemoi.lab}}
ZAP_API_KEY=${ZAP_API_KEY:-}

# Masscan
TARGET_COUNTRY=${TARGET_COUNTRY:-RU}
TARGET_ISP=${TARGET_ISP:-}
SCAN_PORTS=${SCAN_PORTS:-22,80,443,3389,5985,8080,8443}
SCAN_RATE=${SCAN_RATE:-10000}
MAX_CIDRS=${MAX_CIDRS:-50}

# Timezone
TZ=${TZ:-Europe/Paris}
EOF

  chmod 600 "$ENV_FILE"
  success ".env written (permissions: 600)"
}

# -----------------------------------------------------------------------------
# Step 3: Deploy stacks in order
# -----------------------------------------------------------------------------
deploy_stacks() {
  header "Deployment"

  if [ ! -f "$ENV_FILE" ]; then
    error ".env not found. Run without --deploy-only first."
    exit 1
  fi

  # Load env
  set -a && source "$ENV_FILE" && set +a

  # Verify Docker Swarm
  if ! docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null | grep -q "active"; then
    error "Docker Swarm is not active. Initialize with: docker swarm init"
    exit 1
  fi

  local registry="${IMAGE_REGISTRY:-localhost:5000}"

  # Create overlay networks if missing
  info "Creating overlay networks..."
  for net in monitoring backend frontend proxy mail rsync_network; do
    docker network inspect "$net" &>/dev/null || \
      docker network create --driver overlay --attachable "$net" && \
      info "  created: $net" || true
  done

  # Deploy stacks in dependency order
  local stacks=(
    "base:stack/01-service-hl.yml"
  )

  # Optional stacks (deploy if image exists in registry)
  local optional_stacks=(
    "borodino:stack/40-service-borodino.yml"
    "ml-threat:stack/45-service-ml-threat-intel.yml"
    "razvedka:stack/46-service-razvedka.yml"
    "vigie:stack/47-service-vigie.yml"
    "dozor:stack/48-service-dozor.yml"
    "mcp:stack/49-service-mcp.yml"
    "trivy:stack/50-service-trivy.yml"
    "ollama:stack/51-service-ollama.yml"
    "sentinel:stack/55-service-sentinel.yml"
    "dvar:stack/56-service-dvar.yml"
    "telegram:stack/60-service-telegram.yml"
    "medved:stack/65-service-medved.yml"
    "dojo:stack/70-service-defectdojo.yml"
  )

  header "Deploying base stack"
  for entry in "${stacks[@]}"; do
    local name="${entry%%:*}"
    local file="${entry##*:}"
    if [ ! -f "$SCRIPT_DIR/$file" ]; then
      warn "Stack file not found: $file — skipping"
      continue
    fi
    info "Deploying stack: $name ($file)"
    docker stack deploy \
      -c "$SCRIPT_DIR/$file" "$name" \
      --prune --resolve-image always \
      && success "  $name deployed" \
      || error "  $name failed — check: docker service ls"
  done

  header "Deploying optional stacks"
  for entry in "${optional_stacks[@]}"; do
    local name="${entry%%:*}"
    local file="${entry##*:}"
    if [ ! -f "$SCRIPT_DIR/$file" ]; then
      warn "Stack file not found: $file — skipping"
      continue
    fi
    read -rp "$(echo -e "${YELLOW}?${NC} Deploy stack '$name'? [y/N]: ")" yn
    case "$yn" in
      [yY]*)
        info "Deploying stack: $name ($file)"
        docker stack deploy \
          -c "$SCRIPT_DIR/$file" "$name" \
          --prune --resolve-image always \
          && success "  $name deployed" \
          || error "  $name failed — check: docker service ls"
        ;;
      *) info "  Skipping $name" ;;
    esac
  done
}

# -----------------------------------------------------------------------------
# Step 4: Post-install summary
# -----------------------------------------------------------------------------
print_summary() {
  local domain="${LAB_DOMAIN:-bojemoi.lab}"
  header "Deployment Complete"
  echo -e "${GREEN}Services should be available at:${NC}"
  echo "  https://grafana.$domain"
  echo "  https://prometheus.$domain"
  echo "  https://defectdojo.$domain"
  echo "  https://pgadmin.$domain"
  echo "  https://alertmanager.$domain"
  echo "  https://redis.$domain"
  echo
  echo -e "${YELLOW}Next steps:${NC}"
  echo "  1. Configure DNS/hosts for *.$domain → ${MANAGER_IP:-<manager-ip>}"
  echo "  2. Create Docker secrets: see volumes/secrets/ or bojemoi_boot scripts"
  echo "  3. Check service health: docker service ls"
  echo "  4. View logs: docker service logs -f <service>"
  echo
  echo -e "${BOLD}.env file:${NC} $ENV_FILE  (keep it secret, never commit)"
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
  echo -e "${BOLD}"
  echo "╔══════════════════════════════════════════╗"
  echo "║       Bojemoi Lab — Install Script       ║"
  echo "╚══════════════════════════════════════════╝"
  echo -e "${NC}"

  if $DEPLOY_ONLY; then
    deploy_stacks
    print_summary
    exit 0
  fi

  if ! $ENV_ONLY; then
    # Check for existing .env
    if [ -f "$ENV_FILE" ]; then
      warn ".env already exists."
      read -rp "$(echo -e "${YELLOW}?${NC} Overwrite it? [y/N]: ")" yn
      [[ "$yn" =~ ^[yY] ]] || { info "Keeping existing .env"; source "$ENV_FILE"; deploy_stacks; print_summary; exit 0; }
    fi
  fi

  interactive_setup
  write_env

  if $ENV_ONLY; then
    success "Done. Run './install.sh --deploy-only' to deploy."
    exit 0
  fi

  echo
  read -rp "$(echo -e "${YELLOW}?${NC} Proceed with deployment now? [y/N]: ")" yn
  if [[ "$yn" =~ ^[yY] ]]; then
    deploy_stacks
    print_summary
  else
    success "Configuration saved. Run './install.sh --deploy-only' to deploy later."
  fi
}

main
