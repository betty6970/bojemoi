#!/bin/bash
#
# Script d'orchestration pour les scans de sécurité
# Utilise Masscan, ZAP, Metasploit et Burp avec Faraday
#

set -e

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration par défaut
FARADAY_URL="${FARADAY_URL:-http://faraday:5985}"
FARADAY_USER="${FARADAY_USER:-faraday}"
FARADAY_PASS="${FARADAY_PASS:-changeme}"
WORKSPACE="${WORKSPACE:-security-scan}"
TARGET=""
OUTPUT_DIR="/results"

# Fonction d'aide
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -t, --target TARGET     Cible à scanner (IP, réseau CIDR ou URL)
    -w, --workspace NAME    Nom du workspace Faraday (défaut: security-scan)
    -o, --output DIR        Répertoire de sortie (défaut: /results)
    --masscan               Exécuter Masscan
    --zap                   Exécuter ZAP
    --metasploit            Exécuter Metasploit
    --burp                  Exécuter Burp Suite
    --all                   Exécuter tous les outils
    -h, --help              Afficher cette aide

Exemples:
    $0 --target 192.168.1.0/24 --all
    $0 --target http://example.com --zap
    $0 --target 10.0.0.1 --masscan --metasploit

EOF
    exit 0
}

# Fonctions de log
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérifier si Faraday est accessible
check_faraday() {
    log_info "Vérification de la connexion à Faraday..."
    if curl -s -f "${FARADAY_URL}" > /dev/null 2>&1; then
        log_success "Faraday est accessible"
        return 0
    else
        log_error "Faraday n'est pas accessible à ${FARADAY_URL}"
        return 1
    fi
}

# Exécuter Masscan
run_masscan() {
    log_info "Démarrage du scan Masscan sur ${TARGET}..."
    
    MASSCAN_OUTPUT="${OUTPUT_DIR}/masscan_${WORKSPACE}_$(date +%Y%m%d_%H%M%S).json"
    
    masscan ${TARGET} -p1-65535 --rate=10000 -oJ "${MASSCAN_OUTPUT}" || {
        log_error "Échec du scan Masscan"
        return 1
    }
    
    log_success "Scan Masscan terminé: ${MASSCAN_OUTPUT}"
    
    # Import dans Faraday
    log_info "Import des résultats Masscan dans Faraday..."
    python3 /scripts/masscan_to_faraday.py \
        --faraday-url "${FARADAY_URL}" \
        --faraday-user "${FARADAY_USER}" \
        --faraday-pass "${FARADAY_PASS}" \
        --masscan-json "${MASSCAN_OUTPUT}" \
        --workspace "${WORKSPACE}" || {
        log_error "Échec de l'import Masscan vers Faraday"
        return 1
    }
    
    log_success "Import Masscan terminé"
    return 0
}

