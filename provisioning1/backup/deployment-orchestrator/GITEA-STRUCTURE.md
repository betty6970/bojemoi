# Structure des Dépôts Gitea pour Deployment Orchestrator

## 📁 Architecture Recommandée

Il y a **deux approches** possibles :

### Approche 1 : Monorepo (Recommandé pour débuter)

Un seul dépôt contenant toutes les configurations :

```
infrastructure-configs/
├── README.md
├── .gitignore
│
├── deployments/
│   ├── manifest.yaml                    # Manifeste par défaut
│   ├── production/
│   │   ├── manifest-webserver.yaml
│   │   ├── manifest-database.yaml
│   │   └── manifest-api.yaml
│   ├── staging/
│   │   ├── manifest-webserver.yaml
│   │   └── manifest-api.yaml
│   └── development/
│       └── manifest-test.yaml
│
├── vms/
│   ├── production/
│   │   ├── web-prod-01.yaml
│   │   ├── web-prod-02.yaml
│   │   ├── db-prod-01.yaml
│   │   └── api-prod-01.yaml
│   ├── staging/
│   │   ├── web-staging-01.yaml
│   │   └── api-staging-01.yaml
│   └── templates/
│       └── standard-vm.yaml.template
│
├── containers/
│   ├── production/
│   │   ├── nginx-proxy.yaml
│   │   ├── redis-cache.yaml
│   │   └── monitoring-agent.yaml
│   ├── staging/
│   │   ├── api-backend.yaml
│   │   └── frontend.yaml
│   └── templates/
│       └── standard-container.yaml.template
│
├── swarm-services/
│   ├── production/
│   │   ├── frontend-app.yaml
│   │   ├── api-service.yaml
│   │   └── worker-service.yaml
│   ├── staging/
│   │   └── test-service.yaml
│   └── templates/
│       └── standard-service.yaml.template
│
├── cloud-init/
│   ├── roles/
│   │   ├── webserver/
│   │   │   ├── user-data.yaml
│   │   │   └── meta-data.yaml
│   │   ├── database/
│   │   │   ├── user-data.yaml
│   │   │   └── meta-data.yaml
│   │   ├── api-server/
│   │   │   └── user-data.yaml
│   │   └── monitoring/
│   │       └── user-data.yaml
│   └── common/
│       ├── base-packages.yaml
│       └── security-hardening.yaml
│
├── scripts/
│   ├── validate-manifest.sh
│   ├── generate-manifest.py
│   └── backup-configs.sh
│
└── docs/
    ├── deployment-guide.md
    ├── vm-naming-convention.md
    └── troubleshooting.md
```

### Approche 2 : Multi-repos (Pour organisations plus grandes)

Plusieurs dépôts spécialisés :

```
gitea.bojemoi.lab/
├── infra/deployment-manifests      # Manifestes de déploiement
├── infra/vm-configs                # Configurations VMs
├── infra/container-configs         # Configurations containers
├── infra/cloud-init-configs        # Configurations cloud-init
└── infra/deployment-orchestrator   # Code de l'orchestrateur
```

## 📝 Exemples de Fichiers

### 1. Manifeste VM Production

**Fichier** : `deployments/production/manifest-webserver.yaml`

```yaml
version: "1.0"
deployment_type: vm
environment: production

metadata:
  description: "Serveur web nginx de production"
  owner: "ops-team"
  project: "web-infrastructure"
  ticket: "INFRA-123"
  created_by: "betty"
  created_at: "2024-01-15"

vm_config:
  name: "web-prod-01"
  template: "Ubuntu-22.04-Template"
  vcpus: 4
  memory_mb: 8192
  disk_gb: 100
  network: "production-network"
  
  # Configuration cloud-init
  cloud_init_role: "webserver"
  cloud_init_params:
    hostname: "web-prod-01.bojemoi.lab"
    domain: "bojemoi.lab"
    timezone: "Europe/Paris"
    enable_monitoring: true
    backup_schedule: "daily"
  
  # Tags pour organisation et automation
  tags:
    environment: "production"
    role: "webserver"
    managed_by: "orchestrator"
    backup: "daily"
    monitoring: "enabled"
    cost_center: "infrastructure"
    compliance: "gdpr"
```

### 2. Manifeste Container Staging

**Fichier** : `deployments/staging/manifest-api.yaml`

