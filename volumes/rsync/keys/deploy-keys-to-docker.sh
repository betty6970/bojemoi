#!/bin/bash
set -e

# Configuration
KEY_DIR="./ssh-keys"
VOLUME_NAME="rsync_ssh_keys"
CONTAINER_NAME="rsync-key-deployer"

log() {
    echo -e "\033[0;32m[$(date '+%H:%M:%S')]\033[0m $1"
}

error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
    exit 1
}

# Vérification des clés
if [ ! -f "$KEY_DIR/id_rsa" ]; then
    error "Clé privée introuvable dans $KEY_DIR/id_rsa"
fi

if [ ! -f "$KEY_DIR/id_rsa.pub" ]; then
    error "Clé publique introuvable dans $KEY_DIR/id_rsa.pub"
fi

# Création du volume Docker
log "Création du volume Docker '$VOLUME_NAME'..."
docker volume create "$VOLUME_NAME" || true

# Nettoyage du conteneur existant
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Déploiement des clés
log "Déploiement des clés SSH dans le volume Docker..."
docker run --name "$CONTAINER_NAME" \
    -v "$VOLUME_NAME":/keys \
    -v "$(pwd)/$KEY_DIR":/host_keys:ro \
    alpine:3.18 sh -c "
    echo 'Copie des clés...'
    cp /host_keys/id_rsa /keys/
    cp /host_keys/id_rsa.pub /keys/
    
    echo 'Configuration des permissions...'
    chmod 600 /keys/id_rsa
    chmod 644 /keys/id_rsa.pub
    chown root:root /keys/*
    
    echo 'Création de la configuration SSH...'
    cat > /keys/config << 'SSHCONFIG'
Host *
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
    IdentityFile /root/.ssh/id_rsa
SSHCONFIG
    chmod 600 /keys/config
    
    echo 'Vérification du contenu du volume:'
    ls -la /keys/
    
    echo 'Test de la clé privée:'
    ssh-keygen -y -f /keys/id_rsa >/dev/null && echo 'Clé privée valide ✅' || echo 'Clé privée invalide ❌'
"

# Nettoyage
docker rm "$CONTAINER_NAME"

log "✅ Clés déployées avec succès dans le volume '$VOLUME_NAME'"

# Vérification
log "Vérification du déploiement..."
docker run --rm -v "$VOLUME_NAME":/keys alpine:3.18 \
    sh -c "echo 'Contenu du volume:' && ls -la /keys/"
