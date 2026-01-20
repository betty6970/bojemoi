#!/bin/ash
# setup.sh - Script de déploiement de la solution de monitoring rsync (compatible ash)

set -e

echo "=== Déploiement de la solution de monitoring rsync ==="

# Création de la structure des répertoires (compatible ash)
# Liste des répertoires à créer
DIRECTORIES="
grafana/provisioning/dashboards
grafana/provisioning/datasources
prometheus
rsync-monitor/scripts
rsync-monitor/config
rsync-monitor/data
logs
"

# Boucle de création des répertoires
for dir in $DIRECTORIES; do
    if [ ! -z "$dir" ]; then
        echo "Création du répertoire: $dir"
        mkdir -p "$dir"
    fi
done

# Configuration Prometheus
cat > prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'rsync-monitor'
    static_configs:
      - targets: ['rsync-monitor:8080']
    scrape_interval: 30s
EOF

# Configuration Grafana - DataSource
cat > grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

# Configuration Grafana - Dashboard
cat > grafana/provisioning/dashboards/dashboard.yml << 'EOF'
apiVersion: 1
providers:
  - name: 'rsync-dashboards'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

# Script de démarrage pour le container rsync-monitor
cat > rsync-monitor/scripts/start.sh << 'EOF'
#!/bin/ash
set -e

# Démarrage de cron
crond

# Création des répertoires de logs
mkdir -p /logs

# Démarrage du script de monitoring
python3 /scripts/rsync_monitor.py &

# Maintien du container actif
tail -f /logs/rsync_monitor.log
EOF

# Crontab pour les tâches programmées
cat > rsync-monitor/crontab << 'EOF'
# Exécution des backups rsync
0 2 * * * /scripts/run_backups.sh >> /logs/cron.log 2>&1
EOF

# Script d'exécution des backups
cat > rsync-monitor/scripts/run_backups.sh << 'EOF'
#!/bin/ash
# Script d'exécution des backups rsync programmés

LOGFILE="/logs/backup_$(date +%Y%m%d_%H%M%S).log"

echo "$(date): Début des backups programmés" >> "$LOGFILE"

# Vérification de l'existence du fichier de configuration
if [ ! -f "/config/rsync_jobs.json" ]; then
    echo "$(date): Fichier de configuration non trouvé" >> "$LOGFILE"
    exit 1
fi

# Lecture de la configuration JSON et exécution des jobs
python3 -c "
import json
import subprocess
import sys
from datetime import datetime

try:
    with open('/config/rsync_jobs.json', 'r') as f:
        jobs = json.load(f)
    
    for job in jobs:
        print(f'Exécution du job: {job[\"name\"]}')
        cmd = f'rsync {job.get(\"options\", \"-av\")} --stats {job[\"source\"]} {job[\"destination\"]}'
        
        result = subprocess.run(cmd.split(), capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f'✓ Job {job[\"name\"]} réussi')
        else:
            print(f'✗ Job {job[\"name\"]} échoué: {result.stderr}')
            
except Exception as e:
    print(f'Erreur: {e}')
    sys.exit(1)
" >> "$LOGFILE" 2>&1

echo "$(date): Fin des backups programmés" >> "$LOGFILE"
EOF

# Configuration par défaut des jobs rsync
cat > rsync-monitor/config/rsync_jobs.json << 'EOF'
[
  {
    "name": "backup_data",
    "source": "/data/source/",
    "destination": "/data/backup/",
    "options": "-av --delete --stats",
    "description": "Sauvegarde quotidienne des données"
  },
  {
    "name": "sync_configs",
    "source": "/config/",
    "destination": "/data/backup/configs/",
    "options": "-av --stats",
    "description": "Synchronisation des configurations"
  }
]
EOF

# Dockerfile pour rsync-monitor
cat > rsync-monitor/Dockerfile << 'EOF'
FROM alpine:latest

RUN apk add --no-cache \
    python3 \
    py3-pip \
    rsync \
    dcron \
    && pip3 install --no-cache-dir prometheus_client psutil

# Création des répertoires nécessaires
RUN for dir in /scripts /config /data /logs; do \
        mkdir -p "$dir"; \
    done

COPY scripts/ /scripts/
COPY config/ /config/
COPY crontab /var/spool/cron/crontabs/root

# Application des permissions en une seule couche
RUN find /scripts -name "*.sh" -exec chmod +x {} \; && \
    chmod 0600 /var/spool/cron/crontabs/root

EXPOSE 8080

CMD ["/scripts/start.sh"]
EOF

# Rendre les scripts exécutables
chmod +x rsync-monitor/scripts/*.sh

echo "=== Structure créée avec succès ==="
echo ""
echo "Pour démarrer la solution:"
echo "1. docker-compose up -d"
echo "2. Accéder à Grafana: http://localhost:3000 (admin/admin)"
echo "3. Accéder à Prometheus: http://localhost:9090"
echo ""
echo "Configuration:"
echo "- Modifiez rsync-monitor/config/rsync_jobs.json pour vos jobs"
echo "- Les logs sont dans le volume rsync-monitor/data/"
echo "- Dashboard Grafana auto-provisionné"
