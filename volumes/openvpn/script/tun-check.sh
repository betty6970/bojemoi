#!/bin/ash

# Script de vérification du routage réseau Docker -> TUN0
# Compatible Alpine Linux avec ash shell
# Usage: ./verify-routing.sh

# Couleurs pour ash (syntaxe simple)
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { printf "${BLUE}[INFO]${NC} %s\n" "$1"; }
log_success() { printf "${GREEN}[SUCCESS]${NC} %s\n" "$1"; }
log_warning() { printf "${YELLOW}[WARNING]${NC} %s\n" "$1"; }
log_error() { printf "${RED}[ERROR]${NC} %s\n" "$1"; }

echo "=== Vérification de la configuration de routage Docker -> TUN0 ==="
echo ""

# 1. Vérifier l'interface tun0
log_info "Vérification de l'interface tun0..."
if ip link show tun0 > /dev/null 2>&1; then
    # Récupération de l'IP avec awk (compatible ash)
    TUN_IP=$(ip addr show tun0 | awk '/inet / {print $2; exit}')
    TUN_STATUS=$(ip link show tun0 | awk '/state/ {print $9; exit}')
    log_success "Interface tun0 trouvée - IP: ${TUN_IP:-Non configurée}, État: ${TUN_STATUS:-Inconnu}"
else
    log_error "Interface tun0 non trouvée"
    exit 1
fi

# 2. Vérifier le forwarding IP
log_info "Vérification du forwarding IP..."
IP_FORWARD=$(cat /proc/sys/net/ipv4/ip_forward 2>/dev/null || echo "0")
if [ "$IP_FORWARD" = "1" ]; then
    log_success "Forwarding IP activé"
else
    log_warning "Forwarding IP désactivé"
    echo "  Pour activer: echo 1 > /proc/sys/net/ipv4/ip_forward"
fi

# 3. Vérifier les outils disponibles
log_info "Vérification des outils disponibles..."
TOOLS_MISSING=""

if ! command -v iptables > /dev/null 2>&1; then
    TOOLS_MISSING="${TOOLS_MISSING} iptables"
fi

if ! command -v docker > /dev/null 2>&1; then
    TOOLS_MISSING="${TOOLS_MISSING} docker"
fi

if [ -n "$TOOLS_MISSING" ]; then
    log_warning "Outils manquants:$TOOLS_MISSING"
    echo "  Installation: apk add$TOOLS_MISSING"
else
    log_success "Tous les outils nécessaires sont disponibles"
fi

# 4. Vérifier les règles iptables (si disponible)
if command -v iptables > /dev/null 2>&1; then
    log_info "Vérification des règles iptables..."
    
    # Vérifier NAT POSTROUTING
    if iptables -t nat -L POSTROUTING -n 2>/dev/null | grep -q tun0; then
        log_success "Règles NAT pour tun0 présentes"
        echo "  Règles détectées:"
        iptables -t nat -L POSTROUTING -n 2>/dev/null | grep tun0 | while read line; do
            echo "    $line"
        done
    else
        log_warning "Aucune règle NAT pour tun0 détectée"
    fi

    # Vérifier FORWARD
    if iptables -L FORWARD -n 2>/dev/null | grep -q tun0; then
        log_success "Règles FORWARD pour tun0 présentes"
        echo "  Règles détectées:"
        iptables -L FORWARD -n 2>/dev/null | grep tun0 | while read line; do
            echo "    $line"
        done
    else
        log_warning "Aucune règle FORWARD pour tun0 détectée"
    fi
else
    log_warning "iptables non disponible - vérification des règles ignorée"
fi

# 5. Vérifier les routes
log_info "Vérification des routes..."
echo "  Routes actuelles:"
ip route show | while read line; do
    echo "    $line"
done

if ip route show | grep -q "dev tun0"; then
    log_success "Routes via tun0 détectées"
    echo "  Routes tun0:"
    ip route show | grep "dev tun0" | while read line; do
        echo "    $line"
    done
else
    log_warning "Aucune route via tun0 détectée"
fi

