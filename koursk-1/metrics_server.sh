#!/bin/ash
# metrics_server.sh
# Serveur HTTP simple pour exposer les métriques Prometheus
# Compatible Alpine Linux (ash shell)

set -eu

# Configuration
METRICS_DIR="/rsync/metrics"
PORT="${METRICS_PORT:-8080}"
METRICS_FILE="$METRICS_DIR/rsync_metrics.prom"
PID_FILE="/tmp/metrics_server.pid"

# Créer le répertoire s'il n'existe pas
mkdir -p "$METRICS_DIR"

# Fonction de logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [METRICS-SERVER] $*"
}

# Fonction pour créer un fichier de métriques par défaut
create_default_metrics() {
    cat > "$METRICS_FILE" << 'EOF'
# HELP rsync_info Information about rsync monitoring
# TYPE rsync_info gauge
rsync_info{version="1.0",server="metrics_server"} 1

# HELP rsync_server_start_time Server start time
# TYPE rsync_server_start_time gauge
EOF
    echo "rsync_server_start_time $(date +%s)" >> "$METRICS_FILE"
}

# Fonction pour gérer les requêtes HTTP
handle_request() {
    # Lire la première ligne de la requête
    read -r request_line || return 1
    
    # Extraire la méthode et le chemin
    method=$(echo "$request_line" | cut -d' ' -f1)
    path=$(echo "$request_line" | cut -d' ' -f2)
    
    # Lire et ignorer les headers
    while IFS= read -r line && [ -n "$line" ] && [ "$line" != "$(printf '\r')" ]; do
        :
    done
    
    # Répondre selon le chemin demandé
    case "$path" in
        "/metrics")
            # Envoyer les métriques Prometheus
            echo "HTTP/1.1 200 OK"
            echo "Content-Type: text/plain; charset=utf-8"
            echo "Cache-Control: no-cache"
            echo "Connection: close"
            echo ""
            if [ -f "$METRICS_FILE" ]; then
                cat "$METRICS_FILE"
            else
                echo "# No metrics available"
            fi
            ;;
        "/health")
            # Point de santé
            echo "HTTP/1.1 200 OK"
            echo "Content-Type: text/plain"
            echo "Connection: close"
            echo ""
            echo "OK"
            ;;
        "/info")
            # Informations sur le serveur
            echo "HTTP/1.1 200 OK"
            echo "Content-Type: application/json"
            echo "Connection: close"
            echo ""
            cat << EOF
{
    "name": "rsync-metrics-server",
    "version": "1.0",
    "platform": "alpine",
    "metrics_file": "$METRICS_FILE",
    "port": $PORT,
    "uptime": $(( $(date +%s) - $(stat -c %Y "$PID_FILE" 2>/dev/null || echo $(date +%s)) ))
}
EOF
            ;;
        *)
            # 404 pour tous les autres chemins
            echo "HTTP/1.1 404 Not Found"
            echo "Content-Type: text/plain"
            echo "Connection: close"
            echo ""
            echo "Not Found"
            echo "Available endpoints:"
            echo "  /metrics - Prometheus metrics"
            echo "  /health  - Health check"
            echo "  /info    - Server information"
            ;;
    esac
}

# Fonction pour démarrer le serveur avec netcat
start_netcat_server() {
    log "Démarrage du serveur avec netcat sur le port $PORT"
    
    while true; do
        # Créer un pipe nommé pour la communication
        fifo="/tmp/http_fifo_$$"
        mkfifo "$fifo" 2>/dev/null || true
        
        # Démarrer netcat et traiter les requêtes
        if nc -l -p "$PORT" < "$fifo" | handle_request > "$fifo" 2>/dev/null; then
            :
        else
            log "Connexion fermée, redémarrage..."
        fi
        
        # Nettoyer le pipe
        rm -f "$fifo"
        
        # Petite pause avant de redémarrer
        sleep 0.1
    done
}

# Fonction pour démarrer le serveur avec socat
start_socat_server() {
    log "Démarrage du serveur avec socat sur le port $PORT"
    
    # Créer un script temporaire pour socat
    handler_script="/tmp/http_handler_$$.sh"
    cat > "$handler_script" << 'HANDLER_EOF'
#!/bin/ash
handle_request() {
    read -r request_line || return 1
    method=$(echo "$request_line" | cut -d' ' -f1)
    path=$(echo "$request_line" | cut -d' ' -f2)
    
    while IFS= read -r line && [ -n "$line" ] && [ "$line" != "$(printf '\r')" ]; do
        :
    done
    
    case "$path" in
        "/metrics")
            echo "HTTP/1.1 200 OK"
            echo "Content-Type: text/plain; charset=utf-8"
            echo "Connection: close"
            echo ""
            cat "/rsync/metrics/rsync_metrics.prom" 2>/dev/null || echo "# No metrics"
            ;;
        "/health")
            echo "HTTP/1.1 200 OK"
            echo "Content-Type: text/plain"
            echo "Connection: close"
            echo ""
            echo "OK"
            ;;
        *)
            echo "HTTP/1.1 404 Not Found"
            echo "Content-Type: text/plain"
            echo "Connection: close"
            echo ""
            echo "Not Found"
            ;;
    esac
}
handle_request
HANDLER_EOF
    
    chmod +x "$handler_script"
    
    # Démarrer socat avec le handler
    socat TCP-LISTEN:"$PORT",fork,reuseaddr EXEC:"$handler_script"
}

