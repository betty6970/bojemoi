#!/bin/bash
#
# Exemples d'utilisation de Faraday Security Stack
#

set -e

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Exemples d'utilisation - Faraday Security Stack      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Exemple 1: Scan réseau complet
echo -e "${GREEN}[1] Scan réseau complet${NC}"
echo "Scanne un réseau entier avec tous les outils"
echo ""
cat << 'EOF'
make scan TARGET=192.168.1.0/24 WORKSPACE=network-audit

# Ou manuellement:
docker exec faraday-masscan /scripts/orchestrator.sh \
  --target 192.168.1.0/24 \
  --workspace network-audit \
  --all
EOF
echo ""
echo "───────────────────────────────────────────────────────"
echo ""

# Exemple 2: Scan web ciblé
echo -e "${GREEN}[2] Scan d'application web${NC}"
echo "Analyse une application web avec ZAP"
echo ""
cat << 'EOF'
make scan-zap TARGET=http://example.com WORKSPACE=webapp-test

# Ou avec script Python:
docker exec faraday-server python3 /scripts/zap_to_faraday.py \
  --faraday-url http://faraday:5985 \
  --faraday-user faraday \
  --faraday-pass changeme \
  --zap-url http://zap:8080 \
  --workspace webapp-test \
  --target-url http://example.com
EOF
echo ""
echo "───────────────────────────────────────────────────────"
echo ""

# Exemple 3: Scan de ports rapide
echo -e "${GREEN}[3] Scan de ports avec Masscan${NC}"
echo "Scan ultra-rapide des ports d'un réseau"
echo ""
cat << 'EOF'
# Scan rapide (rate 10000)
make scan-masscan TARGET=10.0.0.0/24 WORKSPACE=portscan

# Scan personnalisé dans le conteneur Masscan
docker exec -it faraday-masscan sh
masscan 192.168.1.0/24 -p1-65535 --rate=50000 -oJ /results/scan.json

# Import dans Faraday
docker exec faraday-server python3 /scripts/masscan_to_faraday.py \
  --masscan-json /results/scan.json \
  --workspace portscan
EOF
echo ""
echo "───────────────────────────────────────────────────────"
echo ""

# Exemple 4: Exploitation avec Metasploit
echo -e "${GREEN}[4] Tests de pénétration avec Metasploit${NC}"
echo "Utilisation de Metasploit Framework"
echo ""
cat << 'EOF'
# Accéder à msfconsole
make shell-metasploit

# Dans msfconsole:
use auxiliary/scanner/portscan/tcp
set RHOSTS 192.168.1.0/24
set PORTS 1-1000
run

# Exporter les résultats
db_export -f xml /tmp/msf_results.xml

# Import dans Faraday (depuis l'hôte)
docker exec faraday-server python3 /scripts/msf_to_faraday.py \
  --msf-xml /tmp/msf_results.xml \
  --workspace pentest
EOF
echo ""
echo "───────────────────────────────────────────────────────"
echo ""

# Exemple 5: Workflow complet de reconnaissance
echo -e "${GREEN}[5] Workflow de reconnaissance complet${NC}"
echo "Processus complet de reconnaissance et d'analyse"
echo ""
cat << 'EOF'
#!/bin/bash
TARGET="192.168.1.0/24"
WORKSPACE="recon-$(date +%Y%m%d)"

# 1. Découverte réseau avec Masscan
echo "[*] Phase 1: Découverte réseau"
make scan-masscan TARGET=$TARGET WORKSPACE=$WORKSPACE

# 2. Énumération détaillée avec Metasploit
echo "[*] Phase 2: Énumération des services"
docker exec faraday-metasploit msfconsole << MSF
db_nmap -sV -sC -A $TARGET
db_export -f xml /tmp/enum_results.xml
exit
MSF

docker exec faraday-server python3 /scripts/msf_to_faraday.py \
  --msf-xml /tmp/enum_results.xml \
  --workspace $WORKSPACE

# 3. Scan web des services HTTP découverts
echo "[*] Phase 3: Scan des applications web"
# (Automatiquement sur les services web découverts)
for host in $(docker exec faraday-server faraday-client \
  --workspace $WORKSPACE list-hosts | grep -oP '\d+\.\d+\.\d+\.\d+'); do
  make scan-zap TARGET=http://$host WORKSPACE=$WORKSPACE
