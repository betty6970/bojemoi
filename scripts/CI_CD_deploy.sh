#!/bin/bash
set -e

SWARM_MANAGER="${SWARM_MANAGER:-manager.bojemoi.lab.local}"
STACKS_DIR="stacks"
DEPLOY_MODE="${1:-all}"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

deploy_stack() {
    local stack_name=$1
    local stack_file="${STACKS_DIR}/${stack_name}.yml"
    
    if [ ! -f "$stack_file" ]; then
        log_error "Stack file not found: $stack_file"
        return 1
    fi
    
    log_info "Deploying stack: $stack_name"
    
    # Copie du fichier stack
    scp "$stack_file" "${SWARM_MANAGER}:/tmp/${stack_name}.yml"
    
    # Déploiement
    ssh "$SWARM_MANAGER" "docker stack deploy -c /tmp/${stack_name}.yml $stack_name --prune --resolve-image always"
    
    # Vérification
    sleep 5
    ssh "$SWARM_MANAGER" "docker service ls --filter name=${stack_name}"
    
    log_info "Stack $stack_name deployed successfully"
}

wait_for_service() {
    local service_name=$1
    local max_wait=60
    local count=0
    
    log_info "Waiting for service $service_name to be ready..."
    
    while [ $count -lt $max_wait ]; do
        replicas=$(ssh "$SWARM_MANAGER" "docker service ls --filter name=$service_name --format '{{.Replicas}}'")
        if [[ "$replicas" =~ ^([0-9]+)/\1 ]]; then
            log_info "Service $service_name is ready"
            return 0
        fi
        sleep 2
        count=$((count + 2))
    done
    
    log_warn "Service $service_name not ready after ${max_wait}s"
    return 1
}

# Ordre de déploiement (dépendances)
DEPLOYMENT_ORDER=(
    "traefik"
    "monitoring"
    "crowdsec"
    "suricata"
    "faraday"
)

case "$DEPLOY_MODE" in
    all)
        log_info "Deploying all stacks in order..."
        for stack in "${DEPLOYMENT_ORDER[@]}"; do
            deploy_stack "$stack"
            wait_for_service "${stack}_*"
        done
        ;;
    *)
        deploy_stack "$DEPLOY_MODE"
        ;;
esac

log_info "Deployment completed!"

