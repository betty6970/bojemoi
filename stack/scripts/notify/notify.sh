#!/bin/bash
set -euo pipefail

TARGET=$1

case $TARGET in
    grafana)
        # Annotation Grafana
        curl -X POST http://grafana.bojemoi.lab.local/api/annotations \
            -H "Authorization: Bearer ${GRAFANA_API_KEY}" \
            -H "Content-Type: application/json" \
            -d '{
                "dashboardId": null,
                "time": '$(date +%s000)',
                "tags": ["deployment", "'"${STACK_NAME}"'", "'"${CI_ENVIRONMENT_NAME}"'"],
                "text": "Déploiement '"${STACK_NAME}"' - '"${CI_COMMIT_SHORT_SHA}"'\nBranche: '"${CI_COMMIT_BRANCH}"'\nAuteur: '"${GITLAB_USER_NAME}"'"
            }'
        ;;
    
    team)
        # Notification équipe (Slack, email, etc.)
        echo "Déploiement ${STACK_NAME} terminé"
        # Ajouter votre logique de notification
        ;;
esac

