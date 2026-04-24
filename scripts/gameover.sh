#!/bin/ash

DIR="/opt/bojemoi"

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Retirer un stack avec gestion d'erreur
remove_stack() {
    local stack_name=$1
    if docker stack ls --format '{{.Name}}' | grep -qx "$stack_name"; then
        log_info "Removing stack: ${stack_name}"
        if docker stack rm "$stack_name"; then
            return 0
        else
            log_error "Failed to remove stack: ${stack_name}"
            return 1
        fi
    else
        log_warn "Stack ${stack_name} not found, skipping"
        return 0
    fi
}

# === MAIN ===

NODE_ROLE=$(docker info --format '{{.Swarm.ControlAvailable}}')

if [ "$NODE_ROLE" != "true" ]; then
    log_info "Running on worker node - stopping suricata only"
    docker compose -f "$DIR/stack/01-suricata-host.yml" down 2>/dev/null
    log_info "Done."
    exit 0
fi

log_info "Running on manager node - full teardown"

SSH_OPTS="-p 4422 -i /home/docker/.ssh/meta76_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=5"

# Ordre inverse de startover.sh : dépendants d'abord, fondations en dernier

# Suricata (docker compose) sur tous les nœuds
log_info "Stopping suricata on all nodes..."
docker compose -f "$DIR/stack/01-suricata-host.yml" down 2>/dev/null
for node in $(docker node ls --format '{{.Hostname}}' | grep -v "$(hostname)"); do
    NODE_IP=$(docker node inspect "$node" --format '{{.Status.Addr}}' 2>/dev/null)
    if [ -n "$NODE_IP" ]; then
        log_info "  suricata → $node ($NODE_IP)..."
        ssh $SSH_OPTS docker@"$NODE_IP" \
            "cd /opt/bojemoi && docker compose -f stack/01-suricata-host.yml down" 2>/dev/null \
            && log_info "  $node: OK" \
            || log_warn "  $node: FAILED"
    fi
done

# Stacks applicatifs (ordre inverse de startover)
remove_stack "honeypot"
remove_stack "telegram"
remove_stack "sentinel"
remove_stack "trivy"
remove_stack "mcp"
remove_stack "dozor"
remove_stack "vigie"
remove_stack "razvedka"
remove_stack "ml-threat"

# Pentest core
remove_stack "borodino"

# Infra services
remove_stack "ollama"
remove_stack "maintenance"

# Fondations (base + boot en dernier)
remove_stack "base"
remove_stack "boot"

# Attendre que les services se terminent
log_info "Waiting for services to drain..."
sleep 10

# Vérification
REMAINING=$(docker service ls --format '{{.Name}}' 2>/dev/null | wc -l)
if [ "$REMAINING" -eq 0 ]; then
    log_info "All services stopped"
else
    log_warn "${REMAINING} service(s) still running:"
    docker service ls
fi

# Nettoyage profond sur tous les nœuds
log_info "Deep cleaning all nodes..."

deep_clean() {
    log_info "  Pruning containers, images, volumes, build cache..."
    docker container prune -f 2>/dev/null
    docker image prune -af 2>/dev/null
    docker volume prune -f 2>/dev/null
    docker builder prune -af 2>/dev/null
    docker network prune -f 2>/dev/null
}

# Manager
log_info "  Cleaning manager ($(hostname))..."
deep_clean

# Workers
for node in $(docker node ls --format '{{.Hostname}}' | grep -v "$(hostname)"); do
    NODE_IP=$(docker node inspect "$node" --format '{{.Status.Addr}}' 2>/dev/null)
    if [ -n "$NODE_IP" ]; then
        log_info "  Cleaning $node ($NODE_IP)..."
        ssh $SSH_OPTS docker@"$NODE_IP" "
            docker container prune -f 2>/dev/null
            docker image prune -af 2>/dev/null
            docker volume prune -f 2>/dev/null
            docker builder prune -af 2>/dev/null
            docker network prune -f 2>/dev/null
        " 2>/dev/null \
            && log_info "  $node: OK" \
            || log_warn "  $node: FAILED"
    fi
done

# Résumé espace disque
log_info "Disk usage after cleanup:"
df -h / | awk 'NR==2 {printf "  manager: %s used / %s (%s)\n", $3, $2, $5}'
for node in $(docker node ls --format '{{.Hostname}}' | grep -v "$(hostname)"); do
    NODE_IP=$(docker node inspect "$node" --format '{{.Status.Addr}}' 2>/dev/null)
    if [ -n "$NODE_IP" ]; then
        ssh $SSH_OPTS docker@"$NODE_IP" \
            "df -h / | awk 'NR==2 {printf \"  $node: %s used / %s (%s)\n\", \$3, \$2, \$5}'" 2>/dev/null
    fi
done

log_info "Gameover."
