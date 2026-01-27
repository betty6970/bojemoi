#!/bin/bash
set -e

# Configuration
KEY_DIR="./ssh-keys"
VOLUME_NAME="rsync_ssh_keys"
BACKUP_DIR="$KEY_DIR/rotation-backup-$(date +%Y%m%d-%H%M%S)"

log() {
    echo -e "\033[0;32m[$(date '+%H:%M:%S')]\033[0m $1"
}

error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
    exit 1
}

warn() {
    echo -e "\033[1;33m[WARNING]\033[0m $1"
}

echo "� Rotation des clés SSH"
echo "======================"

# Vérification des clés existantes
if [ ! -f "$KEY_DIR/id_rsa" ]; then
    error "Aucune clé existante trouvée dans $KEY_DIR"
fi

# Sauvegarde des anciennes clés
log "Sauvegarde des anciennes clés..."
mkdir -p "$BACKUP_DIR"
