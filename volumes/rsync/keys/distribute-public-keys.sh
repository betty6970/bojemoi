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
