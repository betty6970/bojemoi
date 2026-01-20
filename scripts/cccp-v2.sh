#!/bin/ash

# Script cccp.sh - Build et push d'image Docker vers registre local
# Usage: ./cccp.sh [repertoire/nom_image:tag] [registre_local]

set -e  # Arrêt du script en cas d'erreur

# Configuration par défaut
DEFAULT_REGISTRY="localhost:5000"
DEFAULT_TAG="latest"
DEFAULT_DIR="."

# Fonction d'aide
show_help() {
    echo "Usage: $0 [OPTIONS] [REPERTOIRE/NOM_IMAGE]"
    echo ""
    echo "Options:"
    echo "  -r, --registry REGISTRY   Registre local (défaut: $DEFAULT_REGISTRY)"
    echo "  -t, --tag TAG            Tag de l'image (défaut: $DEFAULT_TAG)"
    echo "  -h, --help               Afficher cette aide"
    echo ""
    echo "Arguments:"
    echo "  REPERTOIRE               Répertoire contenant le Dockerfile (défaut: répertoire courant)"
    echo "  NOM_IMAGE                Nom de l'image Docker"
    echo ""
    echo "Exemples:"
    echo "  $0 . mon-app"
    echo "  $0 -t v1.0 ./src mon-service"
    echo "  $0 -r registry.local:5000 -t prod ./app mon-app"
}

# Fonction de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Fonction d'erreur
error() {
    log "ERREUR: $1" >&2
    exit 1
}

# Vérification des prérequis
check_requirements() {
    if ! command -v docker &> /dev/null; then
        error "Docker n'est pas installé ou pas dans le PATH"
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker daemon n'est pas accessible. Vérifiez que Docker est démarré."
    fi
}

# Vérification de la connectivité au registre
check_registry() {
    local registry=$1
    log "Vérification de la connectivité au registre $registry..."
    
    # Test de ping du registre
    if ! curl -s -f "http://$registry/v2/" > /dev/null 2>&1; then
        log "AVERTISSEMENT: Impossible de joindre le registre $registry"
        log "Assurez-vous que le registre est démarré et accessible"
    else
        log "Registre $registry accessible"
    fi
}

# Build de l'image
build_image() {
    local build_dir=$1
    local image_name="Dockerfile.$2"
    local tag="latest"
    local repertoire=$2
 
    log "Construction de l'image $image_name:$tag depuis $build_dir..."
    
    # Vérification de l'existence du Dockerfile
    if [[ ! -f "$build_dir/Dockerfile" ]]; then
        error "Dockerfile non trouvé dans $build_dir"
    fi
    
    # Build de l'image
    docker build -t "$image_name:latest" "$build_dir" || error "Échec du build de l'image"
    
    log "Image $image_name:$tag construite avec succès"
}

# Tag de l'image pour le registre
tag_image() {
    local local_image=$1
    local registry_image=$2
    
    log "Tag de l'image $local_image vers $registry_image..."
    docker tag "$local_image" "$registry_image" || error "Échec du tag de l'image"
}

# Push de l'image vers le registre
push_image() {
    local registry_image=$1
    
    log "Push de l'image $registry_image vers le registre..."
    docker push "$registry_image" || error "Échec du push de l'image"
    
    log "Image $registry_image poussée avec succès"
}

# Nettoyage optionnel
cleanup() {
    local registry_image=$1
    
    read -p "Voulez-vous supprimer l'image locale $registry_image ? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "Suppression de l'image locale $registry_image..."
        docker rmi "$registry_image" || log "AVERTISSEMENT: Impossible de supprimer l'image locale"
    fi
}

# Parsing des arguments
REGISTRY="$DEFAULT_REGISTRY"
TAG="$DEFAULT_TAG"
BUILD_DIR=""
IMAGE_NAME=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        -*)
            error "Option inconnue: $1"
            ;;
        *)
            if [[ -z "$BUILD_DIR" ]]; then
                BUILD_DIR="$1"
                IMAGE_NAME="$1"
            else
                error "Trop d'arguments"
            fi
            shift
            ;;
    esac
done

# Valeurs par défaut
BUILD_DIR="${BUILD_DIR:-$DEFAULT_DIR}"
BUILD_DIR=$(realpath "$BUILD_DIR")

# Vérification des arguments obligatoires
if [[ -z "$IMAGE_NAME" ]]; then
    error "Le nom de l'image est obligatoire. Utilisez -h pour l'aide."
fi

if [[ ! -d "$BUILD_DIR" ]]; then
    error "Le répertoire $BUILD_DIR n'existe pas"
fi

# Variables finales
LOCAL_IMAGE="$IMAGE_NAME:$TAG"
REGISTRY_IMAGE="$REGISTRY/$IMAGE_NAME:$TAG"

# Exécution du script principal
main() {
    log "=== Début du processus de build et push ==="
    log "Répertoire de build: $BUILD_DIR"
    log "Image locale: $LOCAL_IMAGE"
    log "Image registre: $REGISTRY_IMAGE"
    log "Registre: $REGISTRY"
    
    check_requirements
#    check_registry "$REGISTRY"
    cd ${BUILD_DIR}
    build_image "$BUILD_DIR" "$IMAGE_NAME" "$TAG"
    tag_image "$LOCAL_IMAGE" "$REGISTRY_IMAGE"
    push_image "$REGISTRY_IMAGE"
    
    log "=== Processus terminé avec succès ==="
    log "L'image est disponible à l'adresse: $REGISTRY_IMAGE"
    
    # Proposition de nettoyage
    cleanup "$REGISTRY_IMAGE"
}

# Exécution du main
main

