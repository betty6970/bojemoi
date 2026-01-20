#!/bin/bash

# Script de test de l'installation de Deployment Orchestrator
# Usage: ./test-installation.sh

set -e

echo "🧪 Test de l'installation - Deployment Orchestrator"
echo "=================================================="
echo ""

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# URL de base
BASE_URL="http://localhost:8080"

# Fonction de test
test_endpoint() {
    local endpoint=$1
    local description=$2
    
    echo -n "Testing $description... "
    
    if curl -sf "$BASE_URL$endpoint" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        return 0
    else
        echo -e "${RED}✗${NC}"
        return 1
    fi
}

# Vérifier que Docker est en cours d'exécution
echo "1. Vérification de Docker..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker n'est pas en cours d'exécution${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker est actif${NC}"
echo ""

# Vérifier que les containers sont démarrés
echo "2. Vérification des containers..."
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✓ Les containers sont démarrés${NC}"
else
    echo -e "${YELLOW}⚠ Les containers ne semblent pas démarrés${NC}"
    echo "Démarrage des services..."
    docker-compose up -d
    echo "Attente de 10 secondes pour l'initialisation..."
    sleep 10
fi
echo ""

# Test des endpoints
echo "3. Test des endpoints API..."
test_endpoint "/" "Endpoint racine"
test_endpoint "/health" "Health check"
test_endpoint "/metrics" "Métriques Prometheus"
test_endpoint "/deployments" "Liste des déploiements"
echo ""

# Test de la base de données
echo "4. Test de la connexion PostgreSQL..."
if docker-compose exec -T postgres psql -U deployment_user -d deployments -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL est accessible${NC}"
else
    echo -e "${RED}✗ Impossible de se connecter à PostgreSQL${NC}"
fi
echo ""

# Vérifier les tables
echo "5. Vérification du schéma de base de données..."
if docker-compose exec -T postgres psql -U deployment_user -d deployments -c "\dt" | grep -q "deployments"; then
    echo -e "${GREEN}✓ Table 'deployments' existe${NC}"
else
    echo -e "${RED}✗ Table 'deployments' n'existe pas${NC}"
fi

if docker-compose exec -T postgres psql -U deployment_user -d deployments -c "\dt" | grep -q "deployment_logs"; then
    echo -e "${GREEN}✓ Table 'deployment_logs' existe${NC}"
else
    echo -e "${RED}✗ Table 'deployment_logs' n'existe pas${NC}"
fi
echo ""

# Test du webhook (optionnel)
echo "6. Test du webhook (simulation)..."
WEBHOOK_RESPONSE=$(curl -sf -X POST "$BASE_URL/webhook/gitea" \
    -H "Content-Type: application/json" \
    -d '{
        "ref": "refs/heads/main",
        "repository": {
            "name": "test-repo",
            "owner": {
                "username": "test-user"
            }
        },
        "commits": [
            {
                "id": "abc123def456",
                "message": "test commit"
            }
        ]
    }' 2>&1)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Webhook répond correctement${NC}"
else
    echo -e "${YELLOW}⚠ Webhook test échoué (normal si Gitea n'est pas configuré)${NC}"
fi
echo ""

# Afficher les logs récents
echo "7. Logs récents (dernières 20 lignes)..."
echo "=========================================="
docker-compose logs --tail=20 orchestrator
echo ""

# Résumé
echo "=========================================="
echo "✅ Tests d'installation terminés"
echo ""
echo "Services disponibles:"
echo "  - API:     http://localhost:8080"
echo "  - Health:  http://localhost:8080/health"
echo "  - Metrics: http://localhost:9090/metrics"
echo ""
echo "Commandes utiles:"
echo "  - Logs:           make logs"
echo "  - Shell:          make shell"
echo "  - DB Shell:       make db-shell"
echo "  - Deployments:    make deployments"
echo "  - Restart:        make restart"
echo ""
echo "Pour configurer Gitea, consultez le README.md"
echo "=========================================="
