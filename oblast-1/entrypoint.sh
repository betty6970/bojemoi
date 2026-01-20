#!/bin/ash

# Script d'entrée pour le container scanner ZAP
set -e

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction de logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" >&2
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] SUCCESS: $1${NC}"
}

# Vérifier les variables d'environnement requises
check_env_vars() {
    log "Vérification des variables d'environnement..."
    
    required_vars="DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD ZAP_HOST ZAP_PORT"
    missing_vars=""
    
    for var in $required_vars; do
        eval value=\$$var
        if [ -z "$value" ]; then
            missing_vars="$missing_vars $var"
        fi
    done
    
    if [ -n "$missing_vars" ]; then
        log_error "Variables d'environnement manquantes:$missing_vars"
        exit 1
    fi
    
    log_success "Variables d'environnement OK"
}

# Tester la connectivité à la base de données
test_database_connection() {
    log "Test de connexion à la base de données PostgreSQL..."
    
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python3 -c "
import psycopg2
import os
import sys
try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD')
    )
    conn.close()
    print('Connexion DB réussie')
    sys.exit(0)
except Exception as e:
    print(f'Erreur DB: {e}')
    sys.exit(1)
" 2>/dev/null; then
            log_success "Connexion à la base de données établie"
            return 0
        fi
        
        log_warning "Tentative $attempt/$max_attempts - Base de données non disponible, nouvelle tentative dans 5s..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    log_error "Impossible de se connecter à la base de données après $max_attempts tentatives"
    exit 1
}

# Tester la connectivité à ZAP
test_zap_connection() {
    log "Test de connexion à ZAP Proxy..."
    
    max_attempts=60
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/view/version/" >/dev/null 2>&1; then
            log_success "Connexion à ZAP Proxy établie"
            return 0
        fi
        
        log_warning "Tentative $attempt/$max_attempts - ZAP Proxy non disponible, nouvelle tentative dans 5s..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    log_error "Impossible de se connecter à ZAP Proxy après $max_attempts tentatives"
    exit 1
}

# Créer les répertoires nécessaires
setup_directories() {
    log "Création des répertoires nécessaires..."
    
    mkdir -p /results /logs
    
    # Vérifier les permissions
    if [ ! -w "/results" ]; then
        log_error "Pas de permission d'écriture sur /results"
        exit 1
    fi
    
    if [ ! -w "/logs" ]; then
        log_error "Pas de permission d'écriture sur /logs"
        exit 1
    fi
    
    log_success "Répertoires configurés"
}

# Afficher les informations de configuration
display_config() {
    log "Configuration du scanner ZAP:"
    echo "  Database: ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
    echo "  ZAP Proxy: ${ZAP_HOST}:${ZAP_PORT}"
    echo "  Répertoire de résultats: /results"
    echo "  Répertoire de logs: /logs"
    echo "  Utilisateur: $(whoami)"
    echo "  PID: $$"
}

# Fonction de nettoyage en cas d'arrêt
cleanup() {
    log "Arrêt du scanner..."
    # Tuer tous les processus enfants
    jobs -p | xargs -r kill 2>/dev/null || true
    exit 0
}

# Gérer les signaux d'arrêt
trap cleanup SIGTERM SIGINT

# Fonction principale
main() {
    log "=========================================="
    log "     Démarrage du Scanner ZAP"
    log "=========================================="
    
    # Vérifications préliminaires
    check_env_vars
    setup_directories
    display_config
    
    # Tests de connectivité
    test_database_connection
    test_zap_connection
    
    log "Toutes les vérifications sont passées avec succès"
    log "Lancement du scanner..."
    
    # Rediriger les logs vers un fichier
    exec 2>> /logs/scanner_error.log
    
    # Exécuter la commande passée en paramètre
    exec "$@"
}

# Démarrer le script principal
main "$@"

