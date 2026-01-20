#!/bin/bash
# Scripts de gestion pour le scanner VPN unifié

# =====================================
# Script: setup-unified-scanner.sh
# =====================================
cat > setup-unified-scanner.sh << 'EOF'
#!/bin/bash
set -e

# Configuration
PROJECT_NAME="vpn-scanner"
VERSION="2.0"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_debug() { echo -e "${BLUE}[DEBUG]${NC} $1"; }

# Fonction de création de la structure
create_directory_structure() {
    log_info "🏗️  Création de la structure de répertoires..."
    
    # Répertoires principaux
    mkdir -p {config,certs,logs,results,data,monitoring,sql,scripts}
    
    # Sous-répertoires logs
    mkdir -p logs/{app,vpn,masscan,msf,system}
    
    # Sous-répertoires data
    mkdir -p data/{ip2location,msf}
    
    # Sous-répertoires monitoring
    mkdir -p monitoring/{prometheus,grafana/{provisioning/{dashboards,datasources},dashboards}}
    
    # Permissions
    chmod 755 config certs logs results data monitoring sql scripts
    chmod 755 logs/{app,vpn,masscan,msf,system}
    chmod 755 data/{ip2location,msf}
    
    log_info "✅ Structure créée"
}

# Configuration des fichiers par défaut
create_default_configs() {
    log_info "📝 Création des configurations par défaut..."
    
    # Fichier .env principal
    cat > .env << 'ENVFILE'
# Configuration Scanner VPN
PROJECT_NAME=vpn-scanner
COMPOSE_PROJECT_NAME=vpn-scanner

# Configuration VPN
USE_VPN=true
VPN_USERNAME=
VPN_PASSWORD=

# Configuration Scan
TARGET_COUNTRY=RU
TARGET_COUNTRIES=RU,CN,KP,IR
SCAN_PORTS=22,80,443,3389,5985,8080,8443
SCAN_RATE=1000
MAX_CIDRS=10
SCAN_INTERVAL=3600
CONTINUOUS_MODE=false

# Configuration Bases de Données
IP2LOCATION_DB_PASSWORD=bojemoi
MSF_DB_PASSWORD=bojemoi

# Configuration Monitoring
GRAFANA_PASSWORD=admin123

# Configuration Système
TZ=Europe/Paris
LOG_LEVEL=INFO
ENVFILE

    # Template configuration VPN
    cat > config/client.ovpn.template << 'VPNTEMPLATE'
# Template de configuration OpenVPN
# Copiez ce fichier vers client.ovpn et adaptez-le

client
dev tun
proto udp
remote your-vpn-server.com 1194

# Certificats (adaptez les chemins)
ca /app/certs/ca.crt
cert /app/certs/client.crt
key /app/certs/client.key
tls-auth /app/certs/ta.key 1

# Sécurité
remote-cert-tls server
cipher AES-256-GCM
auth SHA256
key-direction 1

# Résolution et persistance
resolv-retry infinite
nobind
persist-key
persist-tun

# Scripts DNS
script-security 2
up /etc/openvpn/update-resolv-conf
down /etc/openvpn/update-resolv-conf

# Logging
verb 3
mute 20

# DNS de fallback
dhcp-option DNS 8.8.8.8
dhcp-option DNS 8.8.4.4

# Redirection (décommentez si nécessaire)
# redirect-gateway def1 bypass-dhcp
VPNTEMPLATE

    # Configuration Prometheus
    cat > monitoring/prometheus.yml << 'PROMCONFIG'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "alert_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'vpn-scanner'
    static_configs:
      - targets: ['vpn-scanner-main:8080']
    scrape_interval: 30s
    metrics_path: /metrics
    
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-ip2location:5432', 'postgres-msf:5432']
    scrape_interval: 60s
PROMCONFIG

    # Configuration datasource Grafana
    cat > monitoring/grafana/provisioning/datasources/prometheus.yml << 'GRAFANADS'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    access: proxy
    isDefault: true
GRAFANADS

    # Configuration dashboard Grafana
    cat > monitoring/grafana/provisioning/dashboards/dashboard.yml << 'GRAFANADB'
apiVersion: 1

providers:
  - name: 'VPN Scanner'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards
GRAFANADB

    log_info "✅ Configurations créées"
}

