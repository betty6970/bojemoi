#!/bin/ash
# Script de déploiement interactif des stacks Docker Swarm
# Compatible Alpine Linux
set -e  # Arrêt du script en cas d'erreur

STACK_DIR="./stack"
LOG_FILE="deploy-stacks.log"

# Couleurs pour Alpine (compatible POSIX)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    BOLD=''
    NC=''
fi

# Fonction de logging avec couleurs
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_color() {
    printf "${1}[$(date '+%Y-%m-%d %H:%M:%S')] ${2}${NC}\n" | tee -a "$LOG_FILE"
}

# Fonction pour extraire le nom du service depuis le nom de fichier
extract_service_name() {
    local filename="$1"
    # Supprime l'extension .yml/.yaml et la partie numérotée
    echo "$filename" | sed -E 's/^[0-9]+-service-(.+)\.(yml|yaml)$/\1/'
}

# Fonction pour extraire le numéro d'ordre
extract_order_number() {
    local filename="$1"
    echo "$filename" | sed -E 's/^([0-9]+)-service-.+\.(yml|yaml)$/\1/'
}

# Vérifications préliminaires
check_prerequisites() {
    log_color $BLUE "Vérification des prérequis..."
    
    # Vérification de l'existence du répertoire stack
    if [ ! -d "$STACK_DIR" ]; then
        log_color $RED "ERREUR: Le répertoire '$STACK_DIR' n'existe pas"
        exit 1
    fi
    
    # Vérification que Docker est disponible
    if ! command -v docker >/dev/null 2>&1; then
        log_color $RED "ERREUR: Docker n'est pas installé ou pas dans le PATH"
        exit 1
    fi
    
    # Vérification que Docker Swarm est initialisé
    if ! docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null | grep -q "active"; then
        log_color $RED "ERREUR: Docker Swarm n'est pas initialisé"
        log_color $YELLOW "Exécutez 'docker swarm init' avant de lancer ce script"
        exit 1
    fi
    
    log_color $GREEN "✓ Prérequis validés"
}

# Fonction pour lister les fichiers disponibles
list_available_files() {
    log_color $BLUE "=== FICHIERS DISPONIBLES POUR DÉPLOIEMENT ==="
    counter=1
    file_list=""
    
    # Recherche des fichiers dans l'ordre
    for file in "$STACK_DIR"/[0-9][0-9]-service-*.yml "$STACK_DIR"/[0-9][0-9]-service-*.yaml; do
        # Vérifier que le fichier existe
        [ -f "$file" ] || continue
        
        filename=$(basename "$file")
        service_name=$(extract_service_name "$filename")
        order_num=$(extract_order_number "$filename")
        
        if [ -n "$service_name" ]; then
            printf "${YELLOW}%2d)${NC} ${BOLD}%s${NC} (ordre: %s)\n" "$counter" "$service_name" "$order_num"
            printf "     Fichier: %s\n\n" "$filename"
            
            # Stocker les informations (format: counter:filepath:service_name)
            if [ -z "$file_list" ]; then
                file_list="${counter}:${file}:${service_name}"
            else
                file_list="${file_list}|${counter}:${file}:${service_name}"
            fi
            
            counter=$((counter + 1))
        fi
    done
    
    if [ $counter -eq 1 ]; then
        log_color $RED "Aucun fichier de service trouvé dans $STACK_DIR"
        log "Format attendu: [00-99]-service-<nom>.[yml|yaml]"
        exit 1
    fi
    
    echo "$file_list"
}

# Fonction pour déployer un fichier spécifique
deploy_single_stack() {
    local file="$1"
    local service_name="$2"
    local filename=$(basename "$file")
    
    log_color $BLUE "Déploiement de la stack '$service_name' depuis '$filename'"
    
    # Validation du fichier YAML
    if ! docker stack config -c "$file" >/dev/null 2>&1; then
        log_color $RED "ERREUR: Le fichier '$filename' n'est pas un fichier Docker Compose valide"
        return 1
    fi
    
    # Déployer la stack
    if docker stack deploy -c "$file" "$service_name"; then
        log_color $GREEN "✓ Stack '$service_name' déployée avec succès"
        
        # Afficher l'état de la stack déployée
        printf "\n${BOLD}État de la stack déployée:${NC}\n"
        docker stack ps "$service_name" --format "table {{.Name}}\t{{.Image}}\t{{.CurrentState}}"
        
        return 0
    else
        log_color $RED "✗ Échec du déploiement de la stack '$service_name'"
        return 1
    fi
}

