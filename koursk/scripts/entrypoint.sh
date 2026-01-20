#!/bin/bash
set -e

# Configuration SSH si clés présentes
if [ -f /root/.ssh/id_rsa ]; then
    chmod 600 /root/.ssh/id_rsa
    chmod 644 /root/.ssh/id_rsa.pub 2>/dev/null || true
fi

# Création des répertoires de logs
mkdir -p /var/log/rsync
touch /var/log/rsync/rsync-${RSYNC_MODE}.log

# Attendre que les services réseau soient prêts
sleep 5

# Exécution de la commande principale
exec "$@"
