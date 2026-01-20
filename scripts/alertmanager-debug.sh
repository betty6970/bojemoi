#!/bin/bash
# Script de diagnostic pour AlertManager Gateway Timeout
# bojemoi.lab.local

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Diagnostic AlertManager Gateway Timeout      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

# 1. Vérifier l'état du service
echo -e "${YELLOW}[1/10] État du service AlertManager${NC}"
docker service ps base_alertmanager --no-trunc
echo ""

# 2. Vérifier si le conteneur tourne
echo -e "${YELLOW}[2/10] Tâches en cours${NC}"
RUNNING=$(docker service ps base_alertmanager --filter "desired-state=running" -q | wc -l)
if [ "$RUNNING" -eq 0 ]; then
    echo -e "${RED}✗ Aucune tâche en cours d'exécution !${NC}"
    echo "Le service ne démarre pas correctement."
else
    echo -e "${GREEN}✓ $RUNNING tâche(s) en cours${NC}"
fi
echo ""

# 3. Logs du service
echo -e "${YELLOW}[3/10] Derniers logs AlertManager (20 lignes)${NC}"
docker service logs --tail 20 base_alertmanager 2>&1 | tail -20
echo ""

# 4. Vérifier la configuration du service
echo -e "${YELLOW}[4/10] Labels Traefik configurés${NC}"
docker service inspect base_alertmanager --format '{{json .Spec.Labels}}' | jq -r 'to_entries[] | select(.key | startswith("traefik")) | "\(.key)=\(.value)"'
echo ""

# 5. Vérifier les réseaux
echo -e "${YELLOW}[5/10] Réseaux du service${NC}"
docker service inspect base_alertmanager --format '{{json .Spec.TaskTemplate.Networks}}' | jq
echo ""

# 6. Vérifier si le port est exposé
echo -e "${YELLOW}[6/10] Ports exposés${NC}"
docker service inspect base_alertmanager --format '{{json .Spec.EndpointSpec.Ports}}' | jq
echo ""

# 7. Test de connectivité depuis Traefik
echo -e "${YELLOW}[7/10] Test de connectivité depuis Traefik${NC}"
TRAEFIK_CONTAINER=$(docker ps -q -f name=base_traefik | head -1)
if [ -n "$TRAEFIK_CONTAINER" ]; then
    echo "Test wget depuis Traefik vers AlertManager..."
    docker exec $TRAEFIK_CONTAINER wget -qO- --timeout=5 http://base_alertmanager:9093/-/healthy 2>&1 || echo -e "${RED}✗ Échec de connexion${NC}"
else
    echo -e "${RED}✗ Conteneur Traefik non trouvé${NC}"
fi
echo ""

# 8. Vérifier le healthcheck
echo -e "${YELLOW}[8/10] État de santé du conteneur${NC}"
ALERTMANAGER_CONTAINER=$(docker ps -q -f name=base_alertmanager | head -1)
if [ -n "$ALERTMANAGER_CONTAINER" ]; then
    docker inspect $ALERTMANAGER_CONTAINER --format '{{.State.Health.Status}}' 2>/dev/null || echo "Pas de healthcheck configuré"
    echo ""
    echo "Test direct du endpoint health:"
    docker exec $ALERTMANAGER_CONTAINER wget -qO- http://localhost:9093/-/healthy 2>&1 || echo -e "${RED}✗ AlertManager ne répond pas sur /-/healthy${NC}"
else
    echo -e "${RED}✗ Conteneur AlertManager non trouvé${NC}"
fi
echo ""

# 9. Vérifier la config AlertManager
echo -e "${YELLOW}[9/10] Vérification de la configuration${NC}"
if [ -n "$ALERTMANAGER_CONTAINER" ]; then
    echo "Fichier de config monté:"
    docker exec $ALERTMANAGER_CONTAINER ls -la /etc/alertmanager/ 2>&1 || echo "Impossible de lister les fichiers"
    echo ""
    echo "Validation de la config:"
    docker exec $ALERTMANAGER_CONTAINER cat /etc/alertmanager/alertmanager.yml 2>&1 | head -20 || echo -e "${RED}✗ Impossible de lire la config${NC}"
fi
echo ""

# 10. Vérifier Traefik
echo -e "${YELLOW}[10/10] Routes Traefik pour AlertManager${NC}"
if [ -n "$TRAEFIK_CONTAINER" ]; then
    echo "Recherche des routes configurées..."
    docker exec $TRAEFIK_CONTAINER wget -qO- http://localhost:8080/api/http/routers 2>/dev/null | jq -r '.[] | select(.name | contains("alertmanager")) | {name: .name, rule: .rule, service: .service, status: .status}' 2>/dev/null || echo "Impossible de récupérer les routes"
fi
echo ""

# Résumé et recommandations
echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              RECOMMANDATIONS                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$RUNNING" -eq 0 ]; then
    echo -e "${RED}⚠️  PROBLÈME CRITIQUE : Le service ne démarre pas${NC}"
    echo ""
    echo "Actions à effectuer:"
    echo "1. Vérifier les logs complets :"
    echo "   docker service logs base_alertmanager"
    echo ""
    echo "2. Vérifier que le fichier de config existe :"
    echo "   ls -la /opt/monitoring/alertmanager/alertmanager.yml"
    echo ""
    echo "3. Vérifier les volumes :"
    echo "   docker volume inspect alertmanager-data"
else
    echo -e "${YELLOW}Problèmes possibles :${NC}"
    echo ""
    echo "1. ${YELLOW}Timeout de démarrage${NC}"
    echo "   - AlertManager met trop de temps à démarrer"
    echo "   - Solution: Augmenter le timeout dans les labels Traefik"
    echo ""
    echo "2. ${YELLOW}Problème de réseau${NC}"
    echo "   - Traefik ne peut pas joindre AlertManager"
    echo "   - Vérifier que le label traefik.docker.network=traefik-public est présent"
    echo ""
    echo "3. ${YELLOW}Port incorrect${NC}"
    echo "   - Le port configuré ne correspond pas au port réel"
    echo "   - Vérifier le label traefik.http.services.alertmanager.loadbalancer.server.port"
    echo ""
    echo "4. ${YELLOW}Configuration AlertManager invalide${NC}"
    echo "   - Le fichier alertmanager.yml contient des erreurs"
    echo "   - Vérifier avec: amtool check-config alertmanager.yml"
fi

echo ""
echo -e "${GREEN}Commandes utiles :${NC}"
echo ""
echo "# Voir les logs en temps réel"
echo "docker service logs -f base_alertmanager"
echo ""
echo "# Redémarrer le service"
echo "docker service update --force base_alertmanager"
echo ""
echo "# Vérifier la config Traefik"
echo "docker service inspect base_traefik --format '{{json .Spec.Labels}}' | jq"
echo ""


