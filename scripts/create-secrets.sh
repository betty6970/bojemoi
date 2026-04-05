#!/bin/bash
# =============================================================================
# Bojemoi Lab — Docker Secrets Creator
# =============================================================================
# Creates all Docker Swarm secrets required by the stacks.
# Run this BEFORE deploying any stack.
#
# Usage:
#   ./scripts/create-secrets.sh             # Interactive — prompts for each secret
#   ./scripts/create-secrets.sh --list      # List all secrets and their status
#   ./scripts/create-secrets.sh --delete    # Delete all lab secrets (DESTRUCTIVE)
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR]${NC}  $*" >&2; }
header()  { echo -e "\n${BOLD}$*${NC}"; echo "$(printf '=%.0s' {1..50})"; }

# Create a secret from stdin or a file
# create_secret NAME "description" [--from-file PATH]
create_secret() {
  local name="$1" description="$2" from_file="${3:-}"

  if docker secret inspect "$name" &>/dev/null; then
    warn "Secret '$name' already exists — skipping"
    return 0
  fi

  if [ -n "$from_file" ]; then
    if [ ! -f "$from_file" ]; then
      error "File not found: $from_file"
      return 1
    fi
    docker secret create "$name" "$from_file" >/dev/null
    success "Created secret '$name' from file"
    return 0
  fi

  # Interactive prompt
  echo -e "${YELLOW}?${NC} ${BOLD}$name${NC} — $description"
  read -rsp "  Value (hidden): " value
  echo
  if [ -z "$value" ]; then
    warn "  Empty value — skipping '$name'"
    return 0
  fi
  printf '%s' "$value" | docker secret create "$name" - >/dev/null
  success "Created secret '$name'"
}

create_secret_file() {
  local name="$1" description="$2"
  echo -e "${YELLOW}?${NC} ${BOLD}$name${NC} — $description"
  read -rp "  File path: " fpath
  fpath="${fpath/#\~/$HOME}"
  if [ ! -f "$fpath" ]; then
    warn "  File not found — skipping '$name'"
    return 0
  fi
  if docker secret inspect "$name" &>/dev/null; then
    warn "Secret '$name' already exists — skipping"
    return 0
  fi
  docker secret create "$name" "$fpath" >/dev/null
  success "Created secret '$name' from $fpath"
}

# --list
list_secrets() {
  header "Docker Secrets Status"
  local all_secrets=(
    ssh_private_key telegram_bot_token telegram_alert_chat_id
    telegram_api_credentials telegram_api_id telegram_api_hash telegram_phone
    proton_username proton_password alertmanager_smtp_pass
    protonvpn_ovpn protonvpn_auth
    fly_api_token
    anthropic_api_key abuseipdb_api_key vt_api_key otx_api_key shodan_api_key
    mcp_pg_password mcp_faraday_password
    medved_pg_password medved_faraday_password
    postgres_password
    sentinel_mqtt_pass sentinel_pg_pass mosquitto_passwd_v2
  )
  local existing
  existing=$(docker secret ls --format '{{.Name}}' 2>/dev/null || true)

  printf "%-40s %s\n" "SECRET" "STATUS"
  printf "%-40s %s\n" "------" "------"
  for s in "${all_secrets[@]}"; do
    if echo "$existing" | grep -qx "$s"; then
      printf "%-40s ${GREEN}%s${NC}\n" "$s" "exists"
    else
      printf "%-40s ${RED}%s${NC}\n" "$s" "missing"
    fi
  done
}

# --delete
delete_secrets() {
  echo -e "${RED}WARNING: This will delete ALL Bojemoi lab secrets.${NC}"
  echo "Services using them will fail until secrets are recreated."
  read -rp "Type 'DELETE' to confirm: " confirm
  [ "$confirm" = "DELETE" ] || { info "Aborted."; exit 0; }

  local all_secrets=(
    ssh_private_key telegram_bot_token telegram_alert_chat_id
    telegram_api_credentials telegram_api_id telegram_api_hash telegram_phone
    proton_username proton_password alertmanager_smtp_pass
    protonvpn_ovpn protonvpn_auth
    fly_api_token
    anthropic_api_key abuseipdb_api_key vt_api_key otx_api_key shodan_api_key
    mcp_pg_password mcp_faraday_password
    medved_pg_password medved_faraday_password
    postgres_password
    sentinel_mqtt_pass sentinel_pg_pass mosquitto_passwd_v2
  )
  for s in "${all_secrets[@]}"; do
    docker secret rm "$s" 2>/dev/null && info "Deleted: $s" || true
  done
  success "Done."
}

