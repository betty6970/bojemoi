# 🚀 Guide de Démarrage Rapide

## Installation en 5 minutes

### 1. Prérequis
```bash
# Vérifier Docker
docker --version
docker-compose --version
```

### 2. Configuration
```bash
# Copier le fichier d'environnement
cp .env.example .env

# Éditer avec vos paramètres
nano .env
```

**Paramètres minimaux à configurer :**
```bash
GITEA_URL=https://gitea.bojemoi.lab
GITEA_TOKEN=votre_token_gitea
POSTGRES_PASSWORD=mot_de_passe_securise
XENSERVER_URL=https://xenserver.bojemoi.lab
XENSERVER_PASSWORD=mot_de_passe_xenserver
```

### 3. Démarrage
```bash
# Lancer les services
make up

# Ou avec docker-compose
docker-compose up -d

# Vérifier le statut
make status
```

### 4. Test
```bash
# Exécuter les tests
./test-installation.sh

# Vérifier la santé
curl http://localhost:8080/health
```

### 5. Configuration Gitea

#### A. Créer un Token
1. Aller sur Gitea → Paramètres utilisateur
2. Applications → Générer un nouveau token
3. Copier le token dans `.env` → `GITEA_TOKEN`

#### B. Créer un Webhook
1. Aller dans votre dépôt Gitea
2. Paramètres → Webhooks → Ajouter un webhook
3. Configurer :
   - **URL** : `http://orchestrator.bojemoi.lab:8080/webhook/gitea`
   - **Type de contenu** : `application/json`
   - **Secret** : Créer un secret et le mettre dans `GITEA_WEBHOOK_SECRET`
   - **Événements** : Push
   - **Actif** : ✅

## Premier Déploiement

### 1. Créer un manifeste dans Gitea

Fichier : `deployments/manifest.yaml`

```yaml
version: "1.0"
deployment_type: container
environment: staging

container_config:
  name: "hello-world-staging"
  image: "nginx"
  tag: "alpine"
  ports:
    - "8081:80"
  restart_policy: "unless-stopped"
  labels:
    environment: "staging"
    managed: "orchestrator"
```

### 2. Commit et Push

```bash
git add deployments/manifest.yaml
git commit -m "Add hello-world deployment"
git push
```

### 3. Vérifier le Déploiement

```bash
# Voir les déploiements
make deployments

# Vérifier le container
docker ps | grep hello-world-staging

# Tester
curl http://localhost:8081
```

## Commandes Utiles

### Monitoring
```bash
make logs          # Voir les logs en temps réel
make health        # Vérifier la santé
make metrics       # Voir les métriques
make deployments   # Liste des déploiements
```

### Gestion
```bash
make restart       # Redémarrer les services
make shell         # Shell dans le container
make db-shell      # Shell PostgreSQL
make clean         # Nettoyer tout
```

### Debug
```bash
# Logs détaillés
docker-compose logs -f orchestrator

# Statut du container
docker-compose ps

# Inspecter un déploiement
curl http://localhost:8080/deployments/1
```

## Architecture Minimale

```
Gitea (Lightsail)
    ↓ webhook
Orchestrator (Docker)
    ↓
├─→ XenServer (VMs)
└─→ Docker (Containers)
```

## Structure de Dépôt Recommandée

```
infra-deployments/
├── deployments/
│   ├── manifest.yaml           # Manifeste par défaut
│   ├── production/
│   │   └── manifest.yaml       # Prod
│   └── staging/
│       └── manifest.yaml       # Staging
├── vms/
│   └── webserver.yaml
└── containers/
    └── api-backend.yaml
```

## Troubleshooting Rapide

### Le webhook ne fonctionne pas
1. Vérifier que l'orchestrateur est accessible depuis Gitea
2. Vérifier le secret du webhook
3. Voir les logs : `make logs`

### Le déploiement échoue
1. Vérifier les logs : `curl http://localhost:8080/deployments/ID`
2. Vérifier les credentials (XenServer, Docker)
3. Vérifier le manifeste YAML

### PostgreSQL ne démarre pas
1. Vérifier les volumes : `docker volume ls`
2. Supprimer et recréer : `make clean && make up`

## Prochaines Étapes

1. ✅ Configurer le monitoring Prometheus
2. ✅ Ajouter d'autres types de déploiements
3. ✅ Configurer les environnements (prod/staging/dev)
4. ✅ Mettre en place les cloud-init datasources
5. ✅ Intégrer avec Grafana pour les dashboards

## Support

- 📖 Documentation complète : `README.md`
- 🐛 Issues : Gitea Issues
- 💬 Questions : bojemoi-lab@example.com
