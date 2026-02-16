#!/bin/ash

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

# Déterminer si on est sur un manager ou un worker
NODE_ROLE=$(docker info --format '{{.Swarm.ControlAvailable}}')

if [ "$NODE_ROLE" = "true" ]; then
    log_info "Running on manager node - full deployment"

    # Créer silence pour 30 minutes
    SILENCE_ID=$(create_silence 30 "Full stack deployment - startover.sh")

    # Déployer les stacks
    deploy_stack "${DIR}_boot/stack/01-boot-service.yml" "boot" 15
    deploy_stack "$DIR/stack/01-service-hl.yml" "base" 15
    deploy_stack "$DIR/stack/40-service-borodino.yml" "borodino" 15
    deploy_stack "$DIR/stack/45-service-ml-threat-intel.yml" "ml-threat" 15
    deploy_stack "$DIR/stack/46-service-razvedka.yml" "razvedka" 10
    deploy_stack "$DIR/stack/47-service-vigie.yml" "vigie" 10
    deploy_stack "$DIR/stack/48-service-dozor.yml" "dozor" 10
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

    # === POST-DEPLOY: Monitor (service health) ===
    log_info "=== Service Health Check ==="
    docker service ls --format "{{.Name}} {{.Replicas}}" > /tmp/_svc_status
    FAILED_SERVICES=0
    while IFS= read -r line; do
        NAME=$(echo "$line" | awk '{print $1}')
        REPLICAS=$(echo "$line" | awk '{print $2}')
        CURRENT=$(echo "$REPLICAS" | cut -d'/' -f1)
        DESIRED=$(echo "$REPLICAS" | cut -d'/' -f2)
        if [ "$CURRENT" != "$DESIRED" ]; then
            log_warn "  $NAME: $REPLICAS (unhealthy)"
            FAILED_SERVICES=$((FAILED_SERVICES + 1))
        fi
    done < /tmp/_svc_status
    rm -f /tmp/_svc_status
    if [ "$FAILED_SERVICES" -eq 0 ]; then
        log_info "All services healthy"
    else
        log_warn "${FAILED_SERVICES} service(s) not at desired replica count"
    fi

    # === POST-DEPLOY: Connectivity (external feeds & APIs) ===
    log_info "=== Connectivity Check ==="
    CONN_OK=0
    CONN_FAIL=0

    check_url() {
        local label=$1
        local url=$2
        local http_code
        http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null)
        if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 400 ]; then
            log_info "  [OK]   $label ($http_code)"
            CONN_OK=$((CONN_OK + 1))
        else
            log_error "  [FAIL] $label ($http_code)"
            CONN_FAIL=$((CONN_FAIL + 1))
        fi
    }

    # Public feeds
    check_url "CERT-FR alerte" "https://cert.ssi.gouv.fr/alerte/feed/"
    check_url "FireHOL L1" "https://raw.githubusercontent.com/firehol/blocklist-ipsets/master/firehol_level1.netset"
    check_url "ThreatFox" "https://threatfox.abuse.ch/export/csv/ip-port/recent/"
    check_url "URLhaus" "https://urlhaus.abuse.ch/downloads/text_online/"
    check_url "Feodo Tracker" "https://feodotracker.abuse.ch/downloads/ipblocklist_recommended.txt"
    check_url "IP-API" "http://ip-api.com/json/8.8.8.8"

    # Authenticated APIs (read keys from worker containers)
    SSH_OPTS="-p 4422 -i /home/docker/.ssh/meta76_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=5"
    ML_NODE=$(docker service ps ml-threat_ml-threat-intel-api --format "{{.Node}}" --filter "desired-state=running" 2>/dev/null | head -1)
    if [ -n "$ML_NODE" ]; then
        ML_IP=$(docker node inspect "$ML_NODE" --format '{{.Status.Addr}}' 2>/dev/null)
        SECRETS=$(ssh $SSH_OPTS docker@"$ML_IP" \
            "ML=\$(docker ps -q -f name=ml-threat_ml-threat-intel-api | head -1) && \
             echo VT=\$(docker exec \$ML cat /run/secrets/vt_api_key 2>/dev/null || echo MISSING) && \
             echo SHODAN=\$(docker exec \$ML cat /run/secrets/shodan_api_key 2>/dev/null || echo MISSING) && \
             echo ANTHROPIC=\$(docker exec \$ML cat /run/secrets/anthropic_api_key 2>/dev/null || echo MISSING)" 2>/dev/null)
        eval "$SECRETS"

        is_real_key() { case "$1" in MISSING|your_*|CHANGE_ME*|changeme*|xxx*|TODO*|"") return 1 ;; *) [ ${#1} -ge 10 ] ;; esac; }

        if is_real_key "$VT"; then
            VT_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 -H "x-apikey: $VT" "https://www.virustotal.com/api/v3/users/me")
            if [ "$VT_HTTP" = "200" ]; then log_info "  [OK]   VirusTotal"; CONN_OK=$((CONN_OK+1)); else log_error "  [FAIL] VirusTotal ($VT_HTTP)"; CONN_FAIL=$((CONN_FAIL+1)); fi
        else log_warn "  [SKIP] VirusTotal (no key)"; fi

        if is_real_key "$SHODAN"; then
            SH_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://api.shodan.io/api-info?key=$SHODAN")
            if [ "$SH_HTTP" = "200" ]; then log_info "  [OK]   Shodan"; CONN_OK=$((CONN_OK+1)); else log_error "  [FAIL] Shodan ($SH_HTTP)"; CONN_FAIL=$((CONN_FAIL+1)); fi
        else log_warn "  [SKIP] Shodan (no key)"; fi

        if is_real_key "$ANTHROPIC"; then
            AN_HTTP=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 \
                -H "x-api-key: $ANTHROPIC" -H "anthropic-version: 2023-06-01" -H "content-type: application/json" \
                -d '{"model":"claude-haiku-4-5-20251001","max_tokens":1,"messages":[{"role":"user","content":"hi"}]}' \
                "https://api.anthropic.com/v1/messages")
            if [ "$AN_HTTP" = "200" ]; then log_info "  [OK]   Anthropic"; CONN_OK=$((CONN_OK+1)); else log_error "  [FAIL] Anthropic ($AN_HTTP)"; CONN_FAIL=$((CONN_FAIL+1)); fi
        else log_warn "  [SKIP] Anthropic (no key)"; fi
    else
        log_warn "  [SKIP] Authenticated APIs (ml-threat service not running)"
    fi

    # Telegram
    TG_NODE=$(docker service ps telegram_telegram-bot --format "{{.Node}}" --filter "desired-state=running" 2>/dev/null | head -1)
    if [ -n "$TG_NODE" ]; then
        TG_IP=$(docker node inspect "$TG_NODE" --format '{{.Status.Addr}}' 2>/dev/null)
        TG_TOKEN=$(ssh $SSH_OPTS docker@"$TG_IP" \
            "TG=\$(docker ps -q -f name=telegram_telegram-bot | head -1) && \
             docker exec \$TG cat /run/secrets/telegram_bot_token 2>/dev/null" 2>/dev/null)
        if is_real_key "$TG_TOKEN"; then
            TG_OK=$(curl -s --max-time 10 "https://api.telegram.org/bot${TG_TOKEN}/getMe" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok',''))" 2>/dev/null)
            if [ "$TG_OK" = "True" ]; then log_info "  [OK]   Telegram Bot"; CONN_OK=$((CONN_OK+1)); else log_error "  [FAIL] Telegram Bot"; CONN_FAIL=$((CONN_FAIL+1)); fi
        else log_warn "  [SKIP] Telegram (no token)"; fi
    else
        log_warn "  [SKIP] Telegram (service not running)"
    fi

    CONN_TOTAL=$((CONN_OK + CONN_FAIL))
    log_info "Connectivity: ${CONN_OK}/${CONN_TOTAL} OK, ${CONN_FAIL} FAIL"
else
    log_info "Running on worker node - deploying suricata only"

    # Deploy suricata standalone (needs network_mode: host, not supported in Swarm)
    log_info "Deploying suricata (standalone docker compose)..."
    docker compose -f "$DIR/stack/01-suricata-host.yml" up -d

    log_info "Suricata deployment complete."
fi
