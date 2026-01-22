#!/bin/bash
set -euo pipefail

STACK_NAME=$1
MAX_RETRIES=30
RETRY_INTERVAL=2

echo "💚 Health check de ${STACK_NAME}"

# Déterminer l'URL de l'application
APP_URL="https://${STACK_NAME}.bojemoi.lab.local/health"

for i in $(seq 1 $MAX_RETRIES); do
    echo "Tentative $i/$MAX_RETRIES..."
    
    if curl -f -s -o /dev/null ${APP_URL}; then
        echo "✅ Health check OK"
        
        # Vérifier les métriques
        curl -s http://prometheus.bojemoi.lab.local/api/v1/query?query=up{job=\"${STACK_NAME}\"} | jq .
        
        exit 0
    fi
    
    sleep $RETRY_INTERVAL
done

echo "❌ Health check échoué après $MAX_RETRIES tentatives"
exit 1

