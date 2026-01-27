#!/bin/bash
set -e

# Configuration
KEY_DIR="./ssh-keys"
VOLUME_NAME="rsync_ssh_keys"

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

echo "� Test et validation des clés SSH"
echo "=================================="

# Test 1: Vérification des fichiers locaux
log "Test 1: Vérification des fichiers locaux"
if [ ! -f "$KEY_DIR/id_rsa" ]; then
    error "Clé privée manquante: $KEY_DIR/id_rsa"
fi

if [ ! -f "$KEY_DIR/id_rsa.pub" ]; then
    error "Clé publique manquante: $KEY_DIR/id_rsa.pub"
fi

# Vérification des permissions
PRIV_PERMS=$(stat -c "%a" "$KEY_DIR/id_rsa")
PUB_PERMS=$(stat -c "%a" "$KEY_DIR/id_rsa.pub")

if [ "$PRIV_PERMS" != "600" ]; then
    warn "Permissions clé privée incorrectes: $PRIV_PERMS (devrait être 600)"
    chmod 600 "$KEY_DIR/id_rsa"
    log "Permissions corrigées"
fi

if [ "$PUB_PERMS" != "644" ]; then
    warn "Permissions clé publique incorrectes: $PUB_PERMS (devrait être 644)"
    chmod 644 "$KEY_DIR/id_rsa.pub"
    log "Permissions corrigées"
fi

echo "  ✅ Fichiers locaux OK"

# Test 2: Validité cryptographique
log "Test 2: Validité cryptographique"
if ssh-keygen -y -f "$KEY_DIR/id_rsa" > /tmp/test_pub_key 2>/dev/null; then
    echo "  ✅ Clé privée valide"
else
    error "Clé privée corrompue ou invalide"
fi

# Comparaison avec la clé publique
if diff -q "$KEY_DIR/id_rsa.pub" /tmp/test_pub_key >/dev/null 2>&1; then
    echo "  ✅ Paire de clés cohérente"
else
    error "La clé publique ne correspond pas à la clé privée"
fi

rm -f /tmp/test_pub_key

# Test 3: Volume Docker
log "Test 3: Volume Docker"
if docker volume inspect "$VOLUME_NAME" >/dev/null 2>&1; then
    echo "  ✅ Volume Docker existe"
    
    # Test du contenu
    VOLUME_CONTENT=$(docker run --rm -v "$VOLUME_NAME":/keys alpine:3.18 ls -la /keys/ 2>/dev/null || echo "ERREUR")
    
    if [[ $VOLUME_CONTENT == *"id_rsa"* ]]; then
        echo "  ✅ Clés présentes dans le volume"
        
        # Test de validité dans le volume
        if docker run --rm -v "$VOLUME_NAME":/keys alpine:3.18 sh -c "
            apk add --no-cache openssh-client >/dev/null 2>&1
            ssh-keygen -y -f /keys/id_rsa >/dev/null 2>&1
        "; then
            echo "  ✅ Clés valides dans le volume Docker"
        else
            warn "Clés invalides dans le volume Docker"
        fi
    else
        warn "Clés manquantes dans le volume Docker"
        echo "Contenu du volume:"
        echo "$VOLUME_CONTENT"
    fi
else
    warn "Volume Docker '$VOLUME_NAME' n'existe pas"
fi

# Test 4: Informations de la clé
log "Test 4: Informations de la clé"
echo "Empreinte:"
ssh-keygen -l -f "$KEY_DIR/id_rsa.pub"

echo ""
echo "Type et taille:"
ssh-keygen -l -f "$KEY_DIR/id_rsa.pub" | awk '{print "  Type: " $4 ", Taille: " $1 " bits"}'

echo ""
echo "Commentaire:"
tail -c 50 "$KEY_DIR/id_rsa.pub"

# Test 5: Test de connexion (si serveurs fournis)
if [ $# -gt 0 ]; then
    log "Test 5: Test de connexion aux serveurs"
    DEFAULT_USER="rsync"
    
    for server in "$@"; do
        if [[ $server == *"@"* ]]; then
            target="$server"
        else
            target="$DEFAULT_USER@$server"
        fi
        
        if ssh -i "$KEY_DIR/id_rsa" \
               -o ConnectTimeout=5 \
               -o StrictHostKeyChecking=no \
               -o UserKnownHostsFile=/dev/null \
               -o LogLevel=ERROR \
               "$target" "echo 'SSH OK'" 2>/dev/null; then
            echo "  ✅ Connexion OK: $target"
        else
            echo "  ❌ Connexion KO: $target"
        fi
    done
else
    log "Test 5: Aucun serveur fourni pour test de connexion"
    echo "Usage: $0 [server1] [server2] ..."
fi

echo ""
log "� Tests terminés"
