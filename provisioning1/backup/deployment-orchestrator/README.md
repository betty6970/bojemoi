# Deployment Orchestrator - Bojemoi Lab

Orchestrateur de déploiement automatique pour VMs XenServer et containers Docker via Gitea webhooks.

## 🎯 Fonctionnalités

- ✅ Déploiement automatique de VMs XenServer
- ✅ Déploiement de containers Docker standalone
- ✅ Déploiement de services Docker Swarm
- ✅ Intégration avec Gitea (webhooks)
- ✅ Configuration cloud-init pour VMs
- ✅ Traçabilité complète dans PostgreSQL
- ✅ Métriques Prometheus
- ✅ API REST pour gestion et monitoring
- ✅ Support multi-environnement (prod/staging/dev)

## 🏗️ Architecture

```
┌─────────────┐
│   Gitea     │  Push → Webhook
└──────┬──────┘
       │
       ▼
┌─────────────────────────────┐
│  Deployment Orchestrator    │
│  ┌────────────────────────┐ │
│  │  FastAPI Webhook       │ │
│  │  Endpoint              │ │
│  └───────┬────────────────┘ │
│          │                   │
│          ▼                   │
│  ┌────────────────────────┐ │
│  │  Orchestration Logic   │ │
│  └───┬──────────────┬─────┘ │
│      │              │        │
│      ▼              ▼        │
│  ┌────────┐    ┌─────────┐  │
│  │XenAPI  │    │ Docker  │  │
│  └────────┘    └─────────┘  │
└─────────────────────────────┘
       │
       ▼
┌─────────────┐
│ PostgreSQL  │  Logs + État
└─────────────┘
```

## 📋 Prérequis

- Docker et Docker Compose
- Accès à un serveur Gitea
- Accès à XenServer (pour déploiement VMs)
- PostgreSQL (inclus dans docker-compose)
- Python 3.11+ (pour développement)

## 🚀 Installation

### 1. Cloner le projet

```bash
git clone https://gitea.bojemoi.lab/infra/deployment-orchestrator.git
cd deployment-orchestrator
```

### 2. Configuration

Copier et configurer le fichier d'environnement :

```bash
cp .env.example .env
```

Éditer `.env` avec vos paramètres :

```bash
# Gitea
GITEA_URL=https://gitea.bojemoi.lab
GITEA_TOKEN=your_token_here
GITEA_WEBHOOK_SECRET=your_secret_here

# PostgreSQL
POSTGRES_PASSWORD=secure_password_here

# XenServer
XENSERVER_URL=https://xenserver.bojemoi.lab
XENSERVER_PASSWORD=xenserver_password_here
```

### 3. Démarrer le service

```bash
docker-compose up -d
```

### 4. Vérifier le statut

```bash
# Vérifier les logs
docker-compose logs -f orchestrator

# Tester le health check
curl http://localhost:8080/health
```

## 🔧 Configuration Gitea

### Créer un webhook

1. Aller dans votre dépôt Gitea
2. Settings → Webhooks → Add Webhook → Gitea
3. Configurer :
   - **URL** : `http://orchestrator.bojemoi.lab:8080/webhook/gitea`
   - **Secret** : Votre `GITEA_WEBHOOK_SECRET`
   - **Content Type** : `application/json`
   - **Trigger On** : Push events
   - **Active** : ✅

### Créer un token d'accès

1. User Settings → Applications → Generate New Token
2. Copier le token dans `GITEA_TOKEN`

## 📦 Structure des dépôts Gitea

Organisez vos dépôts comme suit :

```
infra-configs/
├── deployments/
│   ├── manifest.yaml              # Manifeste principal
│   ├── production/
│   │   └── manifest.yaml
│   └── staging/
│       └── manifest.yaml
├── vms/
│   ├── webserver.yaml
│   └── database.yaml
├── containers/
│   ├── api-backend.yaml
│   └── frontend.yaml
└── cloud-init/
    ├── webserver/
    │   └── user-data.yaml
    └── database/
        └── user-data.yaml
```

