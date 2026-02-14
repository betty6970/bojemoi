#!/bin/bash

DIR="/opt/bojemoi"
ALERTMANAGER_URL="http://alertmanager.bojemoi.lab:9093"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Créer un silence Alertmanager pour la durée du déploiement
create_silence() {
    local duration_minutes=${1:-30}
    local comment=${2:-"Deployment in progress"}

    local start_time=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
    local end_time=$(date -u -d "+${duration_minutes} minutes" +"%Y-%m-%dT%H:%M:%S.000Z")

    log_info "Creating Alertmanager silence for ${duration_minutes} minutes..."

    local response=$(curl -s -X POST "${ALERTMANAGER_URL}/api/v2/silences" \
        -H "Content-Type: application/json" \
        -d "{
            \"matchers\": [{
                \"name\": \"alertname\",
                \"value\": \".*\",
                \"isRegex\": true,
                \"isEqual\": true
            }],
            \"startsAt\": \"${start_time}\",
            \"endsAt\": \"${end_time}\",
            \"createdBy\": \"startover.sh\",
            \"comment\": \"${comment}\"
        }" 2>/dev/null)

    if echo "$response" | grep -q "silenceID"; then
        SILENCE_ID=$(echo "$response" | grep -o '"silenceID":"[^"]*"' | cut -d'"' -f4)
        log_info "Silence created: ${SILENCE_ID}"
        echo "$SILENCE_ID"
    else
        log_warn "Could not create silence (Alertmanager may not be ready)"
        echo ""
    fi
}

# Supprimer un silence Alertmanager
delete_silence() {
    local silence_id=$1
    if [ -n "$silence_id" ]; then
        log_info "Removing silence: ${silence_id}"
        curl -s -X DELETE "${ALERTMANAGER_URL}/api/v2/silence/${silence_id}" 2>/dev/null
    fi
}

# Déployer un stack avec gestion d'erreur
deploy_stack() {
    local stack_file=$1
    local stack_name=$2
    local wait_time=${3:-15}

    log_info "Deploying stack: ${stack_name}"
    if docker stack deploy -c "$stack_file" "$stack_name" --prune; then
        log_info "Stack ${stack_name} deployed successfully"
        [ "$wait_time" -gt 0 ] && sleep "$wait_time"
        return 0
    else
        log_error "Failed to deploy stack: ${stack_name}"
        return 1
    fi
}

# === MAIN ===
log_info "Starting full deployment..."

# Créer silence pour 30 minutes
SILENCE_ID=$(create_silence 30 "Full stack deployment - startover.sh")

# Déployer les stacks
deploy_stack "${DIR}_boot/stack/01-boot-service.yml" "boot" 15
deploy_stack "$DIR/stack/01-service-hl.yml" "base" 15
deploy_stack "$DIR/stack/40-service-borodino.yml" "borodino" 15
deploy_stack "$DIR/stack/45-service-ml-threat-intel.yml" "ml-threat" 15
deploy_stack "${DIR}/stack/60-service-telegram.yml" "telegram" 5	
deploy_stack "${DIR}/stack/65-service-medved.yml" "honeypot" 5

# Deploy suricata standalone (needs network_mode: host, not supported in Swarm)
log_info "Deploying suricata (standalone docker compose)..."
docker compose -f "$DIR/stack/01-suricata-host.yml" up -d

# Afficher le statut
log_info "Deployment complete. Services status:"
docker service ls

# Optionnel: supprimer le silence immédiatement après déploiement
# delete_silence "$SILENCE_ID"
log_info "Alert silence will expire automatically in ~25 minutes"
