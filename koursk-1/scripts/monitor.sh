#!/bin/bash
set -e

LOG_FILE="/var/log/rsync-monitor.log"
CHECK_INTERVAL=${CHECK_INTERVAL:-60}
RSYNC_SERVICE_NAME=koursk
ROOT_SYNC_PATH=/opt/bojemoi

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [MONITOR] $1" | tee -a "$LOG_FILE"
}

# Vérification de la santé des services
check_services() {
    local errors=0
    
    # Vérification des conteneurs rsync
    if ! ping rsync-master; then
        log "ALERTE: Services rsync non disponibles"
        ((errors++))
    fi
    
    # Vérification des logs pour erreurs récentes
    if tail -n 100 /var/log/rsync/rsync-*.log | grep -i "error\|failed\|échec" > /dev/null; then
        log "ALERTE: Erreurs détectées dans les logs rsync"
        ((errors++))
    fi
    
    # Vérification de l'espace disque
    local disk_usage=$(df ${ROOT_SYNC_PATH} | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 90 ]; then
        log "ALERTE: Espace disque critique: ${disk_usage}%"
        ((errors++))
    fi
    
    if [ $errors -eq 0 ]; then
        log "Vérifications OK"
    else
        log "Détection de $errors problème(s)"
        send_alert "Problèmes détectés dans la réplication rsync"
    fi
}

# Envoi d'alerte
send_alert() {
    local message="$1"
    log "Envoi d'alerte: $message"
    
    if [ -n "$ALERT_EMAIL" ]; then
        echo "$message" | mail -s "Alerte rsync Swarm" "$ALERT_EMAIL" || log "Échec envoi email"
    fi
    
    # Webhook Slack/Discord si configuré
    if [ -n "$WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
             --data "{\"text\":\"$message\"}" \
             "$WEBHOOK_URL" || log "Échec webhook"
    fi
}

log "Démarrage du monitoring (intervalle: ${CHECK_INTERVAL}s)"

while true; do
    check_services
    sleep "$CHECK_INTERVAL"
done
