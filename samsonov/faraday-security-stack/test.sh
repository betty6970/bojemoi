#!/bin/bash
#
# Script de tests automatiques pour Faraday Security Stack
#

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Compteurs
TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

# Fonction de test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -n "Test $TESTS_TOTAL: $test_name... "
    
    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Header
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Tests automatiques - Faraday Security Stack        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Tests Docker
echo -e "${BLUE}[1] Tests Docker${NC}"
run_test "Docker est installé" "command -v docker"
run_test "Docker Compose est installé" "command -v docker-compose"
run_test "Docker daemon est actif" "docker info"
echo ""

# Tests des conteneurs
echo -e "${BLUE}[2] Tests des conteneurs${NC}"
run_test "Conteneur Faraday est actif" "docker ps | grep -q faraday-server"
run_test "Conteneur PostgreSQL est actif" "docker ps | grep -q faraday-postgres"
run_test "Conteneur ZAP est actif" "docker ps | grep -q faraday-zap"
run_test "Conteneur Metasploit est actif" "docker ps | grep -q faraday-metasploit"
run_test "Conteneur Masscan est actif" "docker ps | grep -q faraday-masscan"
run_test "Conteneur Nginx est actif" "docker ps | grep -q faraday-nginx"
echo ""

# Tests de connectivité
echo -e "${BLUE}[3] Tests de connectivité${NC}"
run_test "Faraday API est accessible" "curl -s -f http://localhost:5985"
run_test "ZAP est accessible" "curl -s -f http://localhost:8080"
run_test "Nginx est accessible" "curl -s -f http://localhost/status"
echo ""

# Tests PostgreSQL
echo -e "${BLUE}[4] Tests PostgreSQL${NC}"
run_test "PostgreSQL accepte les connexions" \
    "docker exec faraday-postgres pg_isready -U faraday"
run_test "Base de données Faraday existe" \
    "docker exec faraday-postgres psql -U faraday -lqt | cut -d \| -f 1 | grep -qw faraday"
echo ""

# Tests des scripts
echo -e "${BLUE}[5] Tests des scripts${NC}"
run_test "Script orchestrator.sh existe" "test -f scripts/orchestrator.sh"
run_test "Script orchestrator.sh est exécutable" "test -x scripts/orchestrator.sh"
run_test "Script zap_to_faraday.py existe" "test -f scripts/zap_to_faraday.py"
run_test "Script msf_to_faraday.py existe" "test -f scripts/msf_to_faraday.py"
run_test "Script masscan_to_faraday.py existe" "test -f scripts/masscan_to_faraday.py"
echo ""

# Tests des fichiers de configuration
echo -e "${BLUE}[6] Tests des fichiers de configuration${NC}"
run_test "docker-compose.yml existe" "test -f docker-compose.yml"
run_test ".env existe" "test -f .env"
run_test "Makefile existe" "test -f Makefile"
run_test "nginx.conf existe" "test -f configs/nginx/nginx.conf"
echo ""

# Tests de l'API Faraday
echo -e "${BLUE}[7] Tests de l'API Faraday${NC}"
run_test "API Faraday répond" \
    "curl -s http://localhost:5985/_api/v3/info | grep -q version"
echo ""

# Tests ZAP
echo -e "${BLUE}[8] Tests ZAP${NC}"
run_test "API ZAP répond" \
    "curl -s http://localhost:8080/JSON/core/view/version/"
echo ""

# Tests des volumes
echo -e "${BLUE}[9] Tests des volumes Docker${NC}"
run_test "Volume postgres_data existe" \
    "docker volume ls | grep -q postgres_data"
run_test "Volume faraday_data existe" \
    "docker volume ls | grep -q faraday_data"
run_test "Volume zap_data existe" \
    "docker volume ls | grep -q zap_data"
run_test "Volume metasploit_data existe" \
    "docker volume ls | grep -q metasploit_data"
echo ""

# Tests réseau
echo -e "${BLUE}[10] Tests réseau Docker${NC}"
run_test "Réseau faraday-network existe" \
    "docker network ls | grep -q faraday-network"
run_test "Faraday peut communiquer avec PostgreSQL" \
    "docker exec faraday-server ping -c 1 postgres > /dev/null 2>&1"
run_test "Faraday peut communiquer avec ZAP" \
    "docker exec faraday-server ping -c 1 zap > /dev/null 2>&1"
echo ""

# Test de performance
echo -e "${BLUE}[11] Tests de performance${NC}"
run_test "Utilisation mémoire < 4GB" \
    "test $(docker stats --no-stream --format '{{.MemUsage}}' | grep -oP '^\d+\.\d+' | awk '{s+=$1} END {print s}' | cut -d. -f1) -lt 4096"
echo ""

# Résumé
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Résumé des tests${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo "Total de tests:    $TESTS_TOTAL"
echo -e "Tests réussis:     ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests échoués:     ${RED}$TESTS_FAILED${NC}"
echo ""

# Code de sortie
if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ Tous les tests sont passés avec succès!${NC}"
    exit 0
else
    echo -e "${RED}✗ Certains tests ont échoué${NC}"
    echo ""
    echo -e "${YELLOW}Conseils de dépannage:${NC}"
    echo "  1. Vérifiez les logs: make logs"
    echo "  2. Vérifiez le statut des services: make status"
    echo "  3. Redémarrez les services: make restart"
    echo "  4. Consultez le README.md pour plus d'informations"
    exit 1
fi
