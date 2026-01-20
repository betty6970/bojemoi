#!/bin/bash

# Script pour régénérer un docker-compose.yml à partir d'une stack Docker Swarm
# Usage: ./swarm-stack-export.sh <stack_name> [output_file]

set -e

STACK_NAME=$1
OUTPUT_FILE=${2:-"${STACK_NAME}-reconstructed.yml"}

if [ -z "$STACK_NAME" ]; then
    echo "Usage: $0 <stack_name> [output_file]"
    echo ""
    echo "Stacks disponibles:"
    docker stack ls --format "  - {{.Name}}"
    exit 1
fi

# Vérifier que la stack existe
if ! docker stack ls --format "{{.Name}}" | grep -q "^${STACK_NAME}$"; then
    echo "❌ Erreur: La stack '$STACK_NAME' n'existe pas"
    echo ""
    echo "Stacks disponibles:"
    docker stack ls --format "  - {{.Name}}"
    exit 1
fi

echo "� Extraction de la configuration de la stack: $STACK_NAME"
echo ""

# Récupérer la liste des services de la stack
SERVICES=$(docker stack services $STACK_NAME --format "{{.Name}}")

if [ -z "$SERVICES" ]; then
    echo "❌ Aucun service trouvé dans la stack $STACK_NAME"
    exit 1
fi

# Début du fichier YAML
cat > "$OUTPUT_FILE" << 'EOF'
# Fichier régénéré automatiquement à partir de la stack déployée
# Date: $(date)
# Stack: $STACK_NAME

version: '3.8'

services:
EOF