# Scripts SQL d'initialisation
create_sql_init() {
    log_info "🗄️  Création des scripts SQL d'initialisation..."
    
    # Script IP2Location
    cat > sql/ip2location_init.sql << 'SQLIP2LOC'
-- Initialisation base IP2Location
CREATE EXTENSION IF NOT EXISTS cidr;

-- Table exemple (adaptez selon votre structure)
CREATE TABLE IF NOT EXISTS ip2location_db1 (
    id SERIAL PRIMARY KEY,
    ip_from BIGINT,
    ip_to BIGINT,
    country_code VARCHAR(2),
    country_name VARCHAR(64),
    region_name VARCHAR(128),
    city_name VARCHAR(128),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    zip_code VARCHAR(30),
    time_zone VARCHAR(8),
    cidr_z CIDR,
    nmap VARCHAR(10) DEFAULT '0',
    date_nmap TIMESTAMP
);

-- Index pour les performances
CREATE INDEX IF NOT EXISTS idx_ip2location_country ON ip2location_db1(country_code);
CREATE INDEX IF NOT EXISTS idx_ip2location_cidr ON ip2location_db1 USING GIST(cidr_z);
CREATE INDEX IF NOT EXISTS idx_ip2location_nmap ON ip2location_db1(nmap);

-- Exemple de données (remplacez par vos vraies données)
-- INSERT INTO ip2location_db1 (ip_from, ip_to, country_code, country_name, cidr_z) 
-- VALUES (16777216, 16777471, 'RU', 'Russia', '1.0.1.0/24');

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
SQLIP2LOC

    # Script MSF
    cat > sql/msf_init.sql << 'SQLMSF'
-- Initialisation base Metasploit
-- Structure simplifiée compatible MSF

CREATE TABLE IF NOT EXISTS workspaces (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hosts (
    id SERIAL PRIMARY KEY,
    workspace_id INTEGER REFERENCES workspaces(id) ON DELETE CASCADE,
    address VARCHAR(45) NOT NULL,
    name VARCHAR(255),
    state VARCHAR(20) DEFAULT 'alive',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(workspace_id, address)
);

CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    host_id INTEGER REFERENCES hosts(id) ON DELETE CASCADE,
    port INTEGER NOT NULL,
    proto VARCHAR(10) DEFAULT 'tcp',
    state VARCHAR(20) DEFAULT 'open',
    name VARCHAR(255),
    info TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(host_id, port, proto)
);

-- Index pour les performances
CREATE INDEX IF NOT EXISTS idx_hosts_workspace ON hosts(workspace_id);
CREATE INDEX IF NOT EXISTS idx_hosts_address ON hosts(address);
CREATE INDEX IF NOT EXISTS idx_services_host ON services(host_id);
CREATE INDEX IF NOT EXISTS idx_services_port ON services(port);

-- Workspace par défaut
INSERT INTO workspaces (name, description) 
VALUES ('default', 'Default workspace') 
ON CONFLICT (name) DO NOTHING;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
SQLMSF

    log_info "✅ Scripts SQL créés"
}

# Script de démarrage
create_startup_script() {
    log_info "🚀 Création du script de démarrage..."
    
    cat > start-scanner.sh << 'STARTSCRIPT'
#!/bin/bash
# Script de démarrage du scanner VPN

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# Vérifications pré-démarrage
check_requirements() {
    log_info "Vérification des prérequis..."
    
    # Docker et Docker Compose
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose n'est pas installé"
        exit 1
    fi
    
    # Configuration VPN
    if [ ! -f "config/client.ovpn" ]; then
        log_warn "Configuration VPN manquante"
        log_info "Copiez config/client.ovpn.template vers config/client.ovpn et adaptez-le"
        read -p "Continuer sans VPN? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
        export USE_VPN=false
    fi
    
    log_info "✅ Prérequis OK"
}

# Fonction de démarrage
start_services() {
    log_info "🚀 Démarrage des services..."
    
    # Charger les variables d'environnement
    if [ -f ".env" ]; then
        source .env
    fi
    
    # Mode de démarrage
    case "${1:-all}" in
        "db")
            log_info "Démarrage des bases de données uniquement..."
            docker-compose up -d postgres-ip2location postgres-msf
            ;;
        "scanner")
            log_info "Démarrage du scanner uniquement..."
            docker-compose up -d vpn-scanner
            ;;
        "monitoring")
            log_info "Démarrage avec monitoring..."
            docker-compose --profile monitoring up -d
            ;;
        "all"|*)
            log_info "Démarrage complet..."
            docker-compose up -d
            ;;
    esac
    
    # Attendre que les services soient prêts
    log_info "⏳ Attente de la disponibilité des services..."
    sleep 10
    
    # Vérifier le statut
    show_status
}