# Parse args
case "${1:-}" in
  --list)   list_secrets; exit 0 ;;
  --delete) delete_secrets; exit 0 ;;
  --help|-h)
    echo "Usage: $0 [--list | --delete]"
    echo "  (no args)  Interactive secret creation"
    echo "  --list     Show which secrets exist"
    echo "  --delete   Delete all lab secrets (destructive)"
    exit 0 ;;
esac

# =============================================================================
# Interactive creation
# =============================================================================
echo -e "${BOLD}"
echo "╔══════════════════════════════════════════╗"
echo "║    Bojemoi Lab — Docker Secrets Setup    ║"
echo "╚══════════════════════════════════════════╝"
echo -e "${NC}"
echo "Secrets are created in Docker Swarm's encrypted store."
echo "Press Enter to skip optional secrets (they can be added later)."
echo

# --- Core infrastructure ---
header "SSH / Access"
create_secret "ssh_private_key" "SSH private key used by rsync-master/slave for inter-node sync"

# --- Telegram ---
header "Telegram"
create_secret "telegram_bot_token"        "Bot token from @BotFather (used by alertmanager + telegram-bot + uzi)"
create_secret "telegram_alert_chat_id"    "Alert chat ID (e.g. -5087117106) — used by uzi-service"
create_secret "telegram_api_credentials"  "MTProto API credentials file (used by razvedka/vigie)"
create_secret "telegram_api_id"           "Telegram API ID (integer) — used by razvedka"
create_secret "telegram_api_hash"         "Telegram API hash — used by razvedka"
create_secret "telegram_phone"            "Telegram phone number (+33...) — used by razvedka"

# --- Proton / Mail ---
header "Proton Mail Bridge"
create_secret "proton_username"        "Proton Mail username (email address)"
create_secret "proton_password"        "Proton Mail password"
create_secret "alertmanager_smtp_pass" "SMTP password from Proton Mail Bridge (copy from 'info' command)"

# --- VPN ---
header "ProtonVPN (outbound scan gateway)"
create_secret_file "protonvpn_ovpn" ".ovpn config file for ProtonVPN (TCP protocol)"
create_secret      "protonvpn_auth" "ProtonVPN credentials: two lines — username\\npassword"

# --- Fly.io ---
header "Fly.io (C2 redirectors)"
create_secret "fly_api_token" "Fly.io API token (from: fly auth token)"

# --- OSINT API keys ---
header "OSINT API Keys (all optional)"
create_secret "anthropic_api_key"  "Anthropic API key (used by nuclei AI template gen + uzi)"
create_secret "abuseipdb_api_key"  "AbuseIPDB API key (OSINT enrichment)"
create_secret "vt_api_key"         "VirusTotal API key (OSINT enrichment)"
create_secret "otx_api_key"        "AlienVault OTX API key (OSINT enrichment)"
create_secret "shodan_api_key"     "Shodan API key (OSINT enrichment)"

# --- MCP server ---
header "MCP Server"
create_secret "mcp_pg_password"      "PostgreSQL password for MCP server (same as POSTGRES_PASSWORD)"
create_secret "mcp_faraday_password" "Faraday password for MCP server (same as FARADAY_PASSWORD)"

# --- Medved ---
header "Medved"
create_secret "medved_pg_password"      "PostgreSQL password for Medved"
create_secret "medved_faraday_password" "Faraday password for Medved"

# --- PostgreSQL secret (some services use it as a Docker secret) ---
header "PostgreSQL secret"
create_secret "postgres_password" "PostgreSQL password (same value as POSTGRES_PASSWORD in .env)"

# --- Sentinel / MQTT ---
header "Sentinel / MQTT"
create_secret "sentinel_mqtt_pass"   "MQTT password for sentinel services"
create_secret "sentinel_pg_pass"     "PostgreSQL sentinel user password"
create_secret_file "mosquitto_passwd_v2" "Mosquitto password file (generated with mosquitto_passwd)"

# =============================================================================
echo
header "Summary"
list_secrets
echo
echo -e "${BOLD}Next step:${NC} run ${YELLOW}./install.sh --deploy-only${NC} to deploy the stacks."
