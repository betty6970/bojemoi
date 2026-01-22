#!/bin/bash
set -euo pipefail

# Configuration
GITLAB_URL="https://gitlab.bojemoi.lab"
GITLAB_TOKEN="votre_token"
PROJECT_NAME="bojemoi"
GROUP_NAME="groupe"

echo "🤖 Automatisation complete du deploiement"

# 1. Creer le projet GitLab
echo "📝 Creation du projet GitLab..."
PROJECT_RESPONSE=$(curl -s --request POST \
  --header "PRIVATE-TOKEN: ${GITLAB_TOKEN}" \
  "${GITLAB_URL}/api/v4/projects" \
  --form "name=${PROJECT_NAME}" \
  --form "namespace_id=$(curl -s --header "PRIVATE-TOKEN: ${GITLAB_TOKEN}" \
    "${GITLAB_URL}/api/v4/groups/${GROUP_NAME}" | jq -r '.id')" \
  --form "visibility=private")

PROJECT_ID=$(echo "$PROJECT_RESPONSE" | jq -r '.id')
echo "✅ Projet créé: ID ${PROJECT_ID}"

# 2. Configurer les variables CI/CD
echo "🔐 Configuration des variables..."
variables=(
  "CI_REGISTRY_USER:gitlab-ci-token:true:false"
  "CI_REGISTRY_PASSWORD:${CI_REGISTRY_PASSWORD}:true:true"
  "PRODUCTION_DATABASE_URL:${PROD_DB_URL}:true:true"
  "PRODUCTION_REDIS_URL:${PROD_REDIS_URL}:true:false"
)

for var in "${variables[@]}"; do
  IFS=':' read -r key value masked protected <<< "$var"
  curl -s --request POST \
    --header "PRIVATE-TOKEN: ${GITLAB_TOKEN}" \
    "${GITLAB_URL}/api/v4/projects/${PROJECT_ID}/variables" \
    --form "key=${key}" \
    --form "value=${value}" \
    --form "masked=${masked}" \
    --form "protected=${protected}" > /dev/null
done
echo "✅ Variables configurées"

# 3. Initialiser le repository
echo "📦 Initialisation du repository..."
git init
git remote add origin "${GITLAB_URL}/${GROUP_NAME}/${PROJECT_NAME}.git"
git add .
git commit -m "Initial commit with automated deployment"
git push -u origin main

echo "✅ Déploiement automatisé configuré!"
echo "🌐 Projet: ${GITLAB_URL}/${GROUP_NAME}/${PROJECT_NAME}"

