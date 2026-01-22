#!/bin/bash
set -euo pipefail

STACK_NAME=$1
COMPOSE_FILE=$2
TIMEOUT=300
CHECK_INTERVAL=5

echo "🚀 Déploiement de la stack ${STACK_NAME}"
echo "📄 Fichier: ${COMPOSE_FILE}"
echo "⏰ $(date)"

# Vérification préalable
echo ""
echo "🔍 Vérification de la configuration..."
if ! docker-compose -f ${COMPOSE_FILE} config > /dev/null 2>&1; then
    echo "❌ Configuration invalide"
    exit 1
fi

# Backup de l'état actuel
echo ""
echo "💾 Sauvegarde de l'état actuel..."
if docker stack ls | grep -q "^${STACK_NAME} "; then
    docker stack ps ${STACK_NAME} --no-trunc > "/tmp/${STACK_NAME}_backup_$(date +%Y%m%d_%H%M%S).txt"
    PREVIOUS_VERSION=$(docker service inspect ${STACK_NAME}_app --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}' 2>/dev/null || echo "none")
    echo "Version précédente: ${PREVIOUS_VERSION}"
fi

# Déploiement
echo ""
echo "🔧 Déploiement en cours..."
docker stack deploy \
    -c ${COMPOSE_FILE} \
    --prune \
    --with-registry-auth \
    ${STACK_NAME}

# Attente du démarrage
echo ""
echo "⏳ Attente du démarrage des services..."
elapsed=0
while [ $elapsed -lt $TIMEOUT ]; do
    sleep $CHECK_INTERVAL
    elapsed=$((elapsed + CHECK_INTERVAL))
    
    # Récupérer l'état des services
    services=$(docker stack services ${STACK_NAME} --format "{{.Name}}\t{{.Replicas}}")
    all_running=true
    
    echo "État à T+${elapsed}s:"
    while IFS=$'\t' read -r name replicas; do
        current=$(echo $replicas | cut -d'/' -f1)
        desired=$(echo $replicas | cut -d'/' -f2)
        echo "  - $name: $current/$desired"
        
        if [ "$current" != "$desired" ]; then
            all_running=false
        fi
    done <<< "$services"
    
    if [ "$all_running" = true ]; then
        echo ""
        echo "✅ Tous les services sont démarrés"
        break
    fi
    
    if [ $elapsed -ge $TIMEOUT ]; then
        echo ""
        echo "❌ Timeout: Les services n'ont pas démarré dans les temps"
        echo ""
        echo "📋 Logs des services en erreur:"
        docker stack ps ${STACK_NAME} --no-trunc --filter "desired-state=running" --format "table {{.Name}}\t{{.CurrentState}}\t{{.Error}}"
        exit 1
    fi
done

# Vérification finale
echo ""
echo "🔍 Vérification finale..."
docker stack services ${STACK_NAME}

echo ""
echo "📊 État détaillé des tâches:"
docker stack ps ${STACK_NAME} --no-trunc

# Health checks
echo ""
echo "💚 Exécution des health checks..."
sleep 10  # Attendre que les health checks soient opérationnels

healthy=true
for service in $(docker stack services ${STACK_NAME} --format "{{.Name}}"); do
    replicas=$(docker service ps $service --filter "desired-state=running" -q | wc -l)
    if [ $replicas -eq 0 ]; then
        echo "⚠️  $service: Aucune réplica en cours"
        healthy=false
    fi
done

if [ "$healthy" = false ]; then
    echo ""
    echo "⚠️  Certains services ont des problèmes"
    exit 1
fi

echo ""
echo "✅ Déploiement de ${STACK_NAME} terminé avec succès"
echo "⏰ $(date)"

