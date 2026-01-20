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
