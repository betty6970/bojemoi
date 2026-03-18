#!/bin/sh
# Crée les catégories et salons Discord via l'API REST
# Usage: GUILD_ID=xxx BOT_TOKEN=xxx ./create_structure.sh

GUILD_ID="${GUILD_ID:?Manque GUILD_ID}"
BOT_TOKEN="${BOT_TOKEN:?Manque BOT_TOKEN}"
API="https://discord.com/api/v10/guilds/$GUILD_ID/channels"
AUTH="Authorization: Bot $BOT_TOKEN"

create_category() {
  NAME="$1"
  curl -s -X POST "$API" \
    -H "$AUTH" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$NAME\",\"type\":4}" \
    | grep -o '"id":"[^"]*"' | head -1 | cut -d'"' -f4
}

create_channel() {
  NAME="$1"
  PARENT_ID="$2"
  TOPIC="$3"
  curl -s -X POST "$API" \
    -H "$AUTH" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$NAME\",\"type\":0,\"parent_id\":\"$PARENT_ID\",\"topic\":\"$TOPIC\"}" > /dev/null
  echo "  #$NAME"
}

echo "==> Création de la structure Bojemoi Lab"

echo "\n[🏠 Général]"
ID=$(create_category "🏠 Général")
create_channel "annonces"    "$ID" "Actualités officielles du lab, nouvelles features, changements d'infrastructure"
create_channel "règles"      "$ID" "Code de conduite et règles du serveur"
create_channel "général"     "$ID" "Discussion libre autour du projet"
create_channel "off-topic"   "$ID" "Tout ce qui n'a rien à voir avec le lab"

echo "\n[🏗️ Infrastructure]"
ID=$(create_category "🏗️ Infrastructure")
create_channel "architecture" "$ID" "Décisions d'architecture, schémas, discussions sur le design du lab"
create_channel "docker-swarm" "$ID" "Opérations sur le cluster (4 noeuds, stacks, services)"
create_channel "deployments"  "$ID" "Suivi des déploiements en cours et historique"
create_channel "gitops"       "$ID" "Pipelines CI/CD, Gitea Actions, gestion des configs"
create_channel "ci-cd"        "$ID" "Builds, tests, automatisations"

echo "\n[🔬 Intelligence]"
ID=$(create_category "🔬 Intelligence")
create_channel "borodino"     "$ID" "Résultats de scan nmap/fingerprinting, stats ak47/bm12"
create_channel "ml-threat"    "$ID" "Détection de menaces par ML, modèles, datasets"
create_channel "osint"        "$ID" "Enrichissement d'IPs, threat intel, sources ouvertes"
create_channel "mitre-attack" "$ID" "Mapping des TTPs, analyse des comportements détectés"

echo "\n[🔒 Sécurité]"
ID=$(create_category "🔒 Sécurité")
create_channel "monitoring"   "$ID" "Métriques Prometheus, dashboards Grafana, alertes"
create_channel "alertes"      "$ID" "Alertes actives (Prometheus, CrowdSec, Suricata)"
create_channel "security"     "$ID" "Vulnérabilités, patches, posture de sécurité"
create_channel "faraday"      "$ID" "Findings Faraday, rapports de pentest"
create_channel "trivy"        "$ID" "Résultats de scan des images Docker"

echo "\n[📝 Contenu]"
ID=$(create_category "📝 Contenu")
create_channel "blog"         "$ID" "Articles publiés sur blog.bojemoi.me, idées, retours"
create_channel "projets"      "$ID" "Projets en cours, roadmap, brainstorming"
create_channel "ressources"   "$ID" "Liens utiles, docs, outils recommandés"

echo "\nDone."