```yaml
version: "1.0"
deployment_type: container
environment: staging

metadata:
  description: "API backend pour l'environnement de staging"
  owner: "dev-team"
  project: "api-backend"
  repository: "https://gitea.bojemoi.lab/apps/api-backend"

container_config:
  name: "api-backend-staging"
  image: "registry.bojemoi.lab/api-backend"
  tag: "staging-latest"
  
  env_vars:
    NODE_ENV: "staging"
    DATABASE_URL: "postgresql://postgres.bojemoi.lab:5432/api_staging"
    REDIS_URL: "redis://redis.bojemoi.lab:6379/0"
    LOG_LEVEL: "debug"
    API_PORT: "3000"
    CORS_ORIGIN: "https://staging.bojemoi.lab"
    JWT_SECRET: "INJECTED_FROM_SECRET_MANAGER"
  
  ports:
    - "3000:3000"
  
  volumes:
    - "/var/log/api-backend:/app/logs"
    - "/etc/api-backend/config.json:/app/config.json:ro"
  
  networks:
    - "bojemoi_network"
  
  restart_policy: "unless-stopped"
  
  labels:
    traefik.enable: "true"
    traefik.http.routers.api-staging.rule: "Host(`api-staging.bojemoi.lab`)"
    traefik.http.routers.api-staging.entrypoints: "websecure"
    traefik.http.routers.api-staging.tls: "true"
    prometheus.scrape: "true"
    prometheus.port: "3000"
    prometheus.path: "/metrics"
```

### 3. Manifeste Swarm Service Production

**Fichier** : `deployments/production/manifest-frontend.yaml`

```yaml
version: "1.0"
deployment_type: swarm_service
environment: production

metadata:
  description: "Application frontend React en production"
  owner: "platform-team"
  project: "frontend-app"
  slack_channel: "#deployments"

swarm_config:
  name: "frontend-prod"
  image: "registry.bojemoi.lab/frontend-app"
  tag: "v2.4.1"
  replicas: 3
  
  env_vars:
    NODE_ENV: "production"
    API_URL: "https://api.bojemoi.lab"
    CDN_URL: "https://cdn.bojemoi.lab"
    SENTRY_DSN: "https://sentry.bojemoi.lab/2"
    ANALYTICS_ID: "GA-123456789"
  
  ports:
    - "8080:8080"
  
  networks:
    - "bojemoi_network"
    - "ingress"
  
  # Contraintes de placement
  constraints:
    - "node.role==worker"
    - "node.labels.region==eu-west"
    - "node.labels.datacenter==primary"
  
  # Labels Traefik et monitoring
  labels:
    traefik.enable: "true"
    traefik.http.routers.frontend.rule: "Host(`www.bojemoi.lab`)"
    traefik.http.routers.frontend.entrypoints: "websecure"
    traefik.http.routers.frontend.tls: "true"
    traefik.http.routers.frontend.tls.certresolver: "letsencrypt"
    traefik.http.services.frontend.loadbalancer.server.port: "8080"
    traefik.http.services.frontend.loadbalancer.sticky.cookie: "true"
    prometheus.scrape: "true"
    prometheus.port: "8080"
  
  # Configuration de rolling update
  update_config:
    parallelism: 1
    delay: 30
    failure_action: "rollback"
    monitor: 60000000000
    max_failure_ratio: 0.1
    order: "start-first"
  
  # Configuration de rollback
  rollback_config:
    parallelism: 1
    delay: 10
    failure_action: "pause"
    monitor: 30000000000
  
  # Ressources
  resources:
    limits:
      cpus: "0.5"
      memory: "512M"
    reservations:
      cpus: "0.25"
      memory: "256M"
```

### 4. Configuration Cloud-init - Webserver

**Fichier** : `cloud-init/roles/webserver/user-data.yaml`