# Fonction pour déployer toutes les stacks
deploy_all_stacks() {
    log_color $BLUE "Début du déploiement de toutes les stacks"
    
    deployed_count=0
    failed_count=0
    
    # Déploiement des stacks dans l'ordre
    for file in "$STACK_DIR"/[0-9][0-9]-service-*.yml "$STACK_DIR"/[0-9][0-9]-service-*.yaml; do
        [ -f "$file" ] || continue
        
        filename=$(basename "$file")
        service_name=$(extract_service_name "$filename")
        
        if [ -z "$service_name" ]; then
            log_color $RED "ERREUR: Impossible d'extraire le nom du service depuis '$filename'"
            failed_count=$((failed_count + 1))
            continue
        fi
        
        if deploy_single_stack "$file" "$service_name"; then
            deployed_count=$((deployed_count + 1))
            # Petite pause entre les déploiements
            if [ -f "$STACK_DIR"/[0-9][0-9]-service-*.yml ] || [ -f "$STACK_DIR"/[0-9][0-9]-service-*.yaml ]; then
                printf "${YELLOW}Pause de 10 secondes avant le prochain déploiement...${NC}\n"
                sleep 10
            fi
        else
            failed_count=$((failed_count + 1))
        fi
        
        printf "\n"
    done
    
    # Résumé final
    printf "\n${BOLD}${BLUE}=== RÉSUMÉ DU DÉPLOIEMENT ===${NC}\n"
    log_color $GREEN "Stacks déployées avec succès: $deployed_count"
    log_color $RED "Stacks en échec: $failed_count"
    log "Total traité: $((deployed_count + failed_count))"
    
    # Affichage de l'état des stacks
    if [ $deployed_count -gt 0 ]; then
        printf "\n${BOLD}État actuel des stacks:${NC}\n"
        docker stack ls
    fi
    
    return $failed_count
}

# Fonction principale
main() {
    printf "${BOLD}${BLUE}Script de déploiement Docker Swarm interactif${NC}\n"
    printf "${BLUE}Répertoire: $STACK_DIR${NC}\n\n"
    
    # Vérifications
    check_prerequisites
    
    # Lister les fichiers disponibles
    list_available_files
    
    if [ -z "$file_list" ]; then
        exit 1
    fi
    
    # Menu de choix
    printf "${BOLD}Options disponibles:${NC}\n"
    printf "${YELLOW} a)${NC} Déployer toutes les stacks dans l'ordre\n"
    printf "${YELLOW} q)${NC} Quitter\n\n"
    
    printf "${BLUE}Entrez le numéro du fichier à déployer, 'a' pour tout déployer, ou 'q' pour quitter: ${NC}"
    read -r choice
    
    case "$choice" in
        q|Q)
            log_color $YELLOW "Déploiement annulé par l'utilisateur"
            exit 0
            ;;
        a|A)
            printf "\n${YELLOW}Confirmation: Voulez-vous vraiment déployer TOUTES les stacks ? (y/N): ${NC}"
            read -r confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                deploy_all_stacks
                exit $?
            else
                log_color $YELLOW "Déploiement annulé"
                exit 0
            fi
            ;;
        *)
            # Vérifier si c'est un numéro valide
            if ! echo "$choice" | grep -q '^[0-9][0-9]*$'; then
                log_color $RED "Choix invalide. Veuillez entrer un numéro valide."
                exit 1
            fi
            
            # Rechercher le fichier correspondant
            selected_file=""
            selected_service=""
            
            # Parser la liste des fichiers
            old_IFS="$IFS"
            IFS='|'
            for item in $file_list; do
                IFS=':'
                set -- $item
                file_counter="$1"
                file_path="$2"
                service_name="$3"
                
                if [ "$file_counter" = "$choice" ]; then
                    selected_file="$file_path"
                    selected_service="$service_name"
                    break
                fi
            done
            IFS="$old_IFS"
            
            if [ -z "$selected_file" ]; then
                log_color $RED "Numéro de choix invalide: $choice"
                exit 1
            fi
            
            # Confirmation du déploiement
            printf "\n${YELLOW}Confirmation: Voulez-vous déployer la stack '$selected_service' ? (y/N): ${NC}"
            read -r confirm
            
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                printf "\n"
                if deploy_single_stack "$selected_file" "$selected_service"; then
                    log_color $GREEN "Déploiement terminé avec succès!"
                    exit 0
                else
                    log_color $RED "Le déploiement a échoué"
                    exit 1
                fi
            else
                log_color $YELLOW "Déploiement annulé"
                exit 0
            fi
            ;;
    esac
}

# Exécution du script principal
main "$@"
