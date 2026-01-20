#!/bin/ash
# rsync-scripts/rsync_wrapper_simple.sh
# Script wrapper pour rsync avec monitoring via Loki/Prometheus uniquement

set -eu

# Configuration
SCRIPT_DIR=$(dirname "$0")
LOG_DIR="/rsync/logs"
METRICS_DIR="/rsync/metrics"

# Créer les répertoires s'ils n'existent pas
mkdir -p "$LOG_DIR" "$METRICS_DIR"

# Fonction de logging structuré pour Loki
log_structured() {
    local level="$1"
    local job_name="$2"
    local message="$3"
    local extra_fields="$4"
    
    local timestamp=$(date '+%Y-%m-%dT%H:%M:%S.%3NZ')
    local log_entry="{\"timestamp\":\"$timestamp\",\"level\":\"$level\",\"job\":\"$job_name\",\"message\":\"$message\"$extra_fields}"
    
    echo "$log_entry" >> "$LOG_DIR/rsync.jsonl"
    echo "$(date '+%Y/%m/%d %H:%M:%S') [$level] $job_name: $message" >> "$LOG_DIR/rsync.log"
}

# Fonction pour exposer les métriques Prometheus
expose_metrics() {
    local job_name="$1"
    local status="$2"
    local duration="$3"
    local bytes_transferred="$4"
    local files_transferred="$5"
    local exit_code="$6"
    
    local metrics_file="$METRICS_DIR/rsync_metrics.prom"
    local timestamp=$(date +%s)
    
    # Écrire les métriques au format Prometheus
    cat > "$metrics_file" << EOF
# HELP rsync_duration_seconds Duration of rsync operation in seconds
# TYPE rsync_duration_seconds gauge
rsync_duration_seconds{job="$job_name"} $duration $timestamp

# HELP rsync_bytes_transferred_total Total bytes transferred
# TYPE rsync_bytes_transferred_total gauge
rsync_bytes_transferred_total{job="$job_name"} $bytes_transferred $timestamp

# HELP rsync_files_transferred_total Total files transferred
# TYPE rsync_files_transferred_total gauge
rsync_files_transferred_total{job="$job_name"} $files_transferred $timestamp

# HELP rsync_last_success_timestamp Timestamp of last successful rsync
# TYPE rsync_last_success_timestamp gauge
rsync_last_success_timestamp{job="$job_name"} $([ "$status" = "success" ] && echo $timestamp || echo 0) $timestamp

# HELP rsync_exit_code Exit code of rsync command
# TYPE rsync_exit_code gauge
rsync_exit_code{job="$job_name"} $exit_code $timestamp
EOF

    # Exposer via un serveur HTTP simple pour Prometheus
    python3 -c "
import http.server
import socketserver
import threading
import time

class MetricsHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            try:
                with open('$metrics_file', 'r') as f:
                    self.wfile.write(f.read().encode())
            except:
                self.wfile.write(b'# No metrics available\n')
        else:
            self.send_response(404)
            self.end_headers()

def start_server():
    with socketserver.TCPServer(('', 8080), MetricsHandler) as httpd:
        httpd.serve_forever()

server_thread = threading.Thread(target=start_server, daemon=True)
server_thread.start()
" &
}

# Fonction pour parser les statistiques rsync
parse_rsync_stats() {
    local output_file="$1"
    local bytes_transferred=0
    local files_transferred=0
    local files_deleted=0
    
    if [[ -f "$output_file" ]]; then
        # Parser la sortie rsync avec --stats
        bytes_transferred=$(grep -E "Total transferred file size:|total size is" "$output_file" | tail -1 | grep -oE '[0-9,]+' | tr -d ',' | head -1 || echo "0")
        files_transferred=$(grep "Number of files transferred:" "$output_file" | grep -oE '[0-9,]+' | tr -d ',' || echo "0")
        files_deleted=$(grep "Number of deleted files:" "$output_file" | grep -oE '[0-9,]+' | tr -d ',' || echo "0")
    fi
    
    echo "$bytes_transferred $files_transferred $files_deleted"
}

# Fonction principale de synchronisation
run_rsync() {
    local job_name="$1"
    local source="$2"
    local destination="$3"
    shift 3
    local rsync_options="$*"
    
    local start_time=$(date '+%Y-%m-%dT%H:%M:%S.%3NZ')
    local start_timestamp=$(date +%s)
    local output_file="$LOG_DIR/${job_name}_$$.log"
    
    log_structured "INFO" "$job_name" "Starting rsync job" ",\"source\":\"$source\",\"destination\":\"$destination\",\"options\":\"$rsync_options\""
    
    # Commande rsync avec statistiques détaillées
    local rsync_cmd="rsync --stats --human-readable --progress --verbose $rsync_options \"$source\" \"$destination\""
    
    # Exécution de rsync
    local exit_code=0
    local status="success"
    local error_message=""
    
    if eval "$rsync_cmd" > "$output_file" 2>&1; then
        exit_code=$?
        if [ $exit_code -eq 0 ]; then
            status="success"
            log_structured "INFO" "$job_name" "Job completed successfully" ",\"exit_code\":$exit_code"
        else
            status="warning"
            log_structured "WARN" "$job_name" "Job completed with warnings" ",\"exit_code\":$exit_code"
        fi
    else
        exit_code=$?
        status="error"
        error_message=$(tail -5 "$output_file" | tr '\n' ' ' | sed 's/"/\\"/g')
        log_structured "ERROR" "$job_name" "Job failed" ",\"exit_code\":$exit_code,\"error\":\"$error_message\""
    fi
    
    local end_time=$(date '+%Y-%m-%dT%H:%M:%S.%3NZ')
    local end_timestamp=$(date +%s)
    local duration=$((end_timestamp - start_timestamp))
    
    # Parser les statistiques
    local stats=($(parse_rsync_stats "$output_file"))
    local bytes_transferred=${stats[0]:-0}
    local files_transferred=${stats[1]:-0}
    local files_deleted=${stats[2]:-0}
    
    # Log final structuré
    log_structured "INFO" "$job_name" "Job statistics" ",\"duration_seconds\":$duration,\"bytes_transferred\":$bytes_transferred,\"files_transferred\":$files_transferred,\"files_deleted\":$files_deleted,\"status\":\"$status\""
    
    # Exposer les métriques pour Prometheus
    expose_metrics "$job_name" "$status" "$duration" "$bytes_transferred" "$files_transferred" "$exit_code"
    
    # Nettoyer les fichiers temporaires
    rm -f "$output_file"
    
    return $exit_code
}

# Fonction d'aide
usage() {
    echo "Usage: $0 <job_name> <source> <destination> [rsync_options...]"
    echo ""
    echo "Exemples:"
    echo "  $0 backup_docs /home/user/docs /backup/docs -av --delete"
    echo "  $0 sync_photos /photos user@remote:/backup/photos -avz --progress"
    exit 1
}

# Script principal
main() {
    if [ $# -lt 3 ]; then
        usage
    fi
    
    local job_name="$1"
    local source="$2"
    local destination="$3"
    shift 3
    local rsync_options="$*"
    
    # Validation des paramètres
    if [[ ! "$job_name" =~ ^[a-zA-Z0-9_-]+$ ]]; then
        echo "Erreur: Le nom du job ne doit contenir que des lettres, chiffres, _ et -"
        exit 1
    fi
    
    run_rsync "$job_name" "$source" "$destination" $rsync_options
}

# Gestion des signaux
trap 'log_structured "WARN" "system" "Script interrupted" ""; exit 130' INT TERM

# Exécution
main "$@"
