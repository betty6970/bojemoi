#!/bin/sh

# Script de déploiement des stacks Docker Swarm
# Compatible Alpine Linux

set -e  # Arrêt du script en cas d'erreur

STACK_DIR="./stack"
LOG_FILE="deploy-stacks.log"

# Fonction de logging
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Fonction pour extraire le nom du service depuis le nom de fichier
extract_service_name() {
    local filename="$1"
    # Supprime l'extension .yml/.yaml et la partie numérotée
    echo "$filename" | sed -E 's/^[0-9]+-service-(.+)\.(yml|yaml)$/\1/'
}

# Vérification de l'existence du répertoire stack
if [ ! -d "$STACK_DIR" ]; then
    log "ERREUR: Le répertoire '$STACK_DIR' n'existe pas"
    exit 1
fi

# Vérification que Docker Swarm est initialisé
if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q "active"; then
    log "ERREUR: Docker Swarm n'est pas initialisé"
    log "Exécutez 'docker swarm init' avant de lancer ce script"
    exit 1
fi

log "Début du déploiement des stacks Docker Swarm"
log "Répertoire: $STACK_DIR"

# Compter les fichiers trouvés
file_count=0

# Recherche et tri des fichiers YAML de services
for file in "$STACK_DIR"/[0-9][0-9]-service-*.yml "$STACK_DIR"/[0-9][0-9]-service-*.yaml; do
    # Vérifier que le fichier existe (évite les patterns non matchés)
    [ -f "$file" ] || continue
    file_count=$((file_count + 1))
done

if [ $file_count -eq 0 ]; then
    log "ATTENTION: Aucun fichier de service trouvé dans $STACK_DIR"
    log "Format attendu: [00-99]-service-<nom>.[yml|yaml]"
    exit 0
fi

log "Nombre de stacks à déployer: $file_count"

# Déploiement des stacks dans l'ordre
deployed_count=0
failed_count=0

for file in "$STACK_DIR"/[0-9][0-9]-service-*.yml "$STACK_DIR"/[0-9][0-9]-service-*.yaml; do
    # Vérifier que le fichier existe
    [ -f "$file" ] || continue
    
    # Extraire le nom du fichier sans le chemin
    filename=$(basename "$file")
    
    # Extraire le nom du service
    service_name=$(extract_service_name "$filename")
    
    if [ -z "$service_name" ]; then
        log "ERREUR: Impossible d'extraire le nom du service depuis '$filename'"
        failed_count=$((failed_count + 1))
        continue
    fi
    
    log "Déploiement de la stack '$service_name' depuis '$filename'"
    
    # Déployer la stack
    if docker stack deploy -c "$file" "$service_name"; then
        log "SUCCESS: Stack '$service_name' déployée avec succès"
        deployed_count=$((deployed_count + 1))
        
        # Petite pause entre les déploiements pour éviter la surcharge
        sleep 10
    else
        log "ERREUR: Échec du déploiement de la stack '$service_name'"
        failed_count=$((failed_count + 1))
    fi
    
    echo ""  # Ligne vide pour la lisibilité
done

# Résumé final
log "=== RÉSUMÉ DU DÉPLOIEMENT ==="
log "Stacks déployées avec succès: $deployed_count"
log "Stacks en échec: $failed_count"
log "Total traité: $((deployed_count + failed_count))"

# Affichage de l'état des stacks
if [ $deployed_count -gt 0 ]; then
    log ""
    log "État actuel des stacks:"
    docker stack ls
fi

# Code de sortie
if [ $failed_count -gt 0 ]; then
    log "ATTENTION: Certains déploiements ont échoué. Consultez les logs ci-dessus."
    exit 1
else
    log "Tous les déploiements se sont terminés avec succès!"
    exit 0
fi
