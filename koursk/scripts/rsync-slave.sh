#!/bin/bash
set -e

LOG_FILE="/var/log/rsync/rsync-slave.log"
PID_FILE="/var/run/rsync-slave.pid"

# Fonction de logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [SLAVE] $1" | tee -a "$LOG_FILE"
}

# Fonction de nettoyage
cleanup() {
    log "Arrêt du processus rsync slave"
    pkill -f "rsync --daemon" || true
    rm -f "$PID_FILE"
    exit 0
}

trap cleanup SIGTERM SIGINT

# Sauvegarde du PID
echo $$ > "$PID_FILE"

log "Démarrage du rsync slave"
log "Master host: $MASTER_HOST"

# Démarrage du daemon rsync
rsync --daemon --no-detach --log-file="$LOG_FILE" &
RSYNC_PID=$!

log "Daemon rsync démarré (PID: $RSYNC_PID)"

# Attente
wait $RSYNC_PID
