#!/bin/ash

# Script de nettoyage Docker complet
# Nettoie les conteneurs, images, volumes et cache Docker non utilisés

#set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Fonction pour afficher l'espace disque utilisé par Docker
show_docker_disk_usage() {
    print_info "Utilisation de l'espace disque par Docker:"
    docker system df
    echo
}

# Fonction pour demander confirmation
confirm() {
    read -p "$(echo -e ${YELLOW}"$1 (y/N): "${NC})" -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# Fonction principale de nettoyage
cleanup_docker() {
    print_info "=== NETTOYAGE DOCKER COMMENCE ==="
    echo

    # Afficher l'utilisation actuelle
    show_docker_disk_usage

    # 1. Nettoyer les conteneurs arrêtés
    print_info "1. Suppression des conteneurs arrêtés..."
    stopped_containers=$(docker ps -aq --filter "status=exited" --filter "status=created")
    if [ -n "$stopped_containers" ]; then
        docker rm $stopped_containers
        print_success "Conteneurs arrêtés supprimés"
    else
        print_info "Aucun conteneur arrêté à supprimer"
    fi
    echo

    # 2. Nettoyer les images non utilisées (dangling)
    print_info "2. Suppression des images 'dangling' (non taguées)..."
    dangling_images=$(docker images -q --filter "dangling=true")
    if [ -n "$dangling_images" ]; then
        docker rmi $dangling_images
        print_success "Images 'dangling' supprimées"
    else
        print_info "Aucune image 'dangling' à supprimer"
    fi
    echo

    # 3. Nettoyer les réseaux non utilisés
    print_info "3. Suppression des réseaux non utilisés..."
    unused_networks=$(docker network ls --filter "type=custom" -q)
    if [ -n "$unused_networks" ]; then
        docker network prune -f
        print_success "Réseaux non utilisés supprimés"
    else
        print_info "Aucun réseau non utilisé à supprimer"
    fi
    echo

    # 4. Nettoyer les volumes non utilisés
    print_info "4. Suppression des volumes non utilisés..."
    if confirm "Supprimer les volumes non utilisés? (ATTENTION: données perdues définitivement)"; then
        docker volume prune -f
        print_success "Volumes non utilisés supprimés"
    else
        print_warning "Suppression des volumes annulée"
    fi
    echo

    # 5. Nettoyage du cache de build
    print_info "5. Nettoyage du cache de build..."
    docker builder prune -f
    print_success "Cache de build nettoyé"
    echo

    # 6. Option pour nettoyage agressif des images
    if confirm "Supprimer TOUTES les images non utilisées par des conteneurs en cours? (ATTENTION: re-téléchargement nécessaire)"; then
        print_info "6. Suppression de toutes les images non utilisées..."
        docker image prune -a -f
        print_success "Toutes les images non utilisées supprimées"
    else
        print_warning "Suppression des images non utilisées annulée"
    fi
    echo

    # 7. Nettoyage système complet (optionnel)
    if confirm "Effectuer un nettoyage système complet? (supprime tout ce qui n'est pas utilisé)"; then
        print_info "7. Nettoyage système complet..."
        docker system prune -a -f --volumes
        print_success "Nettoyage système complet terminé"
    else
        print_warning "Nettoyage système complet annulé"
    fi
    echo

    # Afficher l'utilisation finale
    print_info "=== NETTOYAGE TERMINÉ ==="
    show_docker_disk_usage
}

# Fonction pour afficher les statistiques détaillées
show_detailed_stats() {
    print_info "=== STATISTIQUES DÉTAILLÉES ==="
    echo
    
    print_info "Conteneurs:"
    docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Size}}"
    echo
    
    print_info "Images:"
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    echo
    
    print_info "Volumes:"
    docker volume ls
    echo
    
    print_info "Réseaux:"
    docker network ls
    echo
}

# Fonction pour sauvegarder les images importantes
backup_images() {
    print_info "=== SAUVEGARDE D'IMAGES ==="
    echo "Images actuellement disponibles:"
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}"
    echo
    
    read -p "Entrez les noms des images à sauvegarder (séparés par des espaces): " images_to_backup
    
    if [ -n "$images_to_backup" ]; then
        mkdir -p docker_backups
        for image in $images_to_backup; do
            print_info "Sauvegarde de $image..."
            filename=$(echo "$image" | tr '/' '_' | tr ':' '_')
            docker save -o "docker_backups/${filename}.tar" "$image"
            print_success "Image $image sauvegardée dans docker_backups/${filename}.tar"
        done
    fi
}

# Menu principal
show_menu() {
    echo
    print_info "=== SCRIPT DE NETTOYAGE DOCKER ==="
    echo "1. Nettoyage complet (recommandé)"
    echo "2. Nettoyage sélectif"
    echo "3. Afficher les statistiques détaillées"
    echo "4. Sauvegarder des images importantes"
    echo "5. Afficher l'utilisation disque"
    echo "6. Quitter"
    echo
    read -p "Choisissez une option (1-6): " choice
}

# Vérifier que Docker est installé et en cours d'exécution
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker n'est pas installé sur ce système"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker n'est pas en cours d'exécution ou vous n'avez pas les permissions nécessaires"
        exit 1
    fi
}

# Script principal
main() {
    check_docker
    
    # Si des arguments sont passés, exécuter directement
    case "${1:-}" in
        "--full"|"-f")
            cleanup_docker
            exit 0
            ;;
        "--stats"|"-s")
            show_detailed_stats
            exit 0
            ;;
        "--help"|"-h")
            echo "Usage: $0 [OPTION]"
            echo "Options:"
            echo "  --full, -f     Nettoyage complet automatique"
            echo "  --stats, -s    Afficher les statistiques détaillées"
            echo "  --help, -h     Afficher cette aide"
            exit 0
            ;;
    esac
    
    # Menu interactif
    while true; do
        show_menu
        case $choice in
            1)
                cleanup_docker
                ;;
            2)
                print_info "Nettoyage sélectif non implémenté dans cette version"
                print_info "Utilisez les commandes individuelles ou le nettoyage complet"
                ;;
            3)
                show_detailed_stats
                ;;
            4)
                backup_images
                ;;
            5)
                show_docker_disk_usage
                ;;
            6)
                print_info "Au revoir!"
                exit 0
                ;;
            *)
                print_error "Option invalide. Veuillez choisir entre 1 et 6."
                ;;
        esac
        
        echo
        read -p "Appuyez sur Entrée pour continuer..."
    done
}

# Exécuter le script
main "$@"
