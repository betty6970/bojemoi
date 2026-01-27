#!/bin/bash
set -e

# Configuration
KEY_DIR="./ssh-keys"
KEY_NAME="id_rsa"
KEY_SIZE=4096
COMMENT="rsync-swarm-$(date +%Y%m%d-%H%M%S)"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Création du répertoire
log "Création du répertoire des clés..."
mkdir -p "$KEY_DIR"

# Vérification si les clés existent déjà
if [ -f "$KEY_DIR/$KEY_NAME" ]; then
    warn "Les clés existent déjà dans $KEY_DIR"
    read -p "Voulez-vous les remplacer ? (y/N): " confirm
    if [[ $confirm != [yY] ]]; then
        log "Opération annulée"
        exit 0
    fi
    
    # Sauvegarde des anciennes clés
    BACKUP_DIR="$KEY_DIR/backup-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    mv "$KEY_DIR/$KEY_NAME"* "$BACKUP_DIR/" 2>/dev/null || true
    log "Anciennes clés sauvegardées dans $BACKUP_DIR"
fi

# Génération de la paire de clés
log "Génération de la paire de clés RSA $KEY_SIZE bits..."
ssh-keygen -t rsa \
           -b "$KEY_SIZE" \
           -f "$KEY_DIR/$KEY_NAME" \
           -N "" \
           -C "$COMMENT"

# Configuration des permissions
log "Configuration des permissions sécurisées..."
chmod 700 "$KEY_DIR"
chmod 600 "$KEY_DIR/$KEY_NAME"
chmod 644 "$KEY_DIR/$KEY_NAME.pub"

# Affichage des informations
log "✅ Clés générées avec succès !"
echo ""
echo "� Emplacement: $KEY_DIR"
echo "� Clé privée: $KEY_NAME"
echo "� Clé publique: $KEY_NAME.pub"
echo ""

# Affichage de l'empreinte
log "Empreinte de la clé:"
ssh-keygen -l -f "$KEY_DIR/$KEY_NAME.pub"

# Affichage de la clé publique
echo ""
log "Contenu de la clé publique:"
cat "$KEY_DIR/$KEY_NAME.pub"

# Instructions suivantes
echo ""
echo "� Prochaines étapes:"
echo "1. Déployez la clé publique sur les serveurs cibles"
echo "2. Créez le volume Docker: docker volume create rsync_ssh_keys"
echo "3. Copiez les clés dans le volume avec deploy-keys-to-docker.sh"