done

echo "[+] Reconnaissance terminée!"
echo "[+] Consultez les résultats dans Faraday: http://localhost:5985"
EOF
echo ""
echo "───────────────────────────────────────────────────────"
echo ""

# Exemple 6: Scan avec Burp Suite
echo -e "${GREEN}[6] Analyse manuelle avec Burp Suite${NC}"
echo "Configuration et utilisation de Burp Suite"
echo ""
cat << 'EOF'
# 1. Accéder à Burp Suite
open http://localhost:8081

# 2. Configurer votre navigateur avec le proxy:
#    - Proxy: localhost
#    - Port: 8081

# 3. Naviguer sur l'application cible
#    Burp interceptera automatiquement le trafic

# 4. Exporter les résultats
#    Dans Burp: Target > Site map > Right-click > Export

# 5. Import manuel dans Faraday
#    (Burp n'a pas de script d'import automatique)
EOF
echo ""
echo "───────────────────────────────────────────────────────"
echo ""

# Exemple 7: Gestion des workspaces
echo -e "${GREEN}[7] Gestion des workspaces Faraday${NC}"
echo "Créer et gérer les workspaces"
echo ""
cat << 'EOF'
# Via l'interface web (recommandé)
open http://localhost:5985

# Via l'API REST
curl -X POST http://localhost:5985/_api/v3/ws \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-project",
    "description": "Description du projet",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }'

# Lister les workspaces
curl http://localhost:5985/_api/v3/ws
EOF
echo ""
echo "───────────────────────────────────────────────────────"
echo ""

# Exemple 8: Sauvegarde et restauration
echo -e "${GREEN}[8] Sauvegarde et restauration${NC}"
echo "Sauvegarder et restaurer les données"
echo ""
cat << 'EOF'
# Sauvegarde automatique
make backup

# Sauvegarde manuelle
docker exec faraday-postgres pg_dump -U faraday faraday > \
  backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Restauration
make restore BACKUP_FILE=backups/backup_20240101_120000.sql

# Sauvegarde avec compression
docker exec faraday-postgres pg_dump -U faraday faraday | \
  gzip > backups/backup_$(date +%Y%m%d).sql.gz

# Restauration depuis archive compressée
gunzip -c backups/backup_20240101.sql.gz | \
  docker exec -i faraday-postgres psql -U faraday faraday
EOF
echo ""
echo "───────────────────────────────────────────────────────"
echo ""

# Exemple 9: Monitoring et logs
echo -e "${GREEN}[9] Monitoring et logs${NC}"
echo "Surveiller l'activité des services"
echo ""
cat << 'EOF'
# Logs en temps réel de tous les services
make logs

# Logs d'un service spécifique
make logs-faraday
make logs-zap
docker-compose logs -f metasploit

# Statut des services
make status

# Statistiques Docker
docker stats faraday-server faraday-zap faraday-metasploit

# Espace disque utilisé
docker system df
EOF
echo ""
echo "───────────────────────────────────────────────────────"
echo ""

# Exemple 10: Nettoyage et maintenance
echo -e "${GREEN}[10] Nettoyage et maintenance${NC}"
echo "Maintenance régulière du système"
echo ""
cat << 'EOF'
# Nettoyage des résultats temporaires
rm -rf results/*.json results/*.xml

# Nettoyage des volumes Docker (ATTENTION!)
make clean

# Mise à jour des images
make update

# Nettoyage complet Docker
make prune

# Redémarrage propre
make restart

# Reconstruire après modifications
docker-compose down
docker-compose build --no-cache
docker-compose up -d
EOF
echo ""
echo "───────────────────────────────────────────────────────"
echo ""

# Footer
echo -e "${YELLOW}💡 Conseils:${NC}"
echo "  - Toujours sauvegarder avant les opérations critiques"
echo "  - Utilisez des workspaces séparés pour chaque projet"
echo "  - Consultez les logs en cas de problème"
echo "  - Changez les mots de passe par défaut en production"
echo "  - N'utilisez ces outils que sur des systèmes autorisés"
echo ""
echo -e "${BLUE}Pour plus d'informations, consultez le README.md${NC}"
