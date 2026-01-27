#!/bin/bash

# =============================================================================
# Scripts de gestion des clés SSH pour rsync + Docker Swarm
# =============================================================================

# Script 1: Génération sécurisée des clés
cat > generate-ssh-keys.sh << 'EOF'
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
EOF

# Script 2: Déploiement des clés dans Docker
cat > deploy-keys-to-docker.sh << 'EOF'
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
EOF

# Script 3: Distribution des clés publiques vers les serveurs
cat > distribute-public-keys.sh << 'EOF'
#!/bin/bash
set -e

# Configuration
KEY_DIR="./ssh-keys"
PUBLIC_KEY="$KEY_DIR/id_rsa.pub"
DEFAULT_USER="rsync"

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

# Vérification de la clé publique
if [ ! -f "$PUBLIC_KEY" ]; then
    error "Clé publique introuvable: $PUBLIC_KEY"
fi

# Configuration des serveurs
if [ $# -eq 0 ]; then
    echo "Usage: $0 server1 [server2] [server3] ..."
    echo "       $0 user@server1 user@server2 ..."
    echo ""
    echo "Exemples:"
    echo "  $0 192.168.1.10 192.168.1.11 192.168.1.12"
    echo "  $0 rsync@server1 backup@server2"
    exit 1
fi

SERVERS=("$@")

log "Distribution de la clé publique vers ${#SERVERS[@]} serveur(s)..."
echo "Clé publique: $PUBLIC_KEY"
echo ""

# Affichage de la clé
log "Contenu de la clé publique:"
cat "$PUBLIC_KEY"
echo ""

# Distribution vers chaque serveur
SUCCESS_COUNT=0
FAILED_SERVERS=()

for server in "${SERVERS[@]}"; do
    log "Distribution vers $server..."
    
    # Extraction user@host ou utilisation user par défaut
    if [[ $server == *"@"* ]]; then
        target="$server"
    else
        target="$DEFAULT_USER@$server"
    fi
    
    # Tentative de copie de la clé
    if ssh-copy-id -i "$PUBLIC_KEY" "$target" 2>/dev/null; then
        echo "  ✅ Succès pour $target"
        ((SUCCESS_COUNT++))
    else
        echo "  ❌ Échec pour $target"
        FAILED_SERVERS+=("$target")
        
        # Tentative manuelle
        warn "Tentative de copie manuelle pour $target..."
        if cat "$PUBLIC_KEY" | ssh "$target" 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys'; then
            echo "  ✅ Copie manuelle réussie pour $target"
            ((SUCCESS_COUNT++))
        else
            echo "  ❌ Copie manuelle échouée pour $target"
        fi
    fi
    echo ""
done

# Résumé
log "Distribution terminée:"
echo "  ✅ Succès: $SUCCESS_COUNT/${#SERVERS[@]} serveurs"

if [ ${#FAILED_SERVERS[@]} -gt 0 ]; then
    warn "Échecs pour les serveurs suivants:"
    for failed in "${FAILED_SERVERS[@]}"; do
        echo "    - $failed"
    done
fi

# Test des connexions
echo ""
log "Test des connexions SSH..."
for server in "${SERVERS[@]}"; do
    if [[ $server == *"@"* ]]; then
        target="$server"
    else
        target="$DEFAULT_USER@$server"
    fi
    
    if ssh -i "$KEY_DIR/id_rsa" -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$target" "echo 'Connexion SSH OK'" 2>/dev/null; then
        echo "  ✅ Connexion SSH OK: $target"
    else
        echo "  ❌ Connexion SSH KO: $target"
    fi
done
EOF

# Script 4: Test et validation des clés
cat > test-ssh-keys.sh << 'EOF'
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
EOF

# Script 5: Rotation des clés
cat > rotate-ssh-keys.sh << 'EOF'
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
EOF
