#!/bin/bash
set -e

# Copier la clé SSL depuis le secret Docker avec les bonnes permissions
# (le secret est root:root 0400 — postgres a besoin de 0600 propriétaire postgres)
if [ -f /run/secrets/postgres_ssl_key ]; then
    mkdir -p /var/lib/postgresql/ssl
    cp /run/secrets/postgres_ssl_key /var/lib/postgresql/ssl/server.key
    chown postgres:postgres /var/lib/postgresql/ssl/server.key
    chmod 600 /var/lib/postgresql/ssl/server.key
    echo "[SSL] clé privée copiée → /var/lib/postgresql/ssl/server.key"
fi

exec docker-entrypoint.sh "$@"
