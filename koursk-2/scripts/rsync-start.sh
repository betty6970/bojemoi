#!/bin/ash
set -e



# Démarrage du script de monitoring
python3 /scripts/rsync-master.pyc &

# Maintien du container actif
sleep 10
tail -f /var/log/rsync/rsync-master.log
