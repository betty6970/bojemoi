# Guide de Déploiement Docker Swarm

## 🐳 Prérequis

1. **Docker Swarm initialisé**
```bash
# Si pas encore fait, initialiser le Swarm
docker swarm init --advertise-addr <IP_DU_MANAGER>
```

2. **Réseau overlay** (sera créé automatiquement par le script)
```bash
docker network create --driver overlay --attachable bojemoi_network
```

3. **Registry Docker** (optionnel mais recommandé)
```bash
# Si vous utilisez une registry privée
# Assurez-vous que registry.bojemoi.lab est accessible
```

## 🚀 Déploiement

### Option 1: Script automatique (recommandé)

```bash
# Rendre le script exécutable
chmod +x deploy-swarm.sh

# Lancer le déploiement
./deploy-swarm.sh
```

### Option 2: Déploiement manuel

```bash
# 1. Créer le réseau overlay
docker network create --driver overlay --attachable bojemoi_network

# 2. Labelliser le node pour PostgreSQL
CURRENT_NODE=$(docker node ls --filter "role=manager" --format "{{.Hostname}}" | head -n 1)
docker node update --label-add postgres=true $CURRENT_NODE

# 3. Build et push l'image (si nécessaire)
docker build -t registry.bojemoi.lab/deployment-orchestrator:latest .
docker push registry.bojemoi.lab/deployment-orchestrator:latest

# 4. Déployer le stack
docker stack deploy \
    --compose-file docker-compose.swarm.yml \
    --with-registry-auth \
    deployment-orchestrator
```

## 📊 Vérification

```bash
# Voir les services
docker stack services deployment-orchestrator

# Voir les tâches/containers
docker stack ps deployment-orchestrator

# Logs de l'orchestrator
docker service logs -f deployment-orchestrator_orchestrator

# Logs de PostgreSQL
docker service logs -f deployment-orchestrator_postgres

# Health check
curl http://localhost:8080/health
```

## 🔄 Mise à jour

### Mise à jour de l'image

```bash
# Build nouvelle version
docker build -t registry.bojemoi.lab/deployment-orchestrator:v1.1.0 .
docker push registry.bojemoi.lab/deployment-orchestrator:v1.1.0

# Update du service (rolling update automatique)
docker service update \
    --image registry.bojemoi.lab/deployment-orchestrator:v1.1.0 \
    deployment-orchestrator_orchestrator
```

### Mise à jour de la configuration

```bash
# Modifier .env
nano .env

# Redéployer le stack (préserve les volumes)
docker stack deploy \
    --compose-file docker-compose.swarm.yml \
    --with-registry-auth \
    deployment-orchestrator
```

## 📈 Scaling

```bash
# Scaler l'orchestrator (si besoin de plusieurs réplicas)
docker service scale deployment-orchestrator_orchestrator=2

# Note: PostgreSQL doit rester à 1 réplica
```

## 🔧 Configuration Swarm Spécifique

### Contraintes de placement

Dans `docker-compose.swarm.yml`, l'orchestrator **doit** être sur un **manager node** pour accéder au socket Docker et gérer le Swarm :

```yaml
deploy:
  placement:
    constraints:
      - node.role == manager
```

PostgreSQL est placé sur un node spécifique via un label pour garantir la persistance des données :

```yaml
deploy:
  placement:
    constraints:
      - node.labels.postgres == true
```

### Volumes

Les volumes sont créés automatiquement par Swarm :
- `postgres_data` : Données PostgreSQL (persistantes)
- `orchestrator_logs` : Logs de l'application
- `orchestrator_cache` : Cache temporaire

### Réseau

Le réseau `bojemoi_network` doit être de type **overlay** et **attachable** pour permettre la communication inter-services et l'attachement de containers externes.

## 🔒 Secrets Swarm (Optionnel mais recommandé)

Pour une sécurité accrue, utilisez les secrets Docker Swarm :

```bash
# Créer les secrets
echo "your_gitea_token" | docker secret create gitea_token -
echo "your_postgres_password" | docker secret create postgres_password -
echo "your_xenserver_password" | docker secret create xenserver_password -

# Modifier docker-compose.swarm.yml pour utiliser les secrets
# (nécessite adaptation du code pour lire depuis /run/secrets/)
```

## 🗑️ Suppression

```bash
# Supprimer le stack (préserve les volumes)
docker stack rm deployment-orchestrator

# Supprimer aussi les volumes (ATTENTION: perte de données!)
docker volume rm deployment-orchestrator_postgres_data
docker volume rm deployment-orchestrator_orchestrator_logs
docker volume rm deployment-orchestrator_orchestrator_cache

# Supprimer le réseau (si plus utilisé)
docker network rm bojemoi_network
```

## 🐛 Troubleshooting Swarm

### Service ne démarre pas

```bash
# Voir les détails de l'erreur
docker service ps deployment-orchestrator_orchestrator --no-trunc

# Inspecter le service
docker service inspect deployment-orchestrator_orchestrator
```

### Problème de réseau

```bash
# Vérifier que le réseau overlay existe
docker network ls | grep overlay

# Inspecter le réseau
docker network inspect bojemoi_network
```

### Image non trouvée

```bash
# Vérifier l'accès à la registry
docker pull registry.bojemoi.lab/deployment-orchestrator:latest

# Si problème d'authentification
docker login registry.bojemoi.lab
```

### PostgreSQL ne démarre pas

```bash
# Vérifier le label du node
docker node inspect <NODE_NAME> | grep postgres

# Vérifier les volumes
docker volume ls | grep postgres
docker volume inspect deployment-orchestrator_postgres_data
```

## 📝 Configuration multi-nodes

Si vous avez plusieurs nodes dans votre Swarm :

```bash
# Sur le manager, voir les nodes
docker node ls

# Labelliser des nodes spécifiques
docker node update --label-add region=eu-west node1
docker node update --label-add region=us-east node2

# Adapter les contraintes dans docker-compose.swarm.yml
```

## 🔐 Bonnes pratiques Swarm

1. **Toujours déployer sur un manager** pour l'orchestrator (accès socket Docker)
2. **Utiliser les secrets** pour les mots de passe sensibles
3. **Labelliser les nodes** pour un placement précis des services
4. **Configurer le monitoring** (Prometheus + Grafana)
5. **Tester les rolling updates** avant la production
6. **Sauvegarder PostgreSQL** régulièrement
7. **Utiliser une registry** pour les images (pas de build local)

## 🎯 Architecture de production recommandée

```
┌─────────────────────────────────────────┐
│         Docker Swarm Cluster            │
│                                         │
│  Manager Node 1 (Leader)                │
│  ├─ orchestrator (replica 1)            │
│  └─ postgres (avec label)               │
│                                         │
│  Manager Node 2 (Reachable)             │
│  └─ (backup/failover)                   │
│                                         │
│  Worker Node 1                          │
│  ├─ containers déployés par orchestrator│
│  └─ services applicatifs                │
│                                         │
│  Worker Node 2                          │
│  └─ services applicatifs                │
└─────────────────────────────────────────┘
```

## 📚 Références

- [Docker Swarm Documentation](https://docs.docker.com/engine/swarm/)
- [Docker Stack Deploy](https://docs.docker.com/engine/reference/commandline/stack_deploy/)
- [Docker Secrets](https://docs.docker.com/engine/swarm/secrets/)
