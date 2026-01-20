#!/bin/bash

# Script pour synchroniser les images d'un Docker Stack vers une registry privée
# Usage: ./sync-stack-images.sh <compose-file> <registry-url>

set -e

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérification des arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <compose-file> <registry-url>"
    echo "Exemple: $0 docker-compose.yml registry.bojemoi.lab:5000"
    exit 1
fi

COMPOSE_FILE="$1"
REGISTRY_URL="$2"

# Vérification de l'existence du fichier
if [ ! -f "$COMPOSE_FILE" ]; then
    log_error "Le fichier $COMPOSE_FILE n'existe pas"
    exit 1
fi

log_info "Lecture du fichier: $COMPOSE_FILE"
log_info "Registry cible: $REGISTRY_URL"

# Extraction des images depuis le compose file
# Utilise docker-compose config pour résoudre les variables d'environnement
log_info "Extraction des images..."

IMAGES=$(docker compose -f "$COMPOSE_FILE" config | grep -E "^\s+image:" | awk '{print $2}' | sort -u)

if [ -z "$IMAGES" ]; then
    log_error "Aucune image trouvée dans le fichier compose"
    exit 1
fi

# Compteurs
TOTAL=0
SUCCESS=0
FAILED=0

echo ""
log_info "Images trouvées:"
echo "$IMAGES" | while read -r image; do
    echo "  - $image"
done
echo ""

# Demande de confirmation
read -p "Voulez-vous continuer avec le push de ces images? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_warn "Opération annulée"
    exit 0
fi

echo ""

# Traitement de chaque image
while IFS= read -r IMAGE; do
    TOTAL=$((TOTAL + 1))
    
    log_info "======================================"
    log_info "Traitement de: $IMAGE"
    
    # Pull de l'image si elle n'existe pas localement
    if ! docker image inspect "$IMAGE" &>/dev/null; then
        log_info "Pull de l'image..."
        if ! docker pull "$IMAGE"; then
            log_error "Échec du pull de $IMAGE"
            FAILED=$((FAILED + 1))
            continue
        fi
    else
        log_info "Image déjà présente localement"
    fi
    
    # Création du nouveau tag pour la registry
    # Extrait le nom de l'image sans le registry source
    IMAGE_NAME=$(echo "$IMAGE" | sed 's|^[^/]*/||' | sed 's|^[^/]*/||')
    NEW_TAG="${REGISTRY_URL}/${IMAGE_NAME}"
    
    log_info "Tag vers: $NEW_TAG"
    if ! docker tag "$IMAGE" "$NEW_TAG"; then
        log_error "Échec du tag de $IMAGE"
        FAILED=$((FAILED + 1))
        continue
    fi
    
    # Push vers la registry
    log_info "Push vers la registry..."
    if docker push "$NEW_TAG"; then
        log_info "✓ Image pushée avec succès: $NEW_TAG"
        SUCCESS=$((SUCCESS + 1))
    else
        log_error "✗ Échec du push de $NEW_TAG"
        FAILED=$((FAILED + 1))
    fi
    
    echo ""
done <<< "$IMAGES"

# Résumé
log_info "======================================"
log_info "Résumé de la synchronisation"
log_info "======================================"
echo "Total d'images: $TOTAL"
echo -e "${GREEN}Succès: $SUCCESS${NC}"
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}Échecs: $FAILED${NC}"
fi

if [ $FAILED -eq 0 ]; then
    log_info "Toutes les images ont été synchronisées avec succès!"
    exit 0
else
    log_error "Certaines images n'ont pas pu être synchronisées"
    exit 1
fi

