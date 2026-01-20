#!/bin/ash

# ========================================
# Collection de scripts pour ZAP Proxy
# ========================================

# Script 1: Installation et configuration de base
setup_zap() {
    echo "=== Installation et configuration ZAP ==="
    
    # Installation via Docker (recommandé)
    docker pull owasp/zap2docker-stable
    
    # Ou téléchargement direct
    # wget https://github.com/zaproxy/zaproxy/releases/download/v2.14.0/ZAP_2_14_0_unix.sh
    # chmod +x ZAP_2_14_0_unix.sh
    # ./ZAP_2_14_0_unix.sh
    
    # Configuration du proxy
    export ZAP_HOST="localhost"
    export ZAP_PORT="8080"
    export ZAP_API_KEY="votre-cle-api-ici"
    
    echo "ZAP configuré sur ${ZAP_HOST}:${ZAP_PORT}"
}

# Script 2: Démarrage ZAP en mode daemon
start_zap_daemon() {
    echo "=== Démarrage ZAP en mode daemon ==="
    
    # Avec Docker
    docker run -u zap -p 8080:8080 -i owasp/zap2docker-stable zap.sh \
        -daemon -host 0.0.0.0 -port 8080 \
        -config api.addrs.addr.name=".*" \
        -config api.addrs.addr.regex=true \
        -config api.key=$ZAP_API_KEY
    
    # Sans Docker
    # /opt/zaproxy/zap.sh -daemon -host localhost -port 8080 -config api.key=$ZAP_API_KEY
    
    sleep 10
    echo "ZAP daemon démarré"
}

