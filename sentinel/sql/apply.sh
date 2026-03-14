#!/bin/sh
# Bojemoi Lab — Sentinel
# Applique les scripts SQL sur le postgres du Swarm (base stack)
# Usage: ./apply.sh [PG_PASSWORD]
set -e

PG_PASS="${1:-}"

POSTGRES_CTR=$(docker ps -q --filter "name=base_postgres" | head -1)

if [ -z "$POSTGRES_CTR" ]; then
    echo "ERREUR : conteneur base_postgres introuvable"
    exit 1
fi

if [ -z "$PG_PASS" ]; then
    printf "Mot de passe PostgreSQL pour l'utilisateur sentinel : "
    read -s PG_PASS
    echo ""
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== 01-init-db : création DB + user ==="
docker exec -i "$POSTGRES_CTR" psql -U postgres \
    < "$SCRIPT_DIR/01-init-db.sql"

echo "=== Mise à jour password sentinel ==="
docker exec -i "$POSTGRES_CTR" psql -U postgres \
    -c "ALTER USER sentinel WITH ENCRYPTED PASSWORD '$PG_PASS';"

echo "=== 02-tables : création des tables ==="
docker exec -i "$POSTGRES_CTR" psql -U postgres \
    < "$SCRIPT_DIR/02-tables.sql"

echo "=== 03-grants : grants utilisateur ==="
docker exec -i "$POSTGRES_CTR" psql -U postgres \
    < "$SCRIPT_DIR/03-grants.sql"

echo ""
echo "=== Vérification ==="
docker exec -i "$POSTGRES_CTR" psql -U postgres -d sentinel -c "\dt"

echo ""
echo "Setup sentinel DB terminé."
