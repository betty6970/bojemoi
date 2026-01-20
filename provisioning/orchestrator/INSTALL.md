# Installation Bojemoi Orchestrator

## Prérequis

- Docker et Docker Compose installés
- Accès à votre serveur Gitea (avec token API)
- Accès à XenServer/XCP-ng
- PostgreSQL (fourni dans le docker-compose)

## Installation rapide

### 1. Extraire l'archive

```bash
tar xzf bojemoi-orchestrator.tar.gz
cd bojemoi-orchestrator
```

### 2. Configuration

Copier le fichier d'exemple et le configurer:

```bash
cp .env.example .env
nano .env
```

Configurer les variables suivantes:

```bash
# Gitea
GITEA_URL=https://gitea.bojemoi.me
GITEA_TOKEN=votre_token_gitea
GITEA_REPO=bojemoi-configs

# XenServer
XENSERVER_URL=https://votre-xenserver.local
XENSERVER_USER=root
XENSERVER_PASS=votre_mot_de_passe

# PostgreSQL
POSTGRES_PASSWORD=un_mot_de_passe_securise
```

### 3. Préparer Gitea

Créer le repository `bojemoi-configs` dans Gitea avec la structure suivante:

```
bojemoi-configs/
├── cloud-init/
│   ├── alpine/
│   │   └── webserver.yaml
│   ├── ubuntu/
│   │   └── default.yaml
│   └── debian/
│       └── default.yaml
└── README.md
```

Voir `examples/GITEA_STRUCTURE.md` pour plus de détails.

### 4. Créer le réseau Docker

```bash
docker network create bojemoi-net
```

### 5. Lancer l'orchestrator

```bash
# Construction des images
docker-compose build

# Démarrage des services
docker-compose up -d

# Vérifier les logs
docker-compose logs -f
```

### 6. Vérifier le fonctionnement

```bash
# Health check
curl http://localhost:8000/health

# Ou avec jq pour un affichage formaté
curl -s http://localhost:8000/health | jq .
```

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
    "ports": ["80:80", "443:443"]
  }'
```

### Lister les déploiements

```bash
curl http://localhost:8000/api/v1/deployments | jq .
```

## Commandes utiles

```bash
# Afficher les logs
make logs

# Redémarrer les services
make restart

# Ouvrir un shell dans le container
make shell

# Exécuter les tests
make test

# Arrêter les services
make down

# Nettoyer complètement
make clean
```

## Troubleshooting

### L'orchestrator ne démarre pas

1. Vérifier les logs: `docker-compose logs orchestrator`
2. Vérifier que PostgreSQL est bien démarré: `docker-compose ps`
3. Vérifier la configuration: `cat .env`

### Erreur de connexion Gitea

1. Vérifier l'URL Gitea: `curl https://gitea.bojemoi.me/api/v1/version`
2. Vérifier le token: il doit avoir les permissions de lecture sur le repo
3. Vérifier que le repo existe: `https://gitea.bojemoi.me/bojemoi/bojemoi-configs`

### Erreur de connexion XenServer

1. Vérifier l'URL et les credentials
2. Vérifier que le port XenAPI est accessible (443 par défaut)
3. Note: Le client XenServer actuel est un stub, vous devez implémenter la connexion réelle

### Erreur Docker Swarm

1. Vérifier que Swarm est initialisé: `docker info | grep Swarm`
2. Si non initialisé: `docker swarm init`
3. Vérifier que le socket Docker est monté: `docker-compose config`

## Configuration avancée

### Changer le port de l'API

Dans `docker-compose.yml`:

```yaml
services:
  orchestrator:
    ports:
      - "9000:8000"  # Changer 8000 par le port désiré
```

### Ajouter des variables d'environnement

Dans `docker-compose.yml`:

```yaml
services:
  orchestrator:
    environment:
      - CUSTOM_VAR=valeur
```

### Utiliser une base de données externe

Dans `.env`:

```bash
DATABASE_URL=postgresql://user:pass@external-host:5432/bojemoi
```

Puis commentez le service `postgres` dans `docker-compose.yml`.

## Mise à jour

```bash
# Arrêter les services
docker-compose down

# Récupérer les dernières modifications
git pull  # si vous utilisez Git

# Reconstruire
docker-compose build

# Redémarrer
docker-compose up -d
```

## Support

Pour toute question ou problème, consultez:
- README.md - Documentation principale
- examples/GITEA_STRUCTURE.md - Structure Gitea
- Les logs: `docker-compose logs -f`
