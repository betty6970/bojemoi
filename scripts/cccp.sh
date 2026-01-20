#!/bin/ash

# Script pour créer et pousser une image Docker vers un registry local
# Usage: ./build_and_push.sh <nom_du_service>
# Compatible avec Alpine Linux (ash shell)

set -e  # Arrêter le script en cas d'erreur

# Configuration
REGISTRY_HOST="${REGISTRY_HOST:-localhost:5000}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
VERSION="${VERSION:-latest}"

# Fonction d'aide
show_help() {
    cat << EOF
Usage: $0 <repertoire> <nom_du_service>

Ce script construit une image Docker et la pousse vers le registry local.

Arguments:
  nom_du_service    Nom du service/image à créer

Variables d'environnement optionnelles:
  REGISTRY_HOST     Registry de destination (défaut: localhost:5000)
  VERSION           Version du tag (défaut: latest)

Exemple:
  $0 mon-api
  VERSION=v1.0.0 $0 mon-api
EOF
}

# Fonction de validation du nom de service
validate_service_name() {
    local service_name="$1"
    
    # Vérifier que le nom n'est pas vide
    if [ -z "$service_name" ]; then
        echo "❌ Erreur: Le nom du service ne peut pas etre vide"
        return 1
    fi
    
    # Vérifier le format (compatible avec ash)
    case "$service_name" in
        *[!a-zA-Z0-9_./-]*)
            echo "❌ Erreur: Le nom du service doit contenir uniquement des lettres, chiffres, tirets, points et underscores"
            return 1
            ;;
        [!a-zA-Z0-9]*) 
            echo "❌ Erreur: Le nom du service doit commencer par une lettre ou un chiffre"
            return 1
            ;;
    esac
    
    return 0
}

# Fonction pour vérifier les dépendances
check_dependencies() {
    local missing_deps=""
    
    # Vérifier Docker
    if ! command -v docker >/dev/null 2>&1; then
        missing_deps="$missing_deps docker"
    fi
    
    # Vérifier curl pour les tests de registry
    if ! command -v curl >/dev/null 2>&1; then
        missing_deps="$missing_deps curl"
    fi
    
    if [ -n "$missing_deps" ]; then
        echo "❌ Erreur: Dépendances manquantes:$missing_deps"
        echo "Sur Alpine Linux, installez avec: apk add$missing_deps"
        return 1
    fi
    
    return 0
}

# Fonction pour vérifier les fichiers requis
check_required_files() {
    local repertoire="$1"
    local service_name="$2"
    
    # Vérifier si le répertoire existe
    if [ ! -d "$repertoire" ]; then
        echo "❌ Erreur: Le repertoire '$repertoire' n'existe pas"
        echo "Assurez-vous d'être dans le répertoire parent contenant ./$repertoire"
#        return 1
    fi
    
    # Vérifier si le Dockerfile existe
    if [ ! -f "$repertoire/Dockerfile.$service_name" ]; then
        echo "❌ Erreur: Dockerfile.$service_name non trouve dans le repertoire $repertoire"
        echo "Fichiers trouvés dans $repertoire:"
        ls -la "$repertoire/$service_name/" 2>/dev/null || echo "  (impossible de lister le contenu)"
        return 1
    fi
    
    return 0
}

# Fonction pour tester l'accessibilité du registry
test_registry_connectivity() {
    local registry_host="$1"
    
    echo "🔍 Vérification de l'accessibilité du registry $registry_host..."
    
    # Utiliser wget comme fallback si curl n'est pas disponible
    if command -v curl >/dev/null 2>&1; then
        if curl -4 -s --connect-timeout 5 "http://$registry_host/v2/" >/dev/null 2>&1; then
            return 0
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q --timeout=5 -O /dev/null "http://$registry_host/v2/" >/dev/null 2>&1; then
            return 0
        fi
    fi
    
    return 1
}

