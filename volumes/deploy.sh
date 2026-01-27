#!/bin/ash

# Script de déploiement du stack de monitoring rsync
# Usage: ./deploy.sh [start|stop|restart|logs]

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Fonction pour créer les répertoires nécessaires
create_directories() {
    log "Création des répertoires..."
    
    mkdir -p grafana/provisioning/datasources
    mkdir -p grafana/provisioning/dashboards
    mkdir -p grafana/dashboards
    mkdir -p rsync-exporter
    mkdir -p prometheus
    mkdir -p loki
    
    log "Répertoires créés"
}

# Fonction pour configurer les fichiers
setup_config_files() {
    log "Configuration des fichiers..."
    
    # Copier les configurations
    if [ ! -f "prometheus/prometheus.yml" ]; then
        warn "Créez le fichier prometheus/prometheus.yml avec la configuration Prometheus"
    fi
    
    if [ ! -f "loki/loki-config.yml" ]; then
        warn "Créez le fichier loki/loki-config.yml avec la configuration Loki"
    fi
    
    if [ ! -f "promtail-config.yml" ]; then
        warn "Créez le fichier promtail-config.yml avec la configuration Promtail"
    fi
    
    if [ ! -f "grafana/provisioning/datasources/datasources.yml" ]; then
        warn "Créez le fichier grafana/provisioning/datasources/datasources.yml"
    fi
    
    # Copier le dashboard
    if [ ! -f "grafana/dashboards/rsync-dashboard.json" ]; then
        warn "Créez le fichier grafana/dashboards/rsync-dashboard.json avec le dashboard"
    fi
    
    # Créer le fichier requirements.txt pour l'exporter
    cat > rsync-exporter/requirements.txt << EOF
prometheus-client==0.18.0
psycopg2-binary==2.9.7
watchdog==3.0.0
EOF
    
    # Copier l'exporter Python
    if [ ! -f "rsync-exporter/rsync_exporter.py" ]; then
        warn "Créez le fichier rsync-exporter/rsync_exporter.py avec le code de l'exporter"
    fi
    
    # Créer le Dockerfile pour l'exporter
    if [ ! -f "rsync-exporter/Dockerfile" ]; then
        warn "Créez le fichier rsync-exporter/Dockerfile"
    fi
    
    log "Configuration terminée"
}

# Fonction pour vérifier les prérequis
check_prerequisites() {
    log "Vérification des prérequis..."
    
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose n'est pas installé"
        exit 1
    fi
    
    # Vérifier que le répertoire des logs rsync existe
    if [ ! -d "/path/to/rsync/logs" ]; then
        warn "Le répertoire /path/to/rsync/logs n'existe pas"
        warn "Modifiez le docker-compose.yml avec le bon chemin vers vos logs rsync"
    fi
    
    log "Prérequis vérifiés"
}

# Fonction pour démarrer les services
start_services() {
    log "Démarrage des services..."
    
    docker-compose up -d
    
    log "Services démarrés"
    log "Grafana disponible sur: http://localhost:3000 (admin/admin)"
    log "Prometheus disponible sur: http://localhost:9090"
    log "Loki disponible sur: http://localhost:3100"
}

# Fonction pour arrêter les services
stop_services() {
    log "Arrêt des services..."
    
    docker-compose down
    
    log "Services arrêtés"
}

# Fonction pour redémarrer les services
restart_services() {
    log "Redémarrage des services..."
    
    docker-compose down
    docker-compose up -d
    
    log "Services redémarrés"
}

# Fonction pour afficher les logs
show_logs() {
    log "Affichage des logs..."
    
    if [ -n "$2" ]; then
        docker-compose logs -f "$2"
    else
        docker-compose logs -f
    fi
}

# Fonction pour vérifier le statut
check_status() {
    log "Statut des services:"
    docker-compose ps
    
    echo ""
    log "Vérification de la connectivité:"
    
    # Vérifier Grafana
    if curl -s http://localhost:3000/api/health > /dev/null 2>&1; then
        echo -e "✅ Grafana: ${GREEN}OK${NC}"
    else
        echo -e "❌ Grafana: ${RED}KO${NC}"
    fi
    
    # Vérifier Prometheus
    if curl -s http://localhost:9090/-/healthy > /dev/null 2>&1; then
        echo -e "✅ Prometheus: ${GREEN}OK${NC}"
    else
        echo -e "❌ Prometheus: ${RED}KO${NC}"
    fi
    
    # Vérifier Loki
    if curl -s http://localhost:3100/ready > /dev/null 2>&1; then
        echo -e "✅ Loki: ${GREEN}OK${NC}"
    else
        echo -e "❌ Loki: ${RED}KO${NC}"
    fi
}

# Fonction pour nettoyer les données
cleanup() {
    warn "Cette action supprimera tous les volumes et données"
    read -p "Êtes-vous sûr ? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "Nettoyage en cours..."
        docker-compose down -v
        docker system prune -f
        log "Nettoyage terminé"
    else
        log "Nettoyage annulé"
    fi
}

# Menu principal
case "${1:-help}" in
    start)
        check_prerequisites
        create_directories
        setup_config_files
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    logs)
        show_logs "$@"
        ;;
    status)
        check_status
        ;;
    cleanup)
        cleanup
        ;;
    help|*)
        echo "Usage: $0 {start|stop|restart|logs [service]|status|cleanup}"
        echo ""
        echo "Commandes:"
        echo "  start    - Démarre tous les services"
        echo "  stop     - Arrête tous les services"
        echo "  restart  - Redémarre tous les services"
        echo "  logs     - Affiche les logs (optionnel: nom du service)"
        echo "  status   - Vérifie le statut des services"
        echo "  cleanup  - Supprime tous les volumes et données"
        echo ""
        echo "Exemples:"
        echo "  $0 start"
        echo "  $0 logs grafana"
        echo "  $0 status"
        ;;
esac