# Script 3: Scan rapide d'une URL
quick_scan() {
    local target_url=$1
    
    if [ -z "$target_url" ]; then
        echo "Usage: quick_scan <URL>"
        return 1
    fi
    
    echo "=== Scan rapide de $target_url ==="
    
    # Spider l'application
    echo "Spider en cours..."
    curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/spider/action/scan/?url=${target_url}&apikey=${ZAP_API_KEY}"
    
    # Attendre la fin du spider
    while true; do
        status=$(curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/spider/view/status/?apikey=${ZAP_API_KEY}" | jq -r '.status')
        if [ "$status" = "100" ]; then
            break
        fi
        echo "Spider: ${status}%"
        sleep 5
    done
    
    # Scan actif
    echo "Scan actif en cours..."
    curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/ascan/action/scan/?url=${target_url}&apikey=${ZAP_API_KEY}"
    
    # Attendre la fin du scan
    while true; do
        status=$(curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/ascan/view/status/?apikey=${ZAP_API_KEY}" | jq -r '.status')
        if [ "$status" = "100" ]; then
            break
        fi
        echo "Scan actif: ${status}%"
        sleep 10
    done
    
    echo "Scan terminé pour $target_url"
}

# Script 4: Génération de rapports
generate_reports() {
    local target_name=$1
    local output_dir=${2:-"./zap_reports"}
    
    if [ -z "$target_name" ]; then
        echo "Usage: generate_reports <nom_cible> [repertoire_sortie]"
        return 1
    fi
    
    echo "=== Génération des rapports pour $target_name ==="
    
    mkdir -p "$output_dir"
    
    # Rapport HTML
    curl -s "http://${ZAP_HOST}:${ZAP_PORT}/OTHER/core/other/htmlreport/?apikey=${ZAP_API_KEY}" \
        -o "${output_dir}/${target_name}_report.html"
    
    # Rapport XML
    curl -s "http://${ZAP_HOST}:${ZAP_PORT}/OTHER/core/other/xmlreport/?apikey=${ZAP_API_KEY}" \
        -o "${output_dir}/${target_name}_report.xml"
    
    # Rapport JSON
    curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/view/alerts/?apikey=${ZAP_API_KEY}" \
        -o "${output_dir}/${target_name}_alerts.json"
    
    echo "Rapports générés dans $output_dir"
}

# Script 5: Configuration avancée pour les applications authentifiées
setup_authenticated_scan() {
    local target_url=$1
    local context_name=$2
    local username=$3
    local password=$4
    
    echo "=== Configuration scan authentifié ==="
    
    # Créer un contexte
    curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/context/action/newContext/?contextName=${context_name}&apikey=${ZAP_API_KEY}"
    
    # Ajouter l'URL au contexte
    curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/context/action/includeInContext/?contextName=${context_name}&regex=${target_url}.*&apikey=${ZAP_API_KEY}"
    
    # Créer un utilisateur
    curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/users/action/newUser/?contextId=0&name=${username}&apikey=${ZAP_API_KEY}"
    
    # Configuration de l'authentification (à adapter selon votre app)
    curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/authentication/action/setAuthenticationMethod/?contextId=0&authMethodName=formBasedAuthentication&authMethodConfigParams=loginUrl=${target_url}/login&loginRequestData=username=${username}&password=${password}&apikey=${ZAP_API_KEY}"
    
    echo "Configuration authentifiée terminée"
}

# Script 6: Scan avec exclusions
scan_with_exclusions() {
    local target_url=$1
    local exclusions_file=$2
    
    echo "=== Scan avec exclusions ==="
    
    # Charger les exclusions depuis un fichier
    if [ -f "$exclusions_file" ]; then
        while IFS= read -r pattern; do
            if [[ ! "$pattern" =~ ^#.* ]] && [[ -n "$pattern" ]]; then
                curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/action/excludeFromProxy/?regex=${pattern}&apikey=${ZAP_API_KEY}"
                echo "Exclusion ajoutée: $pattern"
            fi
        done < "$exclusions_file"
    fi
    
    # Lancer le scan
    quick_scan "$target_url"
}

# Script 7: Monitoring des performances ZAP
monitor_zap_performance() {
    echo "=== Monitoring ZAP ==="
    
    while true; do
        # Statistiques mémoire
        memory_stats=$(curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/view/stats/?apikey=${ZAP_API_KEY}")
        
        # Nombre d'alertes
        alerts_count=$(curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/view/numberOfAlerts/?apikey=${ZAP_API_KEY}" | jq -r '.numberOfAlerts')
        
        # URLs découvertes
        urls_count=$(curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/view/urls/?apikey=${ZAP_API_KEY}" | jq -r '.urls | length')
        
        echo "$(date): Alertes: $alerts_count, URLs: $urls_count"
        
        sleep 30
    done
}

# Script 8: Sauvegarde et restauration de session
backup_session() {
    local session_name=$1
    local backup_dir=${2:-"./zap_backups"}
    
    echo "=== Sauvegarde de session: $session_name ==="
    
    mkdir -p "$backup_dir"
    
    # Sauvegarder la session
    curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/action/saveSession/?name=${backup_dir}/${session_name}&overwrite=true&apikey=${ZAP_API_KEY}"
    
    echo "Session sauvegardée: ${backup_dir}/${session_name}"
}

restore_session() {
    local session_file=$1
    
    echo "=== Restauration de session: $session_file ==="
    
    # Charger la session
    curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/action/loadSession/?name=${session_file}&apikey=${ZAP_API_KEY}"
    
    echo "Session restaurée: $session_file"
}

# Script 9: Arrêt propre de ZAP
stop_zap() {
    echo "=== Arrêt de ZAP ==="
    
    # Arrêt via API
    curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/action/shutdown/?apikey=${ZAP_API_KEY}"
    
    # Ou arrêt du container Docker
    # docker stop $(docker ps -q --filter ancestor=owasp/zap2docker-stable)
    
    echo "ZAP arrêté"
}

# Script 10: Scan complet automatisé
full_automated_scan() {
    local target_url=$1
    local project_name=$2
    
    if [ -z "$target_url" ] || [ -z "$project_name" ]; then
        echo "Usage: full_automated_scan <URL> <nom_projet>"
        return 1
    fi
    
    echo "=== Scan complet automatisé de $target_url ==="
    
    # Démarrer ZAP
    start_zap_daemon &
    sleep 15
    
    # Créer un répertoire de projet
    project_dir="./scans/${project_name}_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$project_dir"
    
    # Sauvegarder la configuration
    echo "Target: $target_url" > "${project_dir}/scan_info.txt"
    echo "Date: $(date)" >> "${project_dir}/scan_info.txt"
    
    # Lancer le scan
    quick_scan "$target_url"
    
    # Générer les rapports
    generate_reports "$project_name" "$project_dir"
    
    # Sauvegarder la session
    backup_session "${project_name}_$(date +%Y%m%d)" "$project_dir"
    
    # Arrêter ZAP
    stop_zap
    
    echo "Scan complet terminé. Résultats dans: $project_dir"
}

# ========================================
# Fonctions utilitaires
# ========================================

# Vérifier si ZAP est en cours d'exécution
check_zap_status() {
    if curl -s "http://${ZAP_HOST}:${ZAP_PORT}/JSON/core/view/version/?apikey=${ZAP_API_KEY}" > /dev/null 2>&1; then
        echo "ZAP est en cours d'exécution"
        return 0
    else
        echo "ZAP n'est pas accessible"
        return 1
    fi
}

# Afficher l'aide
show_help() {
    echo "=== Scripts ZAP Proxy - Aide ==="
    echo ""
    echo "Fonctions disponibles:"
    echo "  setup_zap                    - Installation et configuration"
    echo "  start_zap_daemon            - Démarrer ZAP en mode daemon"
    echo "  quick_scan <URL>            - Scan rapide d'une URL"
    echo "  generate_reports <nom>      - Générer les rapports"
    echo "  setup_authenticated_scan    - Configuration pour scan authentifié"
    echo "  scan_with_exclusions        - Scan avec exclusions"
    echo "  monitor_zap_performance     - Monitoring des performances"
    echo "  backup_session <nom>        - Sauvegarder une session"
    echo "  restore_session <fichier>   - Restaurer une session"
    echo "  full_automated_scan         - Scan complet automatisé"
    echo "  stop_zap                    - Arrêter ZAP"
    echo "  check_zap_status            - Vérifier le statut de ZAP"
    echo ""
    echo "Variables d'environnement:"
    echo "  ZAP_HOST     - Hôte ZAP (défaut: localhost)"
    echo "  ZAP_PORT     - Port ZAP (défaut: 8080)"
    echo "  ZAP_API_KEY  - Clé API ZAP"
    echo ""
    echo "Exemple d'utilisation:"
    echo "  export ZAP_API_KEY='votre-cle'"
    echo "  full_automated_scan 'https://example.com' 'test_site'"
}

# Point d'entrée principal
main() {
    case "$1" in
        "setup")
            setup_zap
            ;;
        "start")
            start_zap_daemon
            ;;
        "scan")
            quick_scan "$2"
            ;;
        "report")
            generate_reports "$2" "$3"
            ;;
        "full")
            full_automated_scan "$2" "$3"
            ;;
        "stop")
            stop_zap
            ;;
        "status")
            check_zap_status
            ;;
        "help"|"")
            show_help
            ;;
        *)
            echo "Commande inconnue: $1"
            show_help
            ;;
    esac
}