# Affichage du statut
show_status() {
    log_info "📊 Statut des services:"
    docker-compose ps
    
    log_info "📝 Logs récents du scanner:"
    docker-compose logs --tail 10 vpn-scanner 2>/dev/null || echo "Scanner non démarré"
    
    log_info "🌐 Services disponibles:"
    echo "  • Scanner logs: docker-compose logs -f vpn-scanner"
    echo "  • PostgreSQL IP2Location: localhost:5432"
    echo "  • PostgreSQL MSF: localhost:5433"
    
    if docker-compose ps | grep -q prometheus; then
        echo "  • Prometheus: http://localhost:9090"
    fi
    
    if docker-compose ps | grep -q grafana; then
        echo "  • Grafana: http://localhost:3000 (admin/admin123)"
    fi
}

# Menu principal
case "${1:-help}" in
    "start")
        check_requirements
        start_services "${2:-all}"
        ;;
    "stop")
        log_info "🛑 Arrêt des services..."
        docker-compose down
        ;;
    "restart")
        log_info "🔄 Redémarrage des services..."
        docker-compose restart
        ;;
    "logs")
        service_name="${2:-vpn-scanner}"
        docker-compose logs -f "$service_name"
        ;;
    "status")
        show_status
        ;;
    "shell")
        log_info "🐚 Accès shell au scanner..."
        docker-compose exec vpn-scanner /bin/bash
        ;;
    "clean")
        log_warn "🧹 Nettoyage complet..."
        read -p "Supprimer tous les containers et volumes? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v --remove-orphans
            docker system prune -f
            log_info "✅ Nettoyage terminé"
        fi
        ;;
    "help"|*)
        echo "Usage: $0 {start|stop|restart|logs|status|shell|clean}"
        echo ""
        echo "Commandes:"
        echo "  start [all|db|scanner|monitoring] - Démarrer les services"
        echo "  stop                               - Arrêter tous les services"
        echo "  restart                           - Redémarrer tous les services"
        echo "  logs [service]                    - Afficher les logs"
        echo "  status                            - Afficher le statut"
        echo "  shell                             - Accès shell au scanner"
        echo "  clean                             - Nettoyage complet"
        echo ""
        echo "Exemples:"
        echo "  $0 start                          - Démarrage complet"
        echo "  $0 start db                       - Bases de données uniquement"
        echo "  $0 start monitoring               - Avec Prometheus/Grafana"
        echo "  $0 logs vpn-scanner               - Logs du scanner"
        ;;
esac
STARTSCRIPT

    chmod +x start-scanner.sh
    log_info "✅ Script de démarrage créé"
}

# Script de test
create_test_script() {
    log_info "🧪 Création du script de test..."
    
    cat > test-scanner.sh << 'TESTSCRIPT'
#!/bin/bash
# Script de test pour le scanner VPN

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[✓]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $1"; }

echo "🧪 Tests du Scanner VPN + Masscan + MSF"
echo "========================================"

# Test 1: Containers en cours d'exécution
test_containers() {
    echo "1️⃣ Test des containers..."
    
    containers=("vpn-scanner-main" "postgres-ip2location" "postgres-msf")
    for container in "${containers[@]}"; do
        if docker ps | grep -q "$container"; then
            log_info "$container: Running"
        else
            log_error "$container: Not running"
            return 1
        fi
    done
}

# Test 2: Connectivité bases de données
test_databases() {
    echo "2️⃣ Test des bases de données..."
    
    # IP2Location DB
    if docker-compose exec -T postgres-ip2location pg_isready -U postgres -d ip2location_db1 &>/dev/null; then
        log_info "IP2Location DB: Connected"
    else
        log_error "IP2Location DB: Connection failed"
        return 1
    fi
    
    # MSF DB
    if docker-compose exec -T postgres-msf pg_isready -U postgres -d msf &>/dev/null; then
        log_info "MSF DB: Connected"
    else
        log_error "MSF DB: Connection failed"
        return 1
    fi
}

# Test 3: Services dans le scanner
test_scanner_services() {
    echo "3️⃣ Test des services dans le scanner..."
    
    # Test Python et modules
    if docker-compose exec -T vpn-scanner python3 -c "import psycopg2; print('OK')" &>/dev/null; then
        log_info "Python PostgreSQL: OK"
    else
        log_error "Python PostgreSQL: Failed"
        return 1
    fi
    
    # Test OpenVPN
    if docker-compose exec -T vpn-scanner openvpn --version &>/dev/null; then
        log_info "OpenVPN: Available"
    else
        log_error "OpenVPN: Not available"
        return 1
    fi
    
    # Test Masscan
    if docker-compose exec -T vpn-scanner masscan --version &>/dev/null; then
        log_info "Masscan: Available"
    else
        log_error "Masscan: Not available"
        return 1
    fi
}

# Test 4: Configuration VPN
test_vpn_config() {
    echo "4️⃣ Test de la configuration VPN..."
    
    if [ -f "config/client.ovpn" ]; then
        log_info "Configuration VPN: Present"
    else
        log_warn "Configuration VPN: Missing (template available)"
    fi
    
    # Test device TUN dans le container
    if docker-compose exec -T vpn-scanner test -c /dev/net/tun &>/dev/null; then
        log_info "TUN device: Available"
    else
        log_error "TUN device: Not available"
        log_warn "Vérifiez: --device /dev/net/tun --privileged"
        return 1
    fi
}

# Test 5: Logs et healthcheck
test_health() {
    echo "5️⃣ Test de santé du système..."
    
    # Healthcheck du scanner
    health_status=$(docker inspect --format='{{.State.Health.Status}}' vpn-scanner-main 2>/dev/null || echo "none")
    case "$health_status" in
        "healthy")
            log_info "Scanner health: Healthy"
            ;;
        "unhealthy")
            log_error "Scanner health: Unhealthy"
            return 1
            ;;
        "starting")
            log_warn "Scanner health: Starting..."
            ;;
        "none")
            log_warn "Scanner health: No healthcheck"
            ;;
    esac
    
    # Vérifier les logs récents
    if docker-compose logs --tail 10 vpn-scanner 2>/dev/null | grep -q "ERROR"; then
        log_warn "Erreurs détectées dans les logs récents"
    else
        log_info "Logs: No recent errors"
    fi
}

