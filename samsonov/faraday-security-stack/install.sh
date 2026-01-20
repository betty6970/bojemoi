#!/bin/bash
#
# Script d'installation automatique pour Faraday Security Stack
#

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logo
print_logo() {
    cat << "EOF"
    ____                     __              
   / __/___ __________ _____/ /___ ___  __   
  / /_/ __ `/ ___/ __ `/ __  / __ `/ / / /   
 / __/ /_/ / /  / /_/ / /_/ / /_/ / /_/ /    
/_/  \__,_/_/   \__,_/\__,_/\__,_/\__, /     
  / ___/___  _______  _______(_) /____/ __  __
  \__ \/ _ \/ ___/ / / / ___/ / __/ / / /    
 ___/ /  __/ /__/ /_/ / /  / / /_/ /_/ /     
/____/\___/\___/\__,_/_/  /_/\__/\__, /      
   / ___// /_____ ______/ /__   /____/       
   \__ \/ __/ __ `/ ___/ //_/                
  ___/ / /_/ /_/ / /__/ ,<                   
 /____/\__/\__,_/\___/_/|_|                  
                                             
EOF
}

# Fonctions de log
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérifier les prérequis
check_prerequisites() {
    log_info "Vérification des prérequis..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé"
        log_info "Installez Docker depuis: https://docs.docker.com/get-docker/"
        exit 1
    fi
    log_success "Docker trouvé: $(docker --version)"
    
    # Vérifier Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose n'est pas installé"
        log_info "Installez Docker Compose depuis: https://docs.docker.com/compose/install/"
        exit 1
    fi
    log_success "Docker Compose trouvé: $(docker-compose --version)"
    
    # Vérifier Make
    if ! command -v make &> /dev/null; then
        log_warning "Make n'est pas installé (optionnel mais recommandé)"
        log_info "Installez Make avec: apt-get install make (Debian/Ubuntu) ou yum install make (RedHat/CentOS)"
    else
        log_success "Make trouvé: $(make --version | head -n1)"
    fi
    
    # Vérifier Python
    if ! command -v python3 &> /dev/null; then
        log_warning "Python 3 n'est pas installé (nécessaire pour les scripts)"
        log_info "Installez Python 3 avec: apt-get install python3 (Debian/Ubuntu)"
    else
        log_success "Python 3 trouvé: $(python3 --version)"
    fi
}

# Créer la structure des répertoires
create_directories() {
    log_info "Création de la structure des répertoires..."
    
    mkdir -p configs/{faraday,zap,metasploit,burp,nginx/conf.d}
    mkdir -p scripts/{zap,metasploit,masscan}
    mkdir -p backups
    mkdir -p results
    
    log_success "Structure des répertoires créée"
}

# Configurer les permissions
set_permissions() {
    log_info "Configuration des permissions..."
    
    chmod +x scripts/*.sh 2>/dev/null || true
    chmod +x scripts/*.py 2>/dev/null || true
    chmod 600 .env 2>/dev/null || true
    
    log_success "Permissions configurées"
}

# Installer les dépendances Python
install_python_deps() {
    log_info "Installation des dépendances Python..."
    
    if command -v pip3 &> /dev/null; then
        pip3 install --user python-owasp-zap-v2.4 requests 2>/dev/null || {
            log_warning "Impossible d'installer les dépendances Python"
            log_info "Les scripts nécessiteront ces dépendances:"
            log_info "  - python-owasp-zap-v2.4"
            log_info "  - requests"
        }
    else
        log_warning "pip3 non trouvé, impossible d'installer les dépendances Python"
    fi
}

# Construire les images Docker
build_images() {
    log_info "Construction des images Docker (cela peut prendre plusieurs minutes)..."
    
    if docker-compose build; then
        log_success "Images Docker construites avec succès"
    else
        log_error "Échec de la construction des images Docker"
        exit 1
    fi
}

# Démarrer les services
start_services() {
    log_info "Démarrage des services..."
    
    if docker-compose up -d; then
        log_success "Services démarrés avec succès"
    else
        log_error "Échec du démarrage des services"
        exit 1
    fi
    
    # Attendre que les services soient prêts
    log_info "Attente du démarrage complet des services..."
    sleep 10
}

# Vérifier l'état des services
check_services() {
    log_info "Vérification de l'état des services..."
    
    echo ""
    docker-compose ps
    echo ""
    
    # Tester Faraday
    log_info "Test de Faraday..."
    if curl -s -f http://localhost:5985 > /dev/null 2>&1; then
        log_success "Faraday est accessible sur http://localhost:5985"
    else
        log_warning "Faraday n'est pas encore accessible (il peut prendre quelques minutes pour démarrer)"
    fi
    
    # Tester ZAP
    log_info "Test de ZAP..."
    if curl -s -f http://localhost:8080 > /dev/null 2>&1; then
        log_success "ZAP est accessible sur http://localhost:8080"
    else
        log_warning "ZAP n'est pas encore accessible"
    fi
}

# Afficher les informations de connexion
show_info() {
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Installation terminée avec succès!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${BLUE}URLs d'accès:${NC}"
    echo "  - Faraday:     http://localhost:5985"
    echo "  - ZAP:         http://localhost:8080"
    echo "  - Burp:        http://localhost:8081"
    echo "  - Nginx:       http://localhost"
    echo ""
    echo -e "${BLUE}Credentials par défaut Faraday:${NC}"
    echo "  - Utilisateur: faraday"
    echo "  - Mot de passe: changeme"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Changez ces credentials en production!${NC}"
    echo ""
    echo -e "${BLUE}Commandes utiles:${NC}"
    echo "  - Voir les logs:        make logs"
    echo "  - Arrêter les services: make down"
    echo "  - Redémarrer:           make restart"
    echo "  - Lancer un scan:       make scan TARGET=<cible>"
    echo "  - Aide complète:        make help"
    echo ""
    echo -e "${BLUE}Documentation:${NC}"
    echo "  Consultez le fichier README.md pour plus d'informations"
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
}

# Menu interactif
interactive_menu() {
    echo ""
    echo -e "${BLUE}Que souhaitez-vous faire?${NC}"
    echo "1) Installation complète (recommandé)"
    echo "2) Installation rapide (sans build)"
    echo "3) Vérifier uniquement les prérequis"
    echo "4) Quitter"
    echo ""
    read -p "Votre choix [1-4]: " choice
    
    case $choice in
        1)
            return 0
            ;;
        2)
            QUICK_INSTALL=true
            return 0
            ;;
        3)
            check_prerequisites
            exit 0
            ;;
        4)
            log_info "Installation annulée"
            exit 0
            ;;
        *)
            log_error "Choix invalide"
            interactive_menu
            ;;
    esac
}

# Script principal
main() {
    clear
    print_logo
    echo ""
    echo -e "${GREEN}Installation de Faraday Security Stack${NC}"
    echo ""
    
    # Menu interactif si pas d'argument
    if [ $# -eq 0 ]; then
        interactive_menu
    fi
    
    # Installation
    check_prerequisites
    create_directories
    set_permissions
    #install_python_deps
    
    if [ "${QUICK_INSTALL}" != "true" ]; then
        build_images
    fi
    
    start_services
    check_services
    show_info
    
    log_success "Installation terminée!"
}

# Gestion des signaux
trap 'log_error "Installation interrompue"; exit 1' INT TERM

# Lancer le script principal
main "$@"
