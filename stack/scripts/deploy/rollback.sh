#!/bin/bash
set -euo pipefail

STACK_NAME=$1

echo "🔄 Rollback de la stack ${STACK_NAME}"

# Récupérer la version précédente
PREVIOUS_VERSION=$(docker service inspect ${STACK_NAME}_app --format '{{index .PreviousSpec.TaskTemplate.ContainerSpec.Image}}' 2>/dev/null || echo "")

if [ -z "$PREVIOUS_VERSION" ]; then
    echo "❌ Impossible de trouver la version précédente"
    exit 1
fi

echo "📦 Rollback vers: ${PREVIOUS_VERSION}"

# Rollback de chaque service
for service in $(docker stack services ${STACK_NAME} --format "{{.Name}}"); do
    echo "  Rollback de $service..."
    docker service rollback $service
done

echo "✅ Rollback terminé"