## 📝 Manifestes de déploiement

### Exemple VM

```yaml
version: "1.0"
deployment_type: vm
environment: production

vm_config:
  name: "web-prod-01"
  template: "Ubuntu-22.04-Template"
  vcpus: 4
  memory_mb: 8192
  disk_gb: 50
  cloud_init_role: "webserver"
  
  tags:
    environment: "production"
    role: "webserver"
```

### Exemple Container

```yaml
version: "1.0"
deployment_type: container
environment: staging

container_config:
  name: "api-staging"
  image: "registry.bojemoi.lab/api"
  tag: "staging-latest"
  
  env_vars:
    NODE_ENV: "staging"
  
  ports:
    - "3000:3000"
  
  restart_policy: "unless-stopped"
```

### Exemple Swarm Service

```yaml
version: "1.0"
deployment_type: swarm_service
environment: production

swarm_config:
  name: "frontend-prod"
  image: "registry.bojemoi.lab/frontend"
  tag: "v2.4.1"
  replicas: 3
  
  ports:
    - "80:8080"
  
  update_config:
    parallelism: 1
    delay: 30
    failure_action: "rollback"
```

## 🔍 API Endpoints

### Health Check
```bash
GET /health
```

### Webhook Gitea
```bash
POST /webhook/gitea
```

### Lister les déploiements
```bash
GET /deployments?limit=50&status=completed&environment=production
```

### Détails d'un déploiement
```bash
GET /deployments/{deployment_id}
```

### Métriques Prometheus
```bash
GET /metrics
```

## 📊 Monitoring

### Prometheus

Ajouter au `prometheus.yml` :

```yaml
scrape_configs:
  - job_name: 'deployment-orchestrator'
    static_configs:
      - targets: ['orchestrator.bojemoi.lab:9090']
```

### Grafana

Métriques disponibles :
- `webhook_received_total` - Total des webhooks reçus
- `deployments_total` - Total des déploiements par type/statut
- `deployment_duration_seconds` - Durée des déploiements

## 🔒 Sécurité

- Les webhooks sont vérifiés via HMAC-SHA256
- Les secrets sont stockés dans des variables d'environnement
- Les connexions DB utilisent des mots de passe sécurisés
- L'accès XenServer nécessite authentification

## 🐛 Debug

### Voir les logs détaillés

```bash
docker-compose logs -f orchestrator
```

### Accéder au container

```bash
docker-compose exec orchestrator bash
```

### Vérifier la DB

```bash
docker-compose exec postgres psql -U deployment_user -d deployments
```

Requêtes utiles :

```sql
-- Voir les déploiements récents
SELECT id, name, status, environment, created_at 
FROM deployments 
ORDER BY created_at DESC 
LIMIT 10;

-- Voir les logs d'un déploiement
SELECT * FROM deployment_logs 
WHERE deployment_id = 1 
ORDER BY timestamp;
```

## 🔄 Workflow GitOps

1. Développeur pousse un commit dans Gitea
2. Gitea envoie un webhook à l'orchestrateur
3. L'orchestrateur détecte les changements de manifeste
4. Déploiement automatique selon le type
5. Mise à jour du statut dans la DB
6. Notification du commit status dans Gitea

## 📚 Documentation complémentaire

- [Gitea API](https://docs.gitea.io/en-us/api-usage/)
- [XenServer API](https://docs.citrix.com/en-us/citrix-hypervisor/developer/management-api.html)
- [Docker SDK Python](https://docker-py.readthedocs.io/)
- [Cloud-init](https://cloudinit.readthedocs.io/)

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature
3. Commit les changements
4. Push vers la branche
5. Créer une Pull Request

## 📄 Licence

MIT License - Bojemoi Lab 2024

## ✨ Auteur

Betty - Bojemoi Lab Infrastructure Team