# Exécution des tests
main() {
    local failed=0
    
    test_containers || failed=1
    test_databases || failed=1
    test_scanner_services || failed=1
    test_vpn_config || failed=1
    test_health || failed=1
    
    echo "========================================"
    if [ $failed -eq 0 ]; then
        log_info "🎉 Tous les tests sont passés!"
        echo ""
        echo "Services disponibles:"
        echo "  • Scanner: docker-compose logs -f vpn-scanner"
        echo "  • Shell: docker-compose exec vpn-scanner /bin/bash"
        
        if docker-compose ps | grep -q prometheus; then
            echo "  • Prometheus: http://localhost:9090"
        fi
        
        if docker-compose ps | grep -q grafana; then
            echo "  • Grafana: http://localhost:3000"
        fi
    else
        log_error "❌ Certains tests ont échoué"
        echo ""
        echo "Pour déboguer:"
        echo "  • Logs: ./start-scanner.sh logs"
        echo "  • Status: ./start-scanner.sh status"
        echo "  • Shell: ./start-scanner.sh shell"
        exit 1
    fi
}

main "$@"
TESTSCRIPT

    chmod +x test-scanner.sh
    log_info "✅ Script de test créé"
}

# Fonction principale
main() {
    echo "🛡️  Configuration Scanner VPN + Masscan + MSF v${VERSION}"
    echo "========================================================="
    
    create_directory_structure
    create_default_configs
    create_sql_init
    create_startup_script
    create_test_script
    
    echo ""
    log_info "🎉 Configuration terminée avec succès!"
    echo ""
    echo "📋 Prochaines étapes:"
    echo "1. Configurez votre VPN: config/client.ovpn.template → config/client.ovpn"
    echo "2. Copiez vos certificats VPN dans le dossier certs/"
    echo "3. Modifiez le fichier .env selon vos besoins"
    echo "4. Démarrez: ./start-scanner.sh start"
    echo "5. Testez: ./test-scanner.sh"
    echo ""
    echo "🔧 Commandes utiles:"
    echo "  • Démarrage complet: ./start-scanner.sh start"
    echo "  • Avec monitoring: ./start-scanner.sh start monitoring"
    echo "  • Logs en temps réel: ./start-scanner.sh logs"
    echo "  • Accès shell: ./start-scanner.sh shell"
    echo "  • Tests: ./test-scanner.sh"
    echo ""
    echo "📊 Monitoring (optionnel):"
    echo "  • Prometheus: http://localhost:9090"
    echo "  • Grafana: http://localhost:3000 (admin/admin123)"
}

main "$@"
EOF

chmod +x setup-unified-scanner.sh

echo "✅ Scripts de gestion créés avec succès!"
echo ""
echo "🚀 Pour démarrer la configuration:"
echo "  ./setup-unified-scanner.sh"
