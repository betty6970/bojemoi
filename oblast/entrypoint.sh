#!/bin/ash 
#pt entrypoint pour OWASP ZAP
# Auteur: Votre nom
# Version: 1.0

set -e

# Variables d'environnement par défaut
ZAP_HOME=${ZAP_HOME:-/opt/zaproxy}
ZAP_DATA=${ZAP_DATA:-/home/zap/.ZAP}
ZAP_PORT=${ZAP_PORT:-8080}
ZAP_HOST=${ZAP_HOST:-0.0.0.0}

# Fonction de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Fonction d'aide
show_help() {
    cat << EOF
Usage: docker run [OPTIONS] owasp-zap [COMMAND]

Commands disponibles:
  zap-daemon      Démarre ZAP en mode daemon (par défaut)
  zap-gui         Démarre ZAP avec interface graphique (nécessite X11)
  zap-baseline    Lance un scan baseline
  zap-full        Lance un scan complet
  zap-api         Lance uniquement l'API ZAP
  bash            Ouvre un shell bash
  help            Affiche cette aide

Variables d'environnement:
  ZAP_PORT        Port d'écoute (défaut: 8080)
  ZAP_HOST        Adresse d'écoute (défaut: 0.0.0.0)
  TARGET_URL      URL cible pour les scans
  REPORT_FORMAT   Format du rapport (html, xml, json)

Exemples:
  docker run -p 8080:8080 owasp-zap zap-daemon
  docker run -e TARGET_URL=https://example.com owasp-zap zap-baseline
EOF
}

# Fonction d'initialisation
init_zap() {
    log "Initialisation de OWASP ZAP..."
    
    # Création des répertoires nécessaires
    mkdir -p "${ZAP_DATA}/reports"
    mkdir -p "${ZAP_DATA}/sessions"
    mkdir -p "${ZAP_DATA}/scripts"
    
    # Vérification des permissions
    if [ ! -w "${ZAP_DATA}" ]; then
        log "ERREUR: Impossible d'écrire dans ${ZAP_DATA}"
        exit 1
    fi
    
    # Configuration de base si inexistante
    if [ ! -f "${ZAP_DATA}/config.xml" ]; then
        log "Création de la configuration par défaut..."
        cat > "${ZAP_DATA}/config.xml" << EOF
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<config>
    <api>
        <disablekey>false</disablekey>
        <incerrordetails>false</incerrordetails>
        <key></key>
        <secure>false</secure>
    </api>
    <proxy>
        <ip>${ZAP_HOST}</ip>
        <port>${ZAP_PORT}</port>
    </proxy>
</config>
EOF
    fi
}

# Fonction pour démarrer ZAP en mode daemon
start_daemon() {
    log "Démarrage de ZAP en mode daemon sur ${ZAP_HOST}:${ZAP_PORT}"
    exec "${ZAP_HOME}/zap.sh" \
        -daemon \
        -host "${ZAP_HOST}" \
        -port "${ZAP_PORT}" \
        -config api.addrs.addr.name=".*" \
        -config api.addrs.addr.regex=true \
        -config api.disablekey=true \
        -config spider.maxDuration=60 \
        -config view.mode=attack \
        -dir "${ZAP_DATA}"
}

# Fonction pour démarrer ZAP avec GUI
start_gui() {
    log "Démarrage de ZAP avec interface graphique"
    
    # Configuration X11
    export DISPLAY=${DISPLAY:-:99}
    
    # Démarrage de Xvfb si nécessaire
    if [ ! -f /tmp/.X99-lock ]; then
        log "Démarrage du serveur X virtuel..."
        Xvfb :99 -screen 0 1024x768x24 &
        sleep 2
    fi
    
    exec "${ZAP_HOME}/zap.sh" \
        -host "${ZAP_HOST}" \
        -port "${ZAP_PORT}" \
        -dir "${ZAP_DATA}"
}

# Fonction pour scan baseline
run_baseline() {
    if [ -z "${TARGET_URL}" ]; then
        log "ERREUR: Variable TARGET_URL requise pour le scan baseline"
        exit 1
    fi
    
    log "Lancement du scan baseline pour ${TARGET_URL}"
    
    local report_file="/home/zap/reports/baseline-$(date +%Y%m%d-%H%M%S).html"
    
    exec "${ZAP_HOME}/zap-baseline.py" \
        -t "${TARGET_URL}" \
        -r "${report_file}" \
        -J "/home/zap/reports/baseline-$(date +%Y%m%d-%H%M%S).json" \
        -w "/home/zap/reports/baseline-$(date +%Y%m%d-%H%M%S).md" \
        --hook=/home/zap/scripts/auth_hook.py 2>/dev/null || true
}

# Fonction pour scan complet
run_full_scan() {
    if [ -z "${TARGET_URL}" ]; then
        log "ERREUR: Variable TARGET_URL requise pour le scan complet"
        exit 1
    fi
    
    log "Lancement du scan complet pour ${TARGET_URL}"
    
    local report_file="/home/zap/reports/full-$(date +%Y%m%d-%H%M%S).html"
    
    exec "${ZAP_HOME}/zap-full-scan.py" \
        -t "${TARGET_URL}" \
        -r "${report_file}" \
        -J "/home/zap/reports/full-$(date +%Y%m%d-%H%M%S).json" \
        -w "/home/zap/reports/full-$(date +%Y%m%d-%H%M%S).md"
}

# Fonction pour API seulement
start_api_only() {
    log "Démarrage API ZAP uniquement"
    exec "${ZAP_HOME}/zap.sh" \
        -daemon \
        -host "${ZAP_HOST}" \
        -port "${ZAP_PORT}" \
        -config api.addrs.addr.name=".*" \
        -config api.addrs.addr.regex=true \
        -config api.disablekey=true \
        -nosplash \
        -dir "${ZAP_DATA}"
}

# Fonction de nettoyage à l'arrêt
cleanup() {
    log "Arrêt de ZAP..."
    pkill -f "zap" || true
    pkill -f "Xvfb" || true
}

# Piège pour gérer l'arrêt proprement
trap cleanup SIGTERM SIGINT

# Initialisation
init_zap

# Traitement des commandes
case "${1:-zap-daemon}" in
    "help"|"--help"|"-h")
        show_help
        exit 0
        ;;
    "zap-daemon")
        start_daemon
        ;;
    "zap-gui")
        start_gui
        ;;
    "zap-baseline")
        run_baseline
        ;;
    "zap-full")
        run_full_scan
        ;;
    "zap-api")
        start_api_only
        ;;
    "bash")
        exec /bin/bash
        ;;
    *)
        log "Commande inconnue: $1"
        show_help
        exit 1
        ;;
esac