# Fonction pour démarrer le serveur Python (fallback)
start_python_server() {
    log "Démarrage du serveur Python sur le port $PORT"
    
    # Utiliser le serveur Python intégré
    if [ -f "/rsync/metrics/simple_exporter.py" ]; then
        python3 /rsync/metrics/simple_exporter.py
    else
        # Créer un serveur minimal à la volée
        python3 -c "
import http.server
import socketserver
import os

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            try:
                with open('$METRICS_FILE', 'r') as f:
                    self.wfile.write(f.read().encode())
            except:
                self.wfile.write(b'# No metrics available')
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()

with socketserver.TCPServer(('', $PORT), Handler) as httpd:
    print('Serveur Python démarré sur le port $PORT')
    httpd.serve_forever()
"
    fi
}

# Fonction pour choisir et démarrer le serveur
start_server() {
    log "Démarrage du serveur de métriques sur le port $PORT"
    log "Métriques disponibles sur http://localhost:$PORT/metrics"
    
    # Enregistrer le PID
    echo $$ > "$PID_FILE"
    
    # Créer les métriques par défaut si le fichier n'existe pas
    if [ ! -f "$METRICS_FILE" ]; then
        create_default_metrics
    fi
    
    # Choisir le serveur selon les outils disponibles
    if command -v python3 >/dev/null 2>&1; then
        start_python_server
    elif command -v socat >/dev/null 2>&1; then
        start_socat_server
    elif command -v nc >/dev/null 2>&1; then
        start_netcat_server
    else
        log "ERREUR: Aucun outil disponible pour démarrer le serveur HTTP"
        log "Outils supportés: python3, socat, netcat"
        exit 1
    fi
}

# Fonction pour arrêter le serveur
stop_server() {
    log "Arrêt du serveur de métriques"
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi
    
    # Nettoyer les fichiers temporaires
    rm -f /tmp/http_fifo_* /tmp/http_handler_*.sh
}

# Fonction pour vérifier le statut
check_status() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "Serveur actif (PID: $pid)"
            return 0
        else
            log "Serveur arrêté (PID obsolète: $pid)"
            rm -f "$PID_FILE"
            return 1
        fi
    else
        log "Serveur non démarré"
        return 1
    fi
}

# Fonction d'aide
show_help() {
    cat << 'EOF'
Usage: metrics_server.sh [COMMANDE]

Commandes:
    start     Démarrer le serveur (défaut)
    stop      Arrêter le serveur
    restart   Redémarrer le serveur
    status    Vérifier le statut
    test      Tester le serveur
    help      Afficher cette aide

Variables d'environnement:
    METRICS_PORT    Port du serveur (défaut: 8080)
    METRICS_DIR     Répertoire des métriques (défaut: /rsync/metrics)

Endpoints disponibles:
    /metrics    Métriques Prometheus
    /health     Vérification de santé
    /info       Informations serveur
EOF
}

# Fonction de test
test_server() {
    log "Test du serveur de métriques..."
    
    if ! check_status; then
        log "Serveur non actif, impossible de tester"
        return 1
    fi
    
    # Test avec curl si disponible
    if command -v curl >/dev/null 2>&1; then
        if curl -s "http://localhost:$PORT/health" | grep -q "OK"; then
            log "Test réussi avec curl"
            return 0
        fi
    fi
    
    # Test avec netcat
    if command -v nc >/dev/null 2>&1; then
        if echo -e "GET /health HTTP/1.0\r\n\r\n" | nc localhost "$PORT" | grep -q "OK"; then
            log "Test réussi avec netcat"
            return 0
        fi
    fi
    
    log "Test échoué"
    return 1
}

# Fonction de nettoyage à l'arrêt
cleanup() {
    stop_server
    exit 0
}

# Gestion des signaux
trap cleanup INT TERM

# Fonction principale
main() {
    case "${1:-start}" in
        "start")
            if check_status; then
                log "Serveur déjà actif"
                exit 0
            fi
            start_server
            ;;
        "stop")
            stop_server
            ;;
        "restart")
            stop_server
            sleep 1
            start_server
            ;;
        "status")
            check_status
            ;;
        "test")
            test_server
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            echo "Commande inconnue: $1"
            show_help
            exit 1
            ;;
    esac
}

# Exécution
main "$@"



