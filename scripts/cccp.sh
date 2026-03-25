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
    if curl -4 -s --connect-timeout 5 "http://$registry_host/v2/" >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Fonction pour s'assurer que la registry est disponible (déploie boot si nécessaire)
ensure_registry() {
    local registry_host="$1"
    local boot_stack_file="/opt/bojemoi_boot/stack/01-boot-service.yml"
    local max_wait=60

    echo "🔍 Vérification du registry $registry_host..."

    if test_registry_connectivity "$registry_host"; then
        echo "✅ Registry accessible"
        return 0
    fi

    echo "⚠️  Registry non accessible — vérification de la stack boot..."

    # Vérifier si le service boot_registry existe déjà
    if docker service ls --format "{{.Name}}" 2>/dev/null | grep -q "^boot_registry$"; then
        echo "   Service boot_registry présent mais non répondant, attente..."
    else
        echo "🚀 Déploiement de la stack boot ($boot_stack_file)..."
        if [ ! -f "$boot_stack_file" ]; then
            echo "❌ Fichier stack introuvable: $boot_stack_file"
            return 1
        fi
        docker stack deploy -c "$boot_stack_file" boot --resolve-image always || {
            echo "❌ Echec du déploiement de la stack boot"
            return 1
        }
    fi

    # Attendre que la registry réponde (max $max_wait secondes)
    echo "   Attente du registry (max ${max_wait}s)..."
    local elapsed=0
    while [ $elapsed -lt $max_wait ]; do
        if test_registry_connectivity "$registry_host"; then
            echo "✅ Registry disponible (${elapsed}s)"
            return 0
        fi
        sleep 3
        elapsed=$((elapsed + 3))
        printf "."
    done

    echo ""
    echo "❌ Registry toujours inaccessible après ${max_wait}s"
    return 1
}


# Fonction principale de construction + push direct vers registry (sans stockage local)
build_and_push() {
    local service_name="$1"
    local registry_tag="$2"
    local timestamp_tag="$3"

    echo "📦 Build + push direct vers registry (sans stockage local)..."

    cd "$service_name" || {
        echo "❌ Erreur: Impossible de changer vers le répertoire $service_name"
        return 1
    }

    if docker buildx build \
        --no-cache \
        --push \
        -f "Dockerfile.$service_name" \
        -t "$registry_tag" \
        -t "$timestamp_tag" \
        .; then
        echo "✅ Build + push réussis"
        cd ..
        return 0
    else
        echo "❌ Erreur lors du build/push"
        cd ..
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
    # Définir les tags (registry uniquement, pas de tag local)
    local registry_tag="${REGISTRY_HOST}/${service_name}:${VERSION}"
    local timestamp_tag="${REGISTRY_HOST}/${service_name}:${TIMESTAMP}"

    # Afficher les informations
    echo "🔨 Build direct vers registry (sans stockage local)..."
    echo "   Service: $service_name"
    echo "   Tag registry: $registry_tag"
    echo "   Tag timestamp: $timestamp_tag"
    echo ""

    # S'assurer que la registry est disponible (déploie boot si nécessaire)
    ensure_registry "$REGISTRY_HOST" || exit 1

    # Build + push direct (pas de stockage local, pas de docker tag)
    build_and_push "$service_name" "$registry_tag" "$timestamp_tag" || exit 1

    # Résumé
    cat << EOF

🎉 Opération terminée avec succès!

📋 Résumé (aucune image stockée localement):
   Images dans le registry:
     - $registry_tag
     - $timestamp_tag

💡 Pour utiliser l'image:
   docker pull $registry_tag
   docker run $registry_tag

🔍 Pour voir les images dans le registry:
   curl -4 http://$REGISTRY_HOST/v2/_catalog
   curl -4 http://$REGISTRY_HOST/v2/$service_name/tags/list
EOF
}

# Exécuter la fonction principale avec tous les arguments
main "$@"

