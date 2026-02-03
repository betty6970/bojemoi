# Docker Swarm

Gestion du cluster Docker Swarm Bojemoi Lab.

## Cluster

| Node | Role | IP |
|------|------|-----|
| meta-76 | Manager | - |
| meta-70 | Worker | - |
| meta-68 | Worker | - |

## Stacks

| Stack | Fichier | Description |
|-------|---------|-------------|
| base | `01-service-hl.yml` | Infrastructure (monitoring, proxy, DB) |
| borodino | `40-service-borodino.yml` | Outils pentest |

## Commandes Claude Code

```bash
/swarm status              # Vue d'ensemble
/swarm nodes               # Statut des nodes
/swarm deploy base         # Déployer stack base
/swarm scale service 3     # Scaler un service
/swarm logs service        # Voir les logs
```

## Commandes Docker

### Cluster
```bash
# Voir les nodes
docker node ls

# Infos sur un node
docker node inspect meta-76 --pretty

# Promouvoir un worker en manager
docker node promote meta-70

# Drainer un node (maintenance)
docker node update --availability drain meta-68

# Réactiver un node
docker node update --availability active meta-68
```

### Stacks
```bash
# Lister les stacks
docker stack ls

# Déployer un stack
docker stack deploy -c /opt/bojemoi/stack/01-service-hl.yml base --prune

# Supprimer un stack
docker stack rm base

# Services d'un stack
docker stack services base

# Tâches d'un stack
docker stack ps base
```

### Services
```bash
# Lister les services
docker service ls

# Détails d'un service
docker service inspect base_prometheus --pretty

# Logs d'un service
docker service logs base_prometheus --tail 100 -f

# Scaler un service
docker service scale base_prometheus=2

# Mettre à jour un service
docker service update base_prometheus --image localhost:5000/prometheus:latest

# Forcer le redéploiement
docker service update base_prometheus --force
```

### Conteneurs
```bash
# Voir les conteneurs sur un node
docker ps

# Stats en temps réel
docker stats

# Exec dans un conteneur
docker exec -it <container_id> sh
```

## Réseaux

| Réseau | Type | Usage |
|--------|------|-------|
| monitoring | overlay | Prometheus, Grafana, exporters |
| backend | overlay | Services internes, DB |
| proxy | overlay | Traefik, services exposés |
| mail | overlay | Postfix, ProtonMail bridge |
| rsync_network | overlay | Backup rsync |

```bash
# Lister les réseaux
docker network ls

# Inspecter un réseau
docker network inspect monitoring
```

## Volumes

| Volume | Usage |
|--------|-------|
| prometheus_data | Données TSDB Prometheus |
| grafana_data | Dashboards Grafana |
| postgres_data (bojemoi) | Base PostgreSQL |
| loki_data | Logs Loki |
| registry | Images Docker registry |

```bash
# Lister les volumes
docker volume ls

# Inspecter un volume
docker volume inspect prometheus_data
```

## Déploiement

### Déployer le stack base
```bash
docker stack deploy -c /opt/bojemoi/stack/01-service-hl.yml base --prune --resolve-image always
```

### Déployer le stack borodino
```bash
docker stack deploy -c /opt/bojemoi/stack/40-service-borodino.yml borodino --prune
```

### Mettre à jour un service
```bash
# Avec nouvelle image
docker service update base_prometheus --image localhost:5000/prometheus:latest

# Avec nouveau mount
docker service update base_prometheus --mount-add type=bind,source=/path,target=/path

# Avec nouvelles variables
docker service update base_prometheus --env-add NEW_VAR=value
```

## Secrets et Configs

```bash
# Lister les secrets
docker secret ls

# Créer un secret
echo "password" | docker secret create my_secret -

# Lister les configs
docker config ls

# Créer une config
docker config create my_config /path/to/file
```

## Dépannage

### Service ne démarre pas
```bash
# Voir les tâches échouées
docker service ps base_prometheus --no-trunc

# Logs détaillés
docker service logs base_prometheus --tail 100

# Inspecter la tâche
docker inspect <task_id>
```

### Problème de réseau
```bash
# Vérifier la connectivité
docker exec <container> ping <service_name>

# DNS interne
docker exec <container> nslookup prometheus
```

### Problème de config
```bash
# Erreur "config already exists"
# Supprimer l'ancienne config avant redéploiement
docker config rm base_prometheus_config

# Ou mettre à jour le service sans la config
docker service update base_prometheus --config-rm old_config
```

## Labels

### Prometheus scraping
```yaml
labels:
  - prometheus.enable=true
  - prometheus.port=9090
  - prometheus.path=/metrics
```

### Traefik routing
```yaml
labels:
  - traefik.enable=true
  - traefik.http.routers.myservice.rule=Host(`myservice.bojemoi.lab`)
  - traefik.http.services.myservice.loadbalancer.server.port=8080
```

### Placement
```yaml
deploy:
  placement:
    constraints:
      - node.role == manager
      - node.labels.type == worker
```