# 6. Vérifier Docker (si disponible)
if command -v docker > /dev/null 2>&1; then
    log_info "Vérification de Docker..."
    
    # Vérifier si Docker daemon est accessible
    if docker info > /dev/null 2>&1; then
        log_success "Docker accessible"
        
        # Vérifier les réseaux Docker
        echo "  Réseaux Docker:"
        docker network ls | while read line; do
            echo "    $line"
        done
        
        # Vérifier les containers en cours
        RUNNING_COUNT=$(docker ps -q | wc -l)
        if [ "$RUNNING_COUNT" -gt 0 ]; then
            log_success "$RUNNING_COUNT container(s) en cours d'exécution"
            echo "  Containers actifs:"
            docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" | while read line; do
                echo "    $line"
            done
        else
            log_info "Aucun container en cours d'exécution"
        fi
        
        # Vérifier le subnet Docker par défaut
        DOCKER_SUBNET=$(docker network inspect bridge 2>/dev/null | grep -o '"Subnet": "[^"]*' | cut -d'"' -f4 | head -1)
        if [ -n "$DOCKER_SUBNET" ]; then
            log_info "Subnet Docker par défaut: $DOCKER_SUBNET"
        else
            log_info "Subnet Docker par défaut: 172.17.0.0/16 (supposé)"
        fi
        
    else
        log_warning "Docker daemon non accessible (permissions ou service arrêté)"
    fi
else
    log_warning "Docker non disponible"
fi

# 7. Test de connectivité réseau simple
log_info "Test de connectivité réseau..."
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    log_success "Connectivité Internet OK"
else
    log_warning "Problème de connectivité Internet"
fi

# Test de résolution DNS
if nslookup google.com > /dev/null 2>&1 || [ $? -eq 0 ]; then
    log_success "Résolution DNS OK"
elif ping -c 1 google.com > /dev/null 2>&1; then
    log_success "Résolution DNS OK (via ping)"
else
    log_warning "Problème de résolution DNS"
fi

# 8. Analyser la configuration de routage
log_info "Analyse de la configuration de routage..."
DEFAULT_ROUTE=$(ip route show default | head -1)
if [ -n "$DEFAULT_ROUTE" ]; then
    if echo "$DEFAULT_ROUTE" | grep -q "dev tun0"; then
        log_success "Route par défaut via tun0: $DEFAULT_ROUTE"
    else
        log_warning "Route par défaut NOT via tun0: $DEFAULT_ROUTE"
    fi
else
    log_error "Aucune route par défaut trouvée"
fi

# 9. Vérifier les interfaces réseau disponibles
log_info "Interfaces réseau disponibles..."
ip link show | grep -E '^[0-9]+:' | while read line; do
    IFACE=$(echo "$line" | cut -d':' -f2 | tr -d ' ')
    STATE=$(echo "$line" | grep -o 'state [A-Z]*' | cut -d' ' -f2)
    echo "    $IFACE: $STATE"
done

# 10. Recommandations pour Alpine Linux
echo ""
echo "=== Recommandations pour Alpine Linux ==="

# Vérifier les paquets nécessaires
MISSING_PACKAGES=""
if ! command -v iptables > /dev/null 2>&1; then
    MISSING_PACKAGES="${MISSING_PACKAGES} iptables"
fi
if ! command -v docker > /dev/null 2>&1; then
    MISSING_PACKAGES="${MISSING_PACKAGES} docker"
fi
if ! command -v curl > /dev/null 2>&1; then
    MISSING_PACKAGES="${MISSING_PACKAGES} curl"
fi

if [ -n "$MISSING_PACKAGES" ]; then
    echo "• Installer les paquets manquants: apk add$MISSING_PACKAGES"
fi

# Recommandations de configuration
if ! iptables -t nat -L POSTROUTING -n 2>/dev/null | grep -q tun0; then
    echo "• Ajouter la règle NAT:"
    echo "  iptables -t nat -A POSTROUTING -s 172.17.0.0/16 -o tun0 -j MASQUERADE"
fi

if [ "$IP_FORWARD" != "1" ]; then
    echo "• Activer le forwarding IP:"
    echo "  echo 1 > /proc/sys/net/ipv4/ip_forward"
    echo "  echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf"
fi

if ! ip route show default | grep -q "dev tun0"; then
    echo "• Modifier la route par défaut (optionnel):"
    echo "  ip route del default"
    echo "  ip route add default via [TUN0_GATEWAY] dev tun0"
fi

# Configuration pour Alpine Linux
echo ""
echo "=== Configuration spécifique Alpine Linux ==="
echo "• Démarrage automatique des services:"
echo "  rc-update add docker default"
echo "  rc-service docker start"
echo ""
echo "• Script de configuration au démarrage (/etc/local.d/docker-tun.start):"
echo "  #!/bin/ash"
echo "  echo 1 > /proc/sys/net/ipv4/ip_forward"
echo "  iptables -t nat -A POSTROUTING -s 172.17.0.0/16 -o tun0 -j MASQUERADE"
echo "  chmod +x /etc/local.d/docker-tun.start"

echo ""
echo "=== Docker Compose pour Alpine ==="
echo "Utilisez le fichier docker-compose.yml avec image alpine:latest"

echo ""
log_info "Vérification terminée pour Alpine Linux."