```yaml
#cloud-config

# Configuration cloud-init pour role webserver
# Utilisé automatiquement par l'orchestrateur

hostname: ${hostname}
fqdn: ${hostname}.${domain}
manage_etc_hosts: true

timezone: ${timezone:-Europe/Paris}

# Utilisateurs
users:
  - name: deploy
    groups: sudo, docker
    shell: /bin/bash
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    ssh_authorized_keys:
      - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQ... deploy@bojemoi.lab

# Packages à installer
packages:
  - nginx
  - certbot
  - python3-certbot-nginx
  - ufw
  - fail2ban
  - htop
  - curl
  - wget
  - git
  - docker.io
  - docker-compose

# Configuration réseau
network:
  version: 2
  ethernets:
    ens160:
      dhcp4: true

# Scripts à exécuter
runcmd:
  # Configuration firewall
  - ufw allow 22/tcp
  - ufw allow 80/tcp
  - ufw allow 443/tcp
  - ufw --force enable
  
  # Configuration nginx
  - systemctl enable nginx
  - systemctl start nginx
  
  # Configuration Docker
  - systemctl enable docker
  - systemctl start docker
  - usermod -aG docker deploy
  
  # Configuration fail2ban
  - systemctl enable fail2ban
  - systemctl start fail2ban
  
  # Configuration monitoring (si activé)
  - |
    if [ "${enable_monitoring}" = "true" ]; then
      curl -sSL https://repos.bojemoi.lab/monitoring-agent.sh | bash
    fi
  
  # Configuration backup (si activé)
  - |
    if [ "${backup_schedule}" != "" ]; then
      echo "0 2 * * * /usr/local/bin/backup.sh" | crontab -
    fi
  
  # Signal fin d'installation
  - curl -X POST https://orchestrator.bojemoi.lab/vm-ready \
      -H "Content-Type: application/json" \
      -d '{"hostname":"${hostname}","role":"webserver"}'

# Fichiers à créer
write_files:
  - path: /etc/nginx/sites-available/default
    content: |
      server {
          listen 80 default_server;
          server_name _;
          
          location / {
              return 200 "Webserver ready\n";
              add_header Content-Type text/plain;
          }
          
          location /health {
              return 200 "OK\n";
              add_header Content-Type text/plain;
          }
      }
  
  - path: /usr/local/bin/backup.sh
    permissions: '0755'
    content: |
      #!/bin/bash
      # Script de backup automatique
      BACKUP_DIR="/backup/${hostname}"
      mkdir -p $BACKUP_DIR
      tar -czf $BACKUP_DIR/backup-$(date +%Y%m%d-%H%M%S).tar.gz \
          /etc/nginx \
          /var/www
      # Garder seulement les 7 derniers backups
      find $BACKUP_DIR -name "backup-*.tar.gz" -mtime +7 -delete

# Messages finaux
final_message: |
  Webserver ${hostname} déployé avec succès!
  Rôle: webserver
  Environnement: ${environment:-production}
  
  Services disponibles:
  - Nginx: http://${hostname}.${domain}
  - Health: http://${hostname}.${domain}/health
  
  Configuration cloud-init terminée en $UPTIME secondes.
```

### 5. Configuration Cloud-init - Database

**Fichier** : `cloud-init/roles/database/user-data.yaml`

```yaml
#cloud-config

hostname: ${hostname}
fqdn: ${hostname}.${domain}

timezone: Europe/Paris

users:
  - name: postgres
    system: true
  - name: dbadmin
    groups: sudo
    shell: /bin/bash
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    ssh_authorized_keys:
      - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQ... dbadmin@bojemoi.lab

packages:
  - postgresql-14
  - postgresql-contrib
  - pgbackrest
  - ufw

runcmd:
  # Firewall - PostgreSQL
  - ufw allow 5432/tcp
  - ufw allow 22/tcp
  - ufw --force enable
  
  # Configuration PostgreSQL
  - systemctl enable postgresql
  - systemctl start postgresql
  
  # Configuration de base
  - |
    sudo -u postgres psql -c "CREATE USER ${db_user:-appuser} WITH PASSWORD '${db_password}';"
    sudo -u postgres psql -c "CREATE DATABASE ${db_name:-appdb} OWNER ${db_user:-appuser};"
  
  # Configuration pour écoute réseau
  - |
    echo "listen_addresses = '*'" >> /etc/postgresql/14/main/postgresql.conf
    echo "host all all 0.0.0.0/0 md5" >> /etc/postgresql/14/main/pg_hba.conf
    systemctl restart postgresql
  
  # Backup automatique
  - |
    cat > /usr/local/bin/pg-backup.sh << 'EOF'
    #!/bin/bash
    BACKUP_DIR="/backup/postgresql"
    mkdir -p $BACKUP_DIR
    sudo -u postgres pg_dumpall | gzip > $BACKUP_DIR/backup-$(date +%Y%m%d-%H%M%S).sql.gz
    find $BACKUP_DIR -name "backup-*.sql.gz" -mtime +7 -delete
    EOF
    chmod +x /usr/local/bin/pg-backup.sh
    echo "0 3 * * * /usr/local/bin/pg-backup.sh" | crontab -

write_files:
  - path: /etc/postgresql/14/main/conf.d/custom.conf
    content: |
      # Configuration personnalisée PostgreSQL
      max_connections = ${max_connections:-100}
      shared_buffers = ${shared_buffers:-256MB}
      effective_cache_size = ${effective_cache_size:-1GB}
      work_mem = ${work_mem:-4MB}
      maintenance_work_mem = ${maintenance_work_mem:-64MB}
      
      # Logging
      logging_collector = on
      log_directory = 'pg_log'
      log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
      log_statement = 'ddl'
      log_min_duration_statement = 1000

final_message: |
  PostgreSQL Server ${hostname} déployé!
  Database: ${db_name:-appdb}
  User: ${db_user:-appuser}
  Port: 5432
```

