# Bojemoi Orchestrator

Container orchestrateur pour le déploiement automatisé de VMs et containers dans l'infrastructure Bojemoi Lab.

## Architecture

```
Lightsail (Gitea) → Orchestrator → XenServer (VMs)
                                 → Docker Swarm (Containers)
```

## Fonctionnalités

- ✅ Déploiement de VMs sur XenServer avec cloud-init
- ✅ Déploiement de services sur Docker Swarm
- ✅ Récupération des configurations depuis Gitea
- ✅ Génération dynamique de cloud-init
- ✅ Logging PostgreSQL
- ✅ API REST FastAPI

## Prérequis

- Docker et Docker Compose
- Accès à Gitea (token API)
- Accès à XenServer
- PostgreSQL

## Structure du projet

```
bojemoi-orchestrator/
├── README.md
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py
│   └── services/
│       ├── __init__.py
│       ├── gitea_client.py
│       ├── xenserver_client.py
│       ├── docker_client.py
│       ├── cloudinit_gen.py
│       └── database.py
└── scripts/
    ├── init_db.sql
    └── test_deploy.sh
```

## Installation

1. Cloner et configurer :
```bash
tar xzf bojemoi-orchestrator.tar.gz
cd bojemoi-orchestrator
cp .env.example .env
# Éditer .env avec vos paramètres
```

2. Construire et lancer :
```bash
docker-compose up -d --build
```

3. Vérifier le health :
```bash
curl http://localhost:8000/health
```

## Configuration (.env)

Copier `.env.example` vers `.env` et configurer :

- `GITEA_URL` : URL de votre serveur Gitea
- `GITEA_TOKEN` : Token API Gitea
- `XENSERVER_URL` : URL du serveur XenServer
- `XENSERVER_USER` : Utilisateur XenServer
- `XENSERVER_PASS` : Mot de passe XenServer
- `DATABASE_URL` : URL PostgreSQL

## Utilisation

### Déployer une VM

```bash
curl -X POST http://localhost:8000/api/v1/vm/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "name": "web-prod-01",
    "template": "webserver",
    "os_type": "alpine",
    "cpu": 4,
    "memory": 4096,
    "disk": 20,
    "environment": "production"
  }'
```

### Déployer un container

```bash
curl -X POST http://localhost:8000/api/v1/container/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nginx-proxy",
    "image": "nginx:alpine",
    "replicas": 2,
    "ports": ["80:80", "443:443"],
    "networks": ["bojemoi-net"]
  }'
```

### Lister les déploiements

```bash
curl http://localhost:8000/api/v1/deployments
```

## Structure Gitea attendue

```
bojemoi-configs/
├── cloud-init/
│   ├── alpine/
│   │   ├── webserver.yaml
│   │   └── database.yaml
│   ├── ubuntu/
│   │   └── default.yaml
│   └── debian/
│       └── default.yaml
└── templates/
    └── vm-defaults.yaml
```

## API Endpoints

- `POST /api/v1/vm/deploy` - Déployer une VM
- `POST /api/v1/container/deploy` - Déployer un container
- `GET /api/v1/deployments` - Lister les déploiements
- `GET /api/v1/deployments/{id}` - Détails d'un déploiement
- `DELETE /api/v1/deployments/{id}` - Supprimer un déploiement
- `GET /health` - Health check

## Logs

Les logs sont disponibles via :
```bash
docker-compose logs -f orchestrator
```

## Troubleshooting

### L'orchestrator ne peut pas se connecter à Gitea
- Vérifier le token Gitea
- Vérifier la connectivité réseau

### Erreur de connexion XenServer
- Vérifier les credentials
- Vérifier que le réseau permet la connexion à XenAPI

### Erreur Docker Swarm
- Vérifier que le socket Docker est monté
- Vérifier que Swarm est initialisé

## Développement

Pour développer localement :

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer en mode dev
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## License

Projet interne Bojemoi Lab
