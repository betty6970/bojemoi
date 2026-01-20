#!/bin/bash
set -e

LOG_FILE="/var/log/rsync/rsync-master.log"
PID_FILE="/var/run/rsync-master.pid"
# Fonction de logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [MASTER] $1" | tee -a "$LOG_FILE"
}

# Fonction de nettoyage
cleanup() {
    log "Arrêt du processus rsync master"
    rm -f "$PID_FILE"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Vérification de la configuration
if [ -z "$REMOTE_HOSTS" ]; then
    log "ERREUR: REMOTE_HOSTS non défini"
    exit 1
fi

# Sauvegarde du PID
echo $$ > "$PID_FILE"

log "Démarrage du rsync master"
log "Hosts distants: $REMOTE_HOSTS"
log "Intervalle de sync: $SYNC_INTERVAL secondes"

# Fonction de synchronisation
sync_to_slaves() {
    local sync_start=$(date +%s)
    log "Début de la synchronisation"
    
    IFS=',' read -ra HOSTS <<< "$REMOTE_HOSTS"
    for host in "${HOSTS[@]}"; do
        log "Synchronisation vers $host"
        if rsync $RSYNC_OPTIONS \
         --log-file="$LOG_FILE" \
           $DATA_PATH/ \
           rsync://docker@$host/$MODULE/; then
#rsync -avz /opt/bojemoi/ rsync://rsync-slave/swarm_data

            log "Synchronisation vers $host: SUCCÈS"
        else
            log "Synchronisation vers $host: ÉCHEC (code: $?)"
        fi
        if rsync $RSYNC_OPTIONS \
         --log-file="$LOG_FILE" \
           /etc/init.d/ \
           rsync://docker@$host/initd/; then

            log "Synchronisation vers $host init.d: SUCCÈS"
        else
            log "Synchronisation vers $host init.d: ÉCHEC (code: $?)"
        fi
    done
    
    local sync_end=$(date +%s)
    local duration=$((sync_end - sync_start))
    log "Synchronisation terminée en ${duration}s"
}

# Boucle principale
while true; do
    sync_to_slaves
    sleep "$SYNC_INTERVAL"
done
