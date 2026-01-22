#!/bin/bash
set -euo pipefail

GITLAB_CONTAINER=$(docker ps -q -f name=gitlab_gitlab)
USERNAME=${1:-root}
TOKEN_NAME=${2:-automation-token}

echo "🔑 Création d'un token GitLab pour ${USERNAME}"

TOKEN=$(docker exec -i ${GITLAB_CONTAINER} gitlab-rails runner "
user = User.find_by(username: '${USERNAME}')
if user.nil?
  puts 'ERROR: User not found'
  exit 1
end

token = user.personal_access_tokens.create(
  scopes: [:api, :read_api, :read_repository, :write_repository, :read_registry, :write_registry],
  name: '${TOKEN_NAME}',
  expires_at: 365.days.from_now
)

if token.persisted?
  puts token.token
else
  puts 'ERROR: Token creation failed'
  puts token.errors.full_messages
  exit 1
end
")

if [[ $TOKEN == ERROR* ]]; then
  echo "❌ $TOKEN"
  exit 1
fi

echo "✅ Token créé avec succès:"
echo ""
echo "TOKEN: ${TOKEN}"
echo ""
echo "⚠️  COPIEZ CE TOKEN MAINTENANT - Il ne sera plus visible!"
echo ""
echo "Pour utiliser ce token:"
echo "  export GITLAB_TOKEN='${TOKEN}'"
echo "  curl --header \"PRIVATE-TOKEN: \${GITLAB_TOKEN}\" https://gitlab.bojemoi.lab.local/api/v4/projects"
