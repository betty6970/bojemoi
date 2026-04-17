# Runbook — Déploiement des stacks

## Règle absolue

Les stacks utilisent des Docker secrets et des Docker configs.
**Pas de fichiers `.env` sur le filesystem.**

## Stack `base` (manager)

Le stack `base` utilise des variables d'interpolation obligatoires (`${VAR:?required}`).
Les passer inline au déploiement :

```bash
# Récupérer les valeurs actuelles depuis postgres
PGPASS=$(docker service inspect base_postgres \
  --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{.}}{{"\n"}}{{end}}' \
  | grep POSTGRES_PASSWORD | cut -d= -f2)

POSTGRES_PASSWORD=$PGPASS \
POSTGRES_USER=postgres \
PGADMIN_PASSWORD=<val> \
GRAFANA_ADMIN_PASSWORD=<val> \
  docker stack deploy -c /opt/bojemoi/stack/01-service-hl.yml base \
    --prune --resolve-image always
```

## Stacks workers (ordre recommandé)

```bash
# Scanning + exploitation
docker stack deploy -c stack/40-service-borodino.yml borodino --prune --resolve-image always

# Vuln management
docker stack deploy -c stack/70-service-defectdojo.yml dojo --prune --resolve-image always

# Threat intelligence
docker stack deploy -c stack/45-service-ml-threat-intel.yml ml-threat-intel --prune --resolve-image always
docker stack deploy -c stack/46-service-razvedka.yml razvedka --prune --resolve-image always
docker stack deploy -c stack/47-service-vigie.yml vigie --prune --resolve-image always

# Défensif
docker stack deploy -c stack/48-service-dozor.yml dozor --prune --resolve-image always
docker stack deploy -c stack/55-service-sentinel.yml sentinel --prune --resolve-image always
docker stack deploy -c stack/65-service-medved.yml medved --prune --resolve-image always

# Divers
docker stack deploy -c stack/41-service-nym.yml nym --prune --resolve-image always
docker stack deploy -c stack/49-service-mcp.yml mcp --prune --resolve-image always
docker stack deploy -c stack/51-service-ollama.yml ollama --prune --resolve-image always
docker stack deploy -c stack/60-service-telegram.yml telegram --prune --resolve-image always
```

## Valider la syntaxe avant déploiement

```bash
docker-compose -f stack/<fichier>.yml config --quiet && echo "OK"
```

## Vérifier l'état après déploiement

```bash
docker stack ps <stack> --no-trunc | grep -v "Shutdown"
docker service ls | grep <stack>
```

## Nommage des services (règle DNS)

Utiliser le **nom court** dans les configs inter-services, jamais le nom préfixé :
- ✅ `postgres`, `grafana`, `prometheus`
- ❌ `base_postgres`, `base_grafana`

Le nom préfixé n'existe que dans le CLI Swarm (`docker service ls/logs/inspect`).