# Exécuter ZAP
run_zap() {
    log_info "Démarrage du scan ZAP sur ${TARGET}..."
    
    # Vérifier que la cible est une URL
    if [[ ! "${TARGET}" =~ ^https?:// ]]; then
        log_error "ZAP nécessite une URL (http:// ou https://)"
        return 1
    fi
    
    ZAP_OUTPUT="${OUTPUT_DIR}/zap_${WORKSPACE}_$(date +%Y%m%d_%H%M%S).json"
    
    # Utiliser l'API ZAP pour lancer un scan
    docker exec faraday-zap zap-cli --zap-url http://localhost:8080 quick-scan \
        --self-contained --start-options '-config api.disablekey=true' \
        "${TARGET}" || {
        log_error "Échec du scan ZAP"
        return 1
    }
    
    log_success "Scan ZAP terminé"
    
    # Import dans Faraday
    log_info "Import des résultats ZAP dans Faraday..."
    docker exec faraday-server python3 /scripts/zap_to_faraday.py \
        --faraday-url "${FARADAY_URL}" \
        --faraday-user "${FARADAY_USER}" \
        --faraday-pass "${FARADAY_PASS}" \
        --zap-url "http://zap:8080" \
        --workspace "${WORKSPACE}" \
        --target-url "${TARGET}" || {
        log_error "Échec de l'import ZAP vers Faraday"
        return 1
    }
    
    log_success "Import ZAP terminé"
    return 0
}

# Exécuter Metasploit
run_metasploit() {
    log_info "Démarrage du scan Metasploit sur ${TARGET}..."
    
    MSF_OUTPUT="${OUTPUT_DIR}/metasploit_${WORKSPACE}_$(date +%Y%m%d_%H%M%S).xml"
    
    # Créer un script Metasploit
    MSF_SCRIPT="/tmp/msf_scan_${WORKSPACE}.rc"
    cat > "${MSF_SCRIPT}" << EOF
db_nmap -sV -O ${TARGET}
services -o ${MSF_OUTPUT}
exit
EOF
    
    # Exécuter le script Metasploit
    docker exec -i faraday-metasploit msfconsole -r /tmp/msf_scan_${WORKSPACE}.rc || {
        log_error "Échec du scan Metasploit"
        return 1
    }
    
    log_success "Scan Metasploit terminé: ${MSF_OUTPUT}"
    
    # Import dans Faraday
    if [ -f "${MSF_OUTPUT}" ]; then
        log_info "Import des résultats Metasploit dans Faraday..."
        docker exec faraday-server python3 /scripts/msf_to_faraday.py \
            --faraday-url "${FARADAY_URL}" \
            --faraday-user "${FARADAY_USER}" \
            --faraday-pass "${FARADAY_PASS}" \
            --msf-xml "${MSF_OUTPUT}" \
            --workspace "${WORKSPACE}" || {
            log_error "Échec de l'import Metasploit vers Faraday"
            return 1
        }
        
        log_success "Import Metasploit terminé"
    else
        log_warning "Fichier XML Metasploit non trouvé"
    fi
    
    return 0
}

# Exécuter Burp Suite
run_burp() {
    log_info "Configuration de Burp Suite pour ${TARGET}..."
    
    # Note: Burp Suite nécessite une configuration manuelle
    log_warning "Burp Suite nécessite une configuration manuelle"
    log_info "Accédez à http://localhost:8081 pour configurer Burp Suite"
    log_info "Configurez le proxy sur ${TARGET} et lancez le scan"
    
    return 0
}

# Parser les arguments
RUN_MASSCAN=false
RUN_ZAP=false
RUN_METASPLOIT=false
RUN_BURP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--target)
            TARGET="$2"
            shift 2
            ;;
        -w|--workspace)
            WORKSPACE="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --masscan)
            RUN_MASSCAN=true
            shift
            ;;
        --zap)
            RUN_ZAP=true
            shift
            ;;
        --metasploit)
            RUN_METASPLOIT=true
            shift
            ;;
        --burp)
            RUN_BURP=true
            shift
            ;;
        --all)
            RUN_MASSCAN=true
            RUN_ZAP=true
            RUN_METASPLOIT=true
            RUN_BURP=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            log_error "Option inconnue: $1"
            usage
            ;;
    esac
done

# Vérifications
if [ -z "${TARGET}" ]; then
    log_error "Cible non spécifiée. Utilisez -t ou --target"
    usage
fi

# Créer le répertoire de sortie
mkdir -p "${OUTPUT_DIR}"

# Vérifier Faraday
check_faraday || exit 1

log_info "=== Démarrage des scans ==="
log_info "Cible: ${TARGET}"
log_info "Workspace: ${WORKSPACE}"
log_info "Répertoire de sortie: ${OUTPUT_DIR}"
echo

# Exécuter les scans
if [ "${RUN_MASSCAN}" = true ]; then
    run_masscan
fi

if [ "${RUN_ZAP}" = true ]; then
    run_zap
fi

if [ "${RUN_METASPLOIT}" = true ]; then
    run_metasploit
fi

if [ "${RUN_BURP}" = true ]; then
    run_burp
fi

log_success "=== Tous les scans sont terminés ==="
log_info "Accédez à Faraday: ${FARADAY_URL}"
log_info "Workspace: ${WORKSPACE}"