# Pour chaque service
for SERVICE in $SERVICES; do
    echo "  � Traitement du service: $SERVICE"
    
    # Nom du service (sans le préfixe stack_)
    SERVICE_NAME=${SERVICE#${STACK_NAME}_}
    
    # Récupérer toutes les infos du service
    SERVICE_JSON=$(docker service inspect $SERVICE --format '{{json .}}')
    
    # Écrire le nom du service
    echo "" >> "$OUTPUT_FILE"
    echo "  ${SERVICE_NAME}:" >> "$OUTPUT_FILE"
    
    # Image
    IMAGE=$(echo "$SERVICE_JSON" | jq -r '.Spec.TaskTemplate.ContainerSpec.Image' | cut -d'@' -f1)
    echo "    image: $IMAGE" >> "$OUTPUT_FILE"
    
    # Hostname
    HOSTNAME=$(echo "$SERVICE_JSON" | jq -r '.Spec.TaskTemplate.ContainerSpec.Hostname // empty')
    if [ -n "$HOSTNAME" ]; then
        echo "    hostname: $HOSTNAME" >> "$OUTPUT_FILE"
    fi
    
    # Environment variables
    ENV_VARS=$(echo "$SERVICE_JSON" | jq -r '.Spec.TaskTemplate.ContainerSpec.Env[]? // empty')
    if [ -n "$ENV_VARS" ]; then
        echo "    environment:" >> "$OUTPUT_FILE"
        echo "$ENV_VARS" | while read -r ENV; do
            echo "      - $ENV" >> "$OUTPUT_FILE"
        done
    fi
    
    # Command
    COMMAND=$(echo "$SERVICE_JSON" | jq -r '.Spec.TaskTemplate.ContainerSpec.Command[]? // empty' | tr '\n' ' ')
    if [ -n "$COMMAND" ]; then
        echo "    command: [$COMMAND]" >> "$OUTPUT_FILE"
    fi
    
    # Volumes/Mounts
    MOUNTS=$(echo "$SERVICE_JSON" | jq -c '.Spec.TaskTemplate.ContainerSpec.Mounts[]? // empty')
    if [ -n "$MOUNTS" ]; then
        echo "    volumes:" >> "$OUTPUT_FILE"
        echo "$MOUNTS" | while read -r MOUNT; do
            TYPE=$(echo "$MOUNT" | jq -r '.Type')
            SOURCE=$(echo "$MOUNT" | jq -r '.Source')
            TARGET=$(echo "$MOUNT" | jq -r '.Target')
            READONLY=$(echo "$MOUNT" | jq -r '.ReadOnly // false')
            
            if [ "$TYPE" = "bind" ]; then
                if [ "$READONLY" = "true" ]; then
                    echo "      - ${SOURCE}:${TARGET}:ro" >> "$OUTPUT_FILE"
                else
                    echo "      - ${SOURCE}:${TARGET}" >> "$OUTPUT_FILE"
                fi
            elif [ "$TYPE" = "volume" ]; then
                if [ "$READONLY" = "true" ]; then
                    echo "      - ${SOURCE}:${TARGET}:ro" >> "$OUTPUT_FILE"
                else
                    echo "      - ${SOURCE}:${TARGET}" >> "$OUTPUT_FILE"
                fi
            fi
        done
    fi
    
    # Networks
    NETWORKS=$(echo "$SERVICE_JSON" | jq -r '.Spec.TaskTemplate.Networks[]?.Target // empty')
    if [ -n "$NETWORKS" ]; then
        echo "    networks:" >> "$OUTPUT_FILE"
        echo "$NETWORKS" | while read -r NET_ID; do
            # Récupérer le nom du réseau
            NET_NAME=$(docker network inspect $NET_ID --format '{{.Name}}' 2>/dev/null || echo "$NET_ID")
            # Enlever le préfixe stack_ si présent
            NET_NAME=${NET_NAME#${STACK_NAME}_}
            echo "      - $NET_NAME" >> "$OUTPUT_FILE"
        done
    fi
    
    # Ports
    PORTS=$(echo "$SERVICE_JSON" | jq -c '.Spec.EndpointSpec.Ports[]? // empty')
    if [ -n "$PORTS" ]; then
        echo "    ports:" >> "$OUTPUT_FILE"
        echo "$PORTS" | while read -r PORT; do
            PUBLISHED=$(echo "$PORT" | jq -r '.PublishedPort')
            TARGET=$(echo "$PORT" | jq -r '.TargetPort')
            PROTOCOL=$(echo "$PORT" | jq -r '.Protocol')
            MODE=$(echo "$PORT" | jq -r '.PublishMode // "ingress"')
            
            if [ "$MODE" = "host" ]; then
                echo "      - target: $TARGET" >> "$OUTPUT_FILE"
                echo "        published: $PUBLISHED" >> "$OUTPUT_FILE"
                echo "        protocol: $PROTOCOL" >> "$OUTPUT_FILE"
                echo "        mode: host" >> "$OUTPUT_FILE"
            else
                echo "      - ${PUBLISHED}:${TARGET}/${PROTOCOL}" >> "$OUTPUT_FILE"
            fi
        done
    fi
    
    # Deploy section
    echo "    deploy:" >> "$OUTPUT_FILE"
    
    # Replicas
    REPLICAS=$(echo "$SERVICE_JSON" | jq -r '.Spec.Mode.Replicated.Replicas // 1')
    echo "      replicas: $REPLICAS" >> "$OUTPUT_FILE"
    
    # Placement constraints
    CONSTRAINTS=$(echo "$SERVICE_JSON" | jq -r '.Spec.TaskTemplate.Placement.Constraints[]? // empty')
    if [ -n "$CONSTRAINTS" ]; then
        echo "      placement:" >> "$OUTPUT_FILE"
        echo "        constraints:" >> "$OUTPUT_FILE"
        echo "$CONSTRAINTS" | while read -r CONSTRAINT; do
            echo "          - $CONSTRAINT" >> "$OUTPUT_FILE"
        done
    fi
    
    # Resources
    LIMITS_CPU=$(echo "$SERVICE_JSON" | jq -r '.Spec.TaskTemplate.Resources.Limits.NanoCPUs // empty')
    LIMITS_MEM=$(echo "$SERVICE_JSON" | jq -r '.Spec.TaskTemplate.Resources.Limits.MemoryBytes // empty')
    RESERV_CPU=$(echo "$SERVICE_JSON" | jq -r '.Spec.TaskTemplate.Resources.Reservations.NanoCPUs // empty')
    RESERV_MEM=$(echo "$SERVICE_JSON" | jq -r '.Spec.TaskTemplate.Resources.Reservations.MemoryBytes // empty')
    
    if [ -n "$LIMITS_CPU" ] || [ -n "$LIMITS_MEM" ] || [ -n "$RESERV_CPU" ] || [ -n "$RESERV_MEM" ]; then
        echo "      resources:" >> "$OUTPUT_FILE"
        
        if [ -n "$LIMITS_CPU" ] || [ -n "$LIMITS_MEM" ]; then
            echo "        limits:" >> "$OUTPUT_FILE"
            if [ -n "$LIMITS_CPU" ]; then
                CPU_LIMIT=$(echo "scale=2; $LIMITS_CPU / 1000000000" | bc)
                echo "          cpus: '$CPU_LIMIT'" >> "$OUTPUT_FILE"
            fi
            if [ -n "$LIMITS_MEM" ]; then
                MEM_LIMIT=$(echo "scale=0; $LIMITS_MEM / 1048576" | bc)
                echo "          memory: ${MEM_LIMIT}M" >> "$OUTPUT_FILE"
            fi
        fi
        
        if [ -n "$RESERV_CPU" ] || [ -n "$RESERV_MEM" ]; then
            echo "        reservations:" >> "$OUTPUT_FILE"
            if [ -n "$RESERV_CPU" ]; then
                CPU_RESERV=$(echo "scale=2; $RESERV_CPU / 1000000000" | bc)
                echo "          cpus: '$CPU_RESERV'" >> "$OUTPUT_FILE"
            fi
            if [ -n "$RESERV_MEM" ]; then
                MEM_RESERV=$(echo "scale=0; $RESERV_MEM / 1048576" | bc)
                echo "          memory: ${MEM_RESERV}M" >> "$OUTPUT_FILE"
            fi
        fi
    fi
    
    # Restart policy
    RESTART_CONDITION=$(echo "$SERVICE_JSON" | jq -r '.Spec.TaskTemplate.RestartPolicy.Condition // "any"')
    if [ "$RESTART_CONDITION" != "any" ]; then
        echo "      restart_policy:" >> "$OUTPUT_FILE"
        echo "        condition: $RESTART_CONDITION" >> "$OUTPUT_FILE"
    fi
    
    # Labels
    LABELS=$(echo "$SERVICE_JSON" | jq -r '.Spec.Labels // empty | to_entries[] | "\(.key)=\(.value)"')
    if [ -n "$LABELS" ]; then
        echo "      labels:" >> "$OUTPUT_FILE"
        echo "$LABELS" | while read -r LABEL; do
            echo "        - $LABEL" >> "$OUTPUT_FILE"
        done
    fi
    
done

# Récupérer les networks
echo "" >> "$OUTPUT_FILE"
echo "networks:" >> "$OUTPUT_FILE"

STACK_NETWORKS=$(docker network ls --filter "label=com.docker.stack.namespace=$STACK_NAME" --format "{{.Name}}")
for NET in $STACK_NETWORKS; do
    NET_NAME=${NET#${STACK_NAME}_}
    NET_JSON=$(docker network inspect $NET --format '{{json .}}')
    DRIVER=$(echo "$NET_JSON" | jq -r '.Driver')
    ATTACHABLE=$(echo "$NET_JSON" | jq -r '.Attachable')
    
    echo "  ${NET_NAME}:" >> "$OUTPUT_FILE"
    if [ "$DRIVER" != "overlay" ]; then
        echo "    driver: $DRIVER" >> "$OUTPUT_FILE"
    fi
    if [ "$ATTACHABLE" = "true" ]; then
        echo "    attachable: true" >> "$OUTPUT_FILE"
    fi
done

# Récupérer les volumes
STACK_VOLUMES=$(docker volume ls --filter "label=com.docker.stack.namespace=$STACK_NAME" --format "{{.Name}}")
if [ -n "$STACK_VOLUMES" ]; then
    echo "" >> "$OUTPUT_FILE"
    echo "volumes:" >> "$OUTPUT_FILE"
    for VOL in $STACK_VOLUMES; do
        VOL_NAME=${VOL#${STACK_NAME}_}
        echo "  ${VOL_NAME}:" >> "$OUTPUT_FILE"
    done
fi

echo ""
echo "✅ Configuration exportée vers: $OUTPUT_FILE"
echo ""
echo "⚠️  Note: Vérifie le fichier généré, certains éléments peuvent nécessiter des ajustements:"
echo "   - Secrets et configs ne sont pas exportés (à recréer manuellement)"
echo "   - Variables d'environnement sensibles peuvent être visibles"
echo "   - Les labels Traefik et autres configurations spécifiques sont inclus"
echo ""
echo "� Pour redéployer: docker stack deploy -c $OUTPUT_FILE $STACK_NAME"