# Fonction pour demander confirmation (compatible ash)
ask_confirmation() {
    local prompt="$1"
    local response
    
    printf "%s [y/N]: " "$prompt"
    read -r response
    
    case "$response" in
        [Yy]|[Yy][Ee][Ss]) return 0 ;;
        *) return 1 ;;
    esac
}

# Fonction principale de construction
build_image() {
    local service_name="$1"
    local local_tag="$2"
    
    echo "📦 Construction de l'image $local_tag..."
    
    # Changer vers le répertoire du service
    cd "$service_name" || {
        echo "❌ Erreur: Impossible de changer vers le répertoire $service_name"
        return 1
    }
    
    # Construction avec gestion d'erreur améliorée
    if docker build --no-cache -f "Dockerfile.$service_name" -t "$local_tag" .; then
        echo "✅ Image construite avec succès"
        cd ..
        return 0
    else
        echo "❌ Erreur lors de la construction de l'image"
        cd ..
        return 1
    fi
}

# Fonction pour pusher vers le registry
push_to_registry() {
    local tag="$1"
    
    echo "   Pushing $tag..."
    if docker push "$tag"; then
        echo "✅ Push $tag réussi"
        return 0
    else
        echo "❌ Erreur lors du push $tag"
        return 1
    fi
}

# Fonction principale
main() {
    # Vérifier les arguments
    if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        show_help
        exit 0
    fi
    
    local service_name="$2"
    local repertoire="$1"
 
    # Validation et vérifications
    validate_service_name "$service_name" || exit 1
    check_dependencies || exit 1
    check_required_files "$repertoire" "$service_name" || exit 1
#---------------------
# 
     scripts/tannenberg.py $service_name -f 
    
    # Définir les tags
    local local_tag="${service_name}:${VERSION}"
    local registry_tag="${REGISTRY_HOST}/${service_name}:${VERSION}"
    local timestamp_tag="${REGISTRY_HOST}/${service_name}:${TIMESTAMP}"
    
    # Afficher les informations
    echo "🔨 Construction de l'image Docker..."
    echo "   Service: $service_name"
    echo "   Tag local: $local_tag"
    echo "   Tag registry: $registry_tag"
    echo "   Tag timestamp: $timestamp_tag"
    echo ""
    
    # Construction de l'image
    build_image "$service_name" "$local_tag" || exit 1
    
    # Tagger pour le registry
    echo "🏷️  Ajout des tags pour le registry..."
    docker tag "$local_tag" "$registry_tag" || {
        echo "❌ Erreur lors du tagging $registry_tag"
        exit 1
    }
    docker tag "$local_tag" "$timestamp_tag" || {
        echo "❌ Erreur lors du tagging $timestamp_tag"
        exit 1
    }
    
    # Vérifier la connectivité du registry
    if ! test_registry_connectivity "$REGISTRY_HOST"; then
        echo "⚠️  Attention: Le registry $REGISTRY_HOST ne semble pas accessible"
        echo "   Assurez-vous qu'il est démarré avec:"
        echo "   docker run -d -p 5000:5000 --name registry registry:2"
        
        if ! ask_confirmation "Voulez-vous continuer quand même?"; then
            echo "❌ Opération annulée"
            exit 1
        fi
    fi
    
    # Push vers le registry
    echo "🚀 Push vers le registry..."
    push_to_registry "$registry_tag" || exit 1
    push_to_registry "$timestamp_tag" || exit 1
    
    # Résumé
    cat << EOF

🎉 Opération terminée avec succès!

📋 Résumé:
   Image locale: $local_tag
   Images dans le registry:
     - $registry_tag
     - $timestamp_tag

💡 Pour utiliser l'image:
   docker pull $registry_tag
   docker run $registry_tag

🔍 Pour voir les images dans le registry:
   curl http://$REGISTRY_HOST/v2/_catalog
   curl http://$REGISTRY_HOST/v2/$service_name/tags/list
EOF
}

# Exécuter la fonction principale avec tous les arguments
main "$@"

