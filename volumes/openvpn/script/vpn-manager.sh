#!/bin/ash

# Script de gestion de la passerelle VPN
# Usage: ./manage-vpn.sh [start|stop|restart|status|test|logs|add-service]

COMPOSE_FILE="docker-compose.yml"
VPN_CONTAINER="openvpn-gateway"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_vpn_connection() {
    if docker ps | grep -q $VPN_CONTAINER; then
        local vpn_ip=$(docker exec $VPN_CONTAINER curl -s --max-time 10 ifconfig.me 2>/dev/null)
        if [ $? -eq 0 ] && [ ! -z "$vpn_ip" ]; then
            print_success "VPN connecté - IP publique: $vpn_ip"
            return 0
        else
            print_error "VPN non connecté ou problème de réseau"
            return 1
        fi
    else
        print_error "Container VPN non démarré"
        return 1
    fi
}

start_services() {
    print_status "Démarrage de la passerelle VPN et des services..."
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "Fichier docker-compose.yml non trouvé!"
        exit 1
    fi
    
    # Vérifier la configuration OpenVPN
    if [ ! -f "openvpn-config/client.ovpn" ]; then
        print_error "Configuration OpenVPN manquante!"
        print_warning "Placez votre fichier client.ovpn dans le dossier openvpn-config/"
        exit 1
    fi
    
    docker-compose up -d
    
    # Attendre que le VPN soit connecté
    print_status "Attente de la connexion VPN..."
    sleep 10
    
    local retries=6
    while [ $retries -gt 0 ]; do
        if check_vpn_connection; then
            break
        fi
        print_status "Nouvelle tentative dans 10 secondes..."
        sleep 10
        retries=$((retries-1))
    done
    
    if [ $retries -eq 0 ]; then
        print_error "Impossible de se connecter au VPN"
        docker-compose logs $VPN_CONTAINER
        return 1
    fi
    
    print_success "Tous les services sont démarrés et connectés via VPN"
}

stop_services() {
    print_status "Arrêt des services..."
    docker-compose down
    print_success "Services arrêtés"
}

restart_services() {
    print_status "Redémarrage des services..."
    stop_services
    sleep 3
    start_services
}

show_status() {
    print_status "État des services:"
    docker-compose ps
    echo
    
    if docker ps | grep -q $VPN_CONTAINER; then
        check_vpn_connection
        
        # Afficher les statistiques réseau
        echo
        print_status "Interface VPN (tun0):"
        docker exec $VPN_CONTAINER ip addr show tun0 2>/dev/null || print_warning "Interface tun0 non trouvée"
        
        echo
        print_status "Routes actives:"
        docker exec $VPN_CONTAINER ip route | head -5
    fi
}

test_connectivity() {
    print_status "Test de connectivité pour tous les services..."
    
    # Tester chaque service
    services=$(docker-compose config --services | grep -v openvpn-gateway)
    
    for service in $services; do
        if docker ps | grep -q "$service"; then
            print_status "Test de $service..."
            service_ip=$(docker exec "$service" curl -s --max-time 10 ifconfig.me 2>/dev/null)
            if [ $? -eq 0 ] && [ ! -z "$service_ip" ]; then
                print_success "$service - IP: $service_ip"
            else
                print_error "$service - Pas de connectivité"
            fi
        else
            print_warning "$service n'est pas démarré"
        fi
    done
    
    # Test DNS
    echo
    print_status "Test de résolution DNS..."
    docker exec $VPN_CONTAINER nslookup google.com | grep -A2 "Non-authoritative answer:" || print_warning "Problème DNS détecté"
}

show_logs() {
    local service=${2:-$VPN_CONTAINER}
    print_status "Logs de $service:"
    docker-compose logs -f --tail=50 "$service"
}

add_service() {
    read -p "Nom du nouveau service: " service_name
    read -p "Image Docker: " docker_image
    read -p "Ports à exposer (format 8080:80): " ports
    
    print_status "Ajout du service $service_name..."
    
    # Créer une sauvegarde
    cp docker-compose.yml docker-compose.yml.backup
    
    cat >> docker-compose.yml << EOF

  # Nouveau service ajouté automatiquement
  $service_name:
    image: $docker_image
    container_name: $service_name
    restart: unless-stopped
    network_mode: "service:openvpn-gateway"
    depends_on:
      - openvpn-gateway
EOF

    if [ ! -z "$ports" ]; then
        print_warning "N'oubliez pas d'ajouter le port $ports dans la section ports du service openvpn-gateway"
    fi
    
    print_success "Service $service_name ajouté. Redémarrez les services pour l'activer."
}

show_help() {
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  start       Démarrer tous les services"
    echo "  stop        Arrêter tous les services"
    echo "  restart     Redémarrer tous les services"
    echo "  status      Afficher l'état des services"
    echo "  test        Tester la connectivité VPN"
    echo "  logs [svc]  Afficher les logs (par défaut: openvpn-gateway)"
    echo "  add-service Ajouter un nouveau service"
    echo "  help        Afficher cette aide"
}

# Script principal
case "${1:-help}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    test)
        test_connectivity
        ;;
    logs)
        show_logs "$@"
        ;;
    add-service)
        add_service
        ;;
    help|*)
        show_help
        ;;
esac
