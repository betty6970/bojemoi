#!/bin/bash

# Attendre que PostgreSQL soit prêt
if [ -n "$ZAP_DB_HOST" ]; then
    echo "Waiting for PostgreSQL at $ZAP_DB_HOST:$ZAP_DB_PORT..."
    until pg_isready -h "$ZAP_DB_HOST" -p "$ZAP_DB_PORT" -U "$ZAP_DB_USER"; do
        echo "PostgreSQL is unavailable - sleeping"
        sleep 2
    done
    echo "PostgreSQL is up - starting ZAP"
fi

# Démarrer ZAP avec les arguments passés
exec /zap/zap.sh "$@"