## 🔧 Fichiers de Configuration Complémentaires

### .gitignore

**Fichier** : `.gitignore`

```
# Secrets et credentials
*.secret
*.key
*.pem
credentials.yaml
secrets/

# Fichiers temporaires
*.tmp
*.bak
*.swp
*~

# Logs
logs/
*.log

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.code-workspace
```

### Template de validation

**Fichier** : `scripts/validate-manifest.sh`

```bash
#!/bin/bash
# Script de validation des manifestes avant commit

echo "🔍 Validation des manifestes de déploiement..."

ERRORS=0

# Vérifier tous les fichiers YAML
for file in $(find deployments -name "*.yaml"); do
    echo "Validation: $file"
    
    # Vérifier la syntaxe YAML
    if ! python3 -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
        echo "❌ Erreur de syntaxe YAML: $file"
        ((ERRORS++))
    fi
    
    # Vérifier les champs requis
    if ! grep -q "deployment_type:" "$file"; then
        echo "❌ Champ 'deployment_type' manquant: $file"
        ((ERRORS++))
    fi
    
    if ! grep -q "environment:" "$file"; then
        echo "❌ Champ 'environment' manquant: $file"
        ((ERRORS++))
    fi
done

if [ $ERRORS -eq 0 ]; then
    echo "✅ Tous les manifestes sont valides!"
    exit 0
else
    echo "❌ $ERRORS erreur(s) détectée(s)"
    exit 1
fi
```

## 📋 Conventions de Nommage

### Noms de VMs
```
{role}-{environment}-{number}
Exemples:
- web-prod-01
- db-staging-02
- api-dev-01
```

### Noms de Containers
```
{service}-{environment}[-{instance}]
Exemples:
- api-backend-staging
- redis-cache-prod
- nginx-proxy-prod-01
```

### Noms de Services Swarm
```
{service}-{environment}
Exemples:
- frontend-prod
- worker-staging
- api-prod
```

### Noms de Fichiers
```
manifest-{description}.yaml
{role}-{environment}-{number}.yaml

Exemples:
- manifest-webserver.yaml
- manifest-api-backend.yaml
- web-prod-01.yaml
```

## 🔄 Workflow Git Recommandé

### Branches
```
main          # Production (déploiements auto)
staging       # Staging (déploiements auto)
development   # Dev (déploiements auto)
feature/*     # Features (pas de déploiement auto)
```

### Process de déploiement
```bash
# 1. Créer une branche feature
git checkout -b feature/add-new-api-server

# 2. Créer/modifier le manifeste
nano deployments/production/manifest-api.yaml

# 3. Valider localement
./scripts/validate-manifest.sh

# 4. Commit et push
git add deployments/production/manifest-api.yaml
git commit -m "Add new API server deployment manifest"
git push origin feature/add-new-api-server

# 5. Créer une Pull Request dans Gitea

# 6. Review et merge vers staging
# → Déclenchement auto du déploiement staging

# 7. Test en staging

# 8. Merge vers main
# → Déclenchement auto du déploiement production
```

## 📊 Exemple de README pour le dépôt

**Fichier** : `README.md`

```markdown
# Infrastructure Configurations - Bojemoi Lab

Ce dépôt contient toutes les configurations d'infrastructure pour le déploiement automatisé via l'orchestrateur.

## Structure

- `deployments/` - Manifestes de déploiement par environnement
- `vms/` - Configurations spécifiques aux VMs
- `containers/` - Configurations spécifiques aux containers
- `swarm-services/` - Configurations des services Docker Swarm
- `cloud-init/` - Configurations cloud-init par rôle
- `scripts/` - Scripts utilitaires

## Déploiement Automatique

Tout push vers les branches suivantes déclenche un déploiement automatique :
- `main` → Production
- `staging` → Staging
- `development` → Development

## Créer un Nouveau Déploiement

1. Copier un template depuis `templates/`
2. Adapter la configuration
3. Valider : `./scripts/validate-manifest.sh`
4. Créer une PR
5. Merger après review

## Documentation

- [Guide de déploiement](docs/deployment-guide.md)
- [Conventions de nommage](docs/naming-conventions.md)
- [Troubleshooting](docs/troubleshooting.md)
```

Voulez-vous que je crée maintenant un dépôt Git complet avec tous ces fichiers d'exemple prêts à être poussés vers Gitea ?
