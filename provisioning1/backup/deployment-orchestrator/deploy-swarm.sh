#!/bin/bash

# Script de déploiement pour Docker Swarm
# Usage: ./deploy-swarm.sh

set -e

echo "🐳 Déploiement Orchestrator sur Docker Swarm"
echo "=============================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Vérifier que nous sommes sur un Swarm manager
if ! docker info 2>/dev/null | grep -q "Swarm: active"; then
    echo -e "${RED}❌ Erreur: Ce node n'est pas dans un Swarm actif${NC}"
    echo "Initialisez Swarm avec: docker swarm init"
    exit 1
fi

if ! docker node ls &>/dev/null; then
    echo -e "${RED}❌ Erreur: Vous devez être sur un manager node${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Swarm actif et node manager détecté${NC}"
echo ""

# Vérifier le fichier .env
if [ ! -f .env ]; then
    echo -e "${RED}❌ Fichier .env manquant${NC}"
    echo "Copiez .env.example vers .env et configurez-le"
    exit 1
fi

echo -e "${GREEN}✓ Fichier .env trouvé${NC}"
echo ""

# Créer le réseau si nécessaire
echo "📡 Vérification du réseau bojemoi_network..."
if ! docker network ls | grep -q bojemoi_network; then
    echo "Création du réseau overlay bojemoi_network..."
    docker network create \
        --driver overlay \
        --attachable \
        bojemoi_network
    echo -e "${GREEN}✓ Réseau créé${NC}"
else
    echo -e "${GREEN}✓ Réseau existe déjà${NC}"
fi
echo ""

# Label du node pour PostgreSQL
echo "🏷️  Configuration des labels de node..."
CURRENT_NODE=$(docker node ls --filter "role=manager" --format "{{.Hostname}}" | head -n 1)
echo "Label du node $CURRENT_NODE pour PostgreSQL..."
docker node update --label-add postgres=true $CURRENT_NODE
echo -e "${GREEN}✓ Labels configurés${NC}"
echo ""

# Build de l'image (optionnel, commentez si vous utilisez une registry)
echo "🔨 Build de l'image Docker..."
read -p "Voulez-vous builder l'image localement? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker build -t registry.bojemoi.lab/deployment-orchestrator:latest .
    echo -e "${GREEN}✓ Image buildée${NC}"
    
    read -p "Voulez-vous push l'image vers la registry? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker push registry.bojemoi.lab/deployment-orchestrator:latest
        echo -e "${GREEN}✓ Image poussée vers la registry${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Assurez-vous que l'image existe dans votre registry${NC}"
fi
echo ""

# Déployer le stack
echo "🚀 Déploiement du stack deployment-orchestrator..."
docker stack deploy \
    --compose-file docker-compose.swarm.yml \
    --with-registry-auth \
    deployment-orchestrator

echo ""
echo -e "${GREEN}✓ Stack déployé!${NC}"
echo ""

# Attendre que les services soient prêts
echo "⏳ Attente du démarrage des services..."
sleep 5

# Afficher l'état
echo ""
echo "📊 État des services:"
docker stack services deployment-orchestrator

echo ""
echo "📋 Tâches en cours:"
docker stack ps deployment-orchestrator --no-trunc

echo ""
echo "=============================================="
echo -e "${GREEN}✅ Déploiement terminé!${NC}"
echo ""
echo "Services disponibles:"
echo "  - API:     http://<manager-ip>:8080"
echo "  - Health:  http://<manager-ip>:8080/health"
echo "  - Metrics: http://<manager-ip>:9090/metrics"
echo ""
echo "Commandes utiles:"
echo "  - Logs orchestrator: docker service logs -f deployment-orchestrator_orchestrator"
echo "  - Logs postgres:     docker service logs -f deployment-orchestrator_postgres"
echo "  - Mise à jour:       docker service update deployment-orchestrator_orchestrator --image ..."
echo "  - Supprimer stack:   docker stack rm deployment-orchestrator"
echo "=============================================="
