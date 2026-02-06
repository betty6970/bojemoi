# BUILD PROMPT: BOJEMOI LAB - Infrastructure-as-Code Platform

> Ce document est un prompt de reconstruction. Il contient toutes les spécifications
> nécessaires pour recréer le projet Bojemoi Lab depuis zéro.

---

## 1. Vision du Projet

Construire une plateforme **Infrastructure-as-Code hybride** nommée **Bojemoi Lab** qui orchestre :

- Déploiement de VMs sur XenServer/XCP-ng avec cloud-init
- Orchestration de conteneurs via Docker Swarm (multi-noeud)
- Scanning de sécurité unifié avec orchestrateur de pentest (7+ outils)
- Audit trail immuable via blockchain SHA-256
- Stack de monitoring entreprise (métriques, logs, traces)
- Backup distribué rsync master/slave
- NFS partagé entre noeuds
- Pipeline CI/CD GitLab avec scanning de sécurité intégré
- Threat intelligence par ML
- Alerting via Prometheus → Alertmanager → ProtonMail/Slack

**Convention de nommage** : Les répertoires utilisent des noms de batailles historiques comme noms de code (Borodino, Koursk, Stalingrad, Tsushima, Narva, Berezina, Kyiv, Samsonov, Zarovnik...).

---

## 2. Arborescence Complète du Projet

```
bojemoi/
├── CLAUDE.md                    # Instructions pour Claude Code
├── BUILD_PROMPT.md              # Ce fichier (prompt de reconstruction)
│
├── stack/                       # Stacks Docker Swarm
│   ├── 01-service-hl.yml       # Services core (monitoring, proxy, DB, mail, IDS)
│   ├── 40-service-borodino.yml # Stack sécurité/pentest (fusionnée)
│   ├── 45-service-ml-threat-intel.yml  # ML threat intelligence
│   ├── .gitlab-ci.yml          # Pipeline CI/CD
│   └── README.md
│
├── provisioning/                # Orchestrateur FastAPI
│   ├── orchestrator/
│   │   └── app/
│   │       ├── main.py
│   │       ├── config.py
│   │       ├── auth/           # JWT + CORS + router
│   │       ├── models/         # Pydantic schemas
│   │       ├── services/       # Clients (Gitea, XenServer, Docker, DB, Blockchain)
│   │       └── middleware/     # IP validation, métriques Prometheus
│   ├── alembic/                # Migrations DB
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env
│
├── samsonov/                    # Pentest Orchestrator
│   ├── pentest_orchestrator/
│   │   ├── main.py             # PluginManager + daemon Redis
│   │   ├── import_results.py   # Import vers Faraday
│   │   ├── config/config.json
│   │   ├── results/
│   │   └── plugins/            # 7 plugins (nuclei, masscan, zap, burp, vulnx, metasploit, faraday)
│   └── nuclei_api/             # API FastAPI wrapper pour Nuclei
│       └── main.py
│
├── koursk/                      # Rsync base (Dockerfile + docs)
├── koursk-1/                    # Rsync avec métriques Prometheus
│   ├── metrics_exporter.py
│   └── metrics_server.sh
├── koursk-2/                    # Rsync production master/slave
│   ├── Dockerfile.koursk-2
│   ├── scripts/
│   │   ├── rsync-start.sh      # Démarrage master
│   │   ├── rsync-slave.sh      # Démarrage slave
│   │   └── rsync-master.py     # Orchestration Python
│   ├── config/                  # Jobs rsync (JSON)
│   └── modules/
│
├── oblast/                      # OWASP ZAP proxy
│   └── Dockerfile
├── oblast-1/                    # ZAP scanner automatisé
│   ├── Dockerfile.oblast-1
│   └── zap_scanner.py
│
├── kyiv/                        # Burp Suite Community
│   ├── api_server.py
│   ├── burp_automation.py
│   └── docker-compose.yml
│
├── tsushima/                    # Masscan scanner
│   └── vpn_masscan_pipeline.py  # VPN rotation + scan
│
├── borodino/                    # Weapon services (ak47, bm12, uzi)
│   └── Dockerfile
│
├── karacho/                     # Blockchain audit trail
│   ├── blockchain_postgres_api.py  # Flask API (port 5100)
│   └── blockchain_service.py
│
├── narva/                       # Service auxiliaire
│   └── Dockerfile
│
├── stalingrad/                  # Règles et configurations
│   ├── config/
│   └── rules/
│
├── berezina/                    # Service auxiliaire
│   └── Dockerfile
│
├── vladimir/                    # NFS server
│   ├── Dockerfile.vladimir
│   ├── start-nfs.sh
│   └── supervisord.conf
├── vladimir-1/                  # NFS client v1
│   ├── Dockerfile.vladimir-1
│   └── entrypoint.sh
├── vladimir-2/                  # NFS client v2
│   └── docker-compose.yml
│
├── zarovnik/                    # GitLab
│   ├── gitlab-stack.yml
│   ├── deploy-gitlab.sh
│   ├── gitlab-maintenance.sh
│   └── GITLAB-SETUP.md
│
├── ml-threat-intel/             # ML Threat Intelligence
│   └── (API FastAPI pour classification IoC)
│
├── cloud-init/                  # Templates cloud-init
│   ├── user-data
│   ├── network-config
│   ├── network-config-static
│   ├── meta-data
│   └── templates/               # Templates Jinja2
│
├── scripts/                     # Scripts utilitaires
│   ├── CI_CD_deploy.sh          # Déploiement production
│   ├── CI_CD_check.sh           # Validation pré-déploiement
│   ├── sync-stack-images.sh     # Sync images vers registry local
│   ├── sync_registry.py         # Synchronisation registry
│   ├── cleaning_registry.sh     # Nettoyage registry
│   ├── images_cross_build.py    # Builds cross-platform
│   ├── check_image.py           # Validation images
│   ├── init_postgres.sh         # Init PostgreSQL
│   ├── create-nfs-volume.sh     # Création volumes NFS
│   ├── send_email.sh            # Notifications email
│   ├── import_2_faraday.py      # Import résultats Faraday
│   ├── tannenberg.py            # Orchestration custom
│   └── download_ip.py           # Téléchargement base IP
│
├── volumes/                     # Configurations persistantes
│   ├── prometheus/prometheus.yml
│   ├── alertmanager/alertmanager.yml
│   ├── grafana/
│   │   ├── grafana.ini
│   │   └── provisioning/        # Dashboards + datasources
│   ├── loki/loki-config.yml
│   ├── tempo/config/tempo.yaml
│   ├── alloy/config/config.alloy
│   ├── suricata/suricata.yaml
│   ├── traefik/                 # Certs SSL + config dynamique
│   ├── crowdsec/
│   ├── postfix/main.cf
│   ├── faraday/config/server.ini
│   ├── nuclei/
│   ├── dnsmask/dnsmask.conf
│   ├── registry/config.yml
│   ├── openvpn/
│   ├── rsync/configs/rsyncd.conf
│   ├── provisioning/.env
│   └── telegram_bot/
│
├── nfs-exports/                 # Points de montage NFS
├── dump/                        # Dumps divers
├── bacasable/                   # Sandbox / tests
│
└── wiki/                        # Documentation
    ├── Home.md
    ├── Docker-Swarm.md
    ├── Pentest-Orchestrator.md
    ├── Faraday.md
    ├── Monitoring.md
    ├── Alertes.md
    └── Claude-Skills.md
```

---

## 3. Stack Docker Swarm - Services Core (01-service-hl.yml)

### 3.1 Reverse Proxy - Traefik

```yaml
traefik:
  image: traefik:v3.x
  ports:
    - "80:80"
    - "443:443"
  # Let's Encrypt ACME
  # Labels Traefik pour dashboard
  # Montage docker.sock (lecture seule)
  networks: [proxy, monitoring]
```

Domaines routés via Traefik :
- `grafana.bojemoi.lab` → 3000
- `prometheus.bojemoi.lab` → 9090 (avec basic auth)
- `alertmanager.bojemoi.lab` → 9093
- `pgadmin.bojemoi.lab` → 80
- `cadvisor.bojemoi.lab` → 8080
- `tempo.bojemoi.lab` → 3200
- `nuclei.bojemoi.lab` → 8001
- `faraday.bojemoi.lab` → 5985
- `zap.bojemoi.lab` → 8090
- `provisioning.bojemoi.lab` → 8000
- `karacho.bojemoi.lab` → 5100
- `threat-intel.bojemoi.lab.local` → 8001

### 3.2 Monitoring

```yaml
prometheus:
  image: prom/prometheus
  port: 9090
  # Docker Swarm service discovery
  # Scrape configs pour tous les exporters
  networks: [monitoring]

grafana:
  image: grafana/grafana
  port: 3000
  # Provisioning auto : dashboards + datasources
  networks: [monitoring, proxy]

loki:
  image: grafana/loki
  port: 3100
  networks: [monitoring]

alertmanager:
  image: prom/alertmanager
  port: 9093
  # Routing : email (ProtonMail), Slack
  networks: [monitoring]

tempo:
  image: grafana/tempo
  port: 3200
  # Distributed tracing
  networks: [monitoring]

alloy:
  image: grafana/alloy
  # Collecteur OpenTelemetry
  # Mode global (tous les noeuds)
  networks: [monitoring]
```

### 3.3 Exporters (mode global)

```yaml
node-exporter:    # port 9100, mode global
cadvisor:         # port 8080, mode global
postgres-exporter: # port 9187
postfix-exporter:  # métriques mail
```

### 3.4 Base de Données

```yaml
postgres:
  image: postgres:15
  port: 5432
  volumes: [postgres_data:/var/lib/postgresql/data]
  networks: [backend, monitoring]

pgadmin:
  image: dpage/pgadmin4
  networks: [backend, proxy]
```

### 3.5 Sécurité (IDS/IPS)

```yaml
suricata:
  image: jasonish/suricata
  # Mode global, network_mode: host
  # ET Open rules, custom rules
  networks: [monitoring]

crowdsec:
  image: crowdsecurity/crowdsec
  # Analyse logs, bouncer Traefik
  networks: [monitoring, proxy]
```

### 3.6 Mail

```yaml
postfix:
  image: boky/postfix (ou custom)
  port: 25
  networks: [mail, monitoring]

protonmail-bridge:
  # Relais SMTP ProtonMail
  networks: [mail]
```

### 3.7 Rsync Backup

```yaml
rsync-master:
  image: localhost:5000/koursk-2
  # Déployé sur manager
  # Cron-based, syncs /opt/bojemoi vers slaves
  networks: [rsync_network]

rsync-slave:
  image: localhost:5000/koursk-2
  # Déployé sur workers (label rsync.slave=true)
  networks: [rsync_network]
```

### 3.8 Provisioning Orchestrator

```yaml
orchestrator:
  image: localhost:5000/provisioning
  port: 8000 (exposé 28080 en Swarm)
  # FastAPI + PostgreSQL
  networks: [backend, monitoring, proxy]
```

### 3.9 Docker Registry

```yaml
registry:
  image: registry:2
  port: 5000
  # Registry local pour images custom
```

### Réseaux Overlay

```yaml
networks:
  monitoring:
    driver: overlay
  backend:
    driver: overlay
  proxy:
    driver: overlay
  mail:
    driver: overlay
  rsync_network:
    driver: overlay
  pentest:
    driver: overlay
    attachable: true
```

---

## 4. Stack Docker Swarm - Sécurité (40-service-borodino.yml)

### 4.1 OWASP ZAP

```yaml
zaproxy:
  image: localhost:5000/oblast
  port: 8090
  networks: [pentest, proxy]

zap-scanner:
  image: localhost:5000/oblast-1
  # Scanner automatisé
  networks: [pentest]
```

### 4.2 Nuclei

```yaml
nuclei:
  image: projectdiscovery/nuclei
  # Scanner basé sur templates
  networks: [pentest]

nuclei-api:
  image: localhost:5000/nuclei-api
  port: 8001
  # Wrapper FastAPI pour Nuclei
  networks: [pentest, proxy]
```

### 4.3 Autres scanners

```yaml
vulnx:          # CMS vulnerability scanner (Python wrapper)
masscan-scanner: # Port scanner global, support VPN
burp:           # Burp Suite Community (kyiv)
```

### 4.4 Weapon Services (Borodino)

```yaml
ak47-service:   # 15 replicas
bm12-service:   # 15 replicas
uzi-service:    # 5 replicas
# Services d'attaque / simulation
```

### 4.5 Faraday + Pentest Orchestrator

```yaml
faraday:
  image: faradaysec/faraday
  port: 5985
  networks: [pentest, proxy, backend]

redis:
  image: redis:alpine
  # File d'attente pour orchestration
  networks: [pentest]

pentest-orchestrator:
  image: localhost:5000/samsonov
  # Daemon Python, plugin architecture
  # Connecté à Redis, Faraday, tous les scanners
  networks: [pentest]

redis-exporter:    # Métriques Redis
pentest-exporter:  # Métriques pentest
```

### 4.6 Blockchain Audit

```yaml
karacho-blockchain:
  image: localhost:5000/karacho
  port: 5100
  # Flask API, SHA-256 hash chain
  # Token-based auth (3600s expiry)
  networks: [pentest, proxy, backend]
```

---

## 5. Stack ML Threat Intelligence (45-service-ml-threat-intel.yml)

```yaml
ml-threat-intel-api:
  image: localhost:5000/ml-threat-intel
  port: 8001
  # Classification IoC par ML
  # Intégrations : VirusTotal, AbuseIPDB, OTX, Shodan
  # Secrets Docker pour clés API
  networks: [monitoring, proxy]
```

---

## 6. Provisioning Orchestrator (FastAPI)

### 6.1 Structure

```
provisioning/orchestrator/app/
├── main.py              # FastAPI avec lifespan management
├── config.py            # Pydantic BaseSettings
├── auth/
│   ├── security.py      # JWT tokens + CORS
│   ├── dependencies.py  # Dependency injection
│   ├── models.py        # User schemas
│   └── router.py        # /auth/login, /auth/register
├── models/
│   └── schemas.py       # Enums + Request/Response models
├── services/
│   ├── gitea_client.py       # Fetch configs depuis Gitea (httpx async)
│   ├── xenserver_client_real.py  # XenAPI pour déploiement VMs
│   ├── docker_client.py      # docker-py pour Docker Swarm
│   ├── cloudinit_gen.py      # Jinja2 templates cloud-init
│   ├── database.py           # PostgreSQL async (asyncpg + SQLAlchemy 2.0)
│   ├── blockchain.py         # SHA-256 hash chain audit
│   └── ip2location_client.py # Géolocalisation IP
└── middleware/
    ├── ip_validation.py      # Filtrage par pays (FR,DE,CH,BE,LU,NL,AT)
    └── metrics.py            # Prometheus client métriques
```

### 6.2 Endpoints API

```
POST /deploy/vm/{vm_name}              - Déployer VM sur XenServer
POST /deploy/container/{container_name} - Déployer conteneur
POST /deploy/service/{service_name}    - Déployer service Swarm
POST /deploy/all                       - Déploiement complet
GET  /deployments                      - Lister les déploiements (paginé)
GET  /status                           - Health check connexions
GET  /health                           - Liveness probe
GET  /metrics                          - Métriques Prometheus
POST /auth/login                       - Authentification JWT
POST /auth/register                    - Création utilisateur
```

### 6.3 Stack technique

| Composant | Version |
|-----------|---------|
| FastAPI | 0.109 |
| Uvicorn | latest |
| Pydantic | 2.5 |
| SQLAlchemy | 2.0 |
| asyncpg | latest |
| docker-py | 7.0 |
| httpx | latest |
| APScheduler | latest |
| Jinja2 | latest |
| prometheus-client | latest |

### 6.4 Modèles de données

#### Enums

```python
class OSType(str, Enum):
    ALPINE = "alpine"
    UBUNTU = "ubuntu"
    UBUNTU_20 = "ubuntu-20"
    UBUNTU_22 = "ubuntu-22"
    UBUNTU_24 = "ubuntu-24"
    DEBIAN = "debian"
    DEBIAN_11 = "debian-11"
    DEBIAN_12 = "debian-12"
    CENTOS = "centos"
    ROCKY = "rocky"

class Environment(str, Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEV = "dev"

class DeploymentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
```

#### XenServer Template Mapping

```python
TEMPLATE_MAP = {
    "alpine": "alpine-meta",
    "ubuntu": "Ubuntu Focal Fossa 20.04",
    "ubuntu-20": "Ubuntu Focal Fossa 20.04",
    "ubuntu-22": "Ubuntu Jammy Jellyfish 22.04",
    "ubuntu-24": "Ubuntu Noble Numbat 24.04",
    "debian": "Debian Bookworm 12",
    "debian-11": "Debian Bullseye 11",
    "debian-12": "Debian Bookworm 12",
    "centos": "CentOS 7",
    "rocky": "Rocky Linux 8",
}
```

#### VM Deploy Request

```python
class VMDeployRequest(BaseModel):
    name: str
    template: str            # Nom du template cloud-init
    os_type: OSType
    cpu: int = 2             # 1-32
    memory: int = 2048       # MB, min 512
    disk: int = 20           # GB, min 10
    network: str = "default"
    environment: Environment
    variables: Dict[str, Any]  # Variables cloud-init additionnelles
```

#### Container Deploy Request

```python
class ContainerDeployRequest(BaseModel):
    name: str
    image: str
    replicas: int = 1
    environment: Dict[str, str]
    ports: List[str]          # ["80:80", "443:443"]
    networks: List[str]
    labels: Dict[str, str]    # Labels Traefik, etc.
```

#### Blockchain Block

```python
class BlockchainBlock(BaseModel):
    id: int
    block_number: int
    previous_hash: Optional[str]
    current_hash: str         # SHA-256
    deployment_type: str      # vm, container
    name: str
    config: Dict[str, Any]
    resource_ref: Optional[str]
    status: DeploymentStatus
    source_ip: Optional[str]
    source_country: Optional[str]
    created_at: datetime
```

### 6.5 Schéma Base de Données

```sql
-- Table des déploiements
CREATE TABLE deployments (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,
    resource_ref VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_deployments_type ON deployments(type);
CREATE INDEX idx_deployments_status ON deployments(status);

-- Table blockchain (audit trail immuable)
CREATE TABLE deployment_blocks (
    id SERIAL PRIMARY KEY,
    block_number INTEGER UNIQUE NOT NULL,
    previous_hash VARCHAR(64),
    current_hash VARCHAR(64) NOT NULL,
    deployment_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,
    resource_ref VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    error TEXT,
    source_ip VARCHAR(45),
    source_country VARCHAR(2),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_blocks_number ON deployment_blocks(block_number);
```

### 6.6 Variables d'environnement

```env
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=deployments
POSTGRES_USER=orchestrator
POSTGRES_PASSWORD=secret

# Gitea (source GitOps)
GITEA_URL=https://gitea.bojemoi.lab
GITEA_TOKEN=xxx
GITEA_REPO=bojemoi-configs

# XenServer
XENSERVER_URL=https://xenserver.local
XENSERVER_USER=root
XENSERVER_PASSWORD=xxx

# Docker Swarm
DOCKER_HOST=unix:///var/run/docker.sock
DOCKER_SWARM_MANAGER=manager.bojemoi.lab.local

# IP Validation
IP_VALIDATION_ENABLED=true
ALLOWED_COUNTRIES=FR,DE,CH,BE,LU,NL,AT

# Scheduler
CHECK_INTERVAL_MINUTES=5
ENABLE_SCHEDULER=true
```

---

## 7. Pentest Orchestrator (Samsonov)

### 7.1 Architecture Plugin

```python
# base.py - Classe de base
class BasePlugin:
    name: str
    scan_types: List[str]  # ["full", "web", "network", "vuln", "cms"]

    def configure(self, target, options) -> None
    def run(self) -> dict
    def get_results(self) -> dict
    def cleanup(self) -> None
```

### 7.2 Plugins

| Plugin | Outil | Types de scan | Port/Protocole |
|--------|-------|---------------|----------------|
| plugin_nuclei | Nuclei | full, vuln, web | CLI subprocess |
| plugin_masscan | Masscan | full, network | CLI subprocess |
| plugin_zap | OWASP ZAP | full, web | API REST 8090 |
| plugin_burp | Burp Suite | web | API REST |
| plugin_vulnx | VulnX | cms | CLI subprocess |
| plugin_metasploit | Metasploit | full, network, vuln | MSFRPC |
| plugin_faraday | Faraday | (agrégation) | API REST 5985 |

### 7.3 Flux d'exécution

1. Configurer cible et type de scan
2. `PluginManager` charge dynamiquement les plugins via `importlib`
3. Exécution séquentielle : Masscan → ZAP → Nuclei → VulnX
4. Agrégation des résultats avec breakdown par sévérité
5. Sauvegarde locale JSON dans `results/`
6. Import automatique vers workspace Faraday
7. Stockage Redis pour traitement asynchrone

### 7.4 Mode daemon Redis

```python
# main.py - Mode daemon
orchestrator = PentestOrchestrator(config)
orchestrator.run_daemon(workspace="default")
# Écoute Redis pour commandes : scan, status, stop
```

### 7.5 Nuclei API (FastAPI wrapper)

```
POST /scan          - Lancer un scan Nuclei
GET  /scan/{id}     - Statut d'un scan
GET  /templates     - Lister les templates disponibles
GET  /health        - Health check
```

---

## 8. Système de Backup Rsync (Koursk)

### 8.1 Architecture

- **Master** (koursk-2) : déployé sur le noeud manager, exécute les jobs rsync
- **Slave** (koursk-2) : déployé sur les workers (label `rsync.slave=true`)
- Communication via réseau overlay `rsync_network`
- Planification par cron

### 8.2 Jobs de synchronisation

```json
{
  "jobs": [
    {"name": "bojemoi", "source": "/opt/bojemoi/", "dest": "/backup/bojemoi/"},
    {"name": "bojemoi_boot", "source": "/opt/bojemoi_boot/", "dest": "/backup/bojemoi_boot/"},
    {"name": "bojemoi-ml", "source": "/opt/bojemoi-ml-threat/", "dest": "/backup/ml-threat/"},
    {"name": "bojemoi-telegram", "source": "/opt/bojemoi-telegram/", "dest": "/backup/telegram/"}
  ]
}
```

### 8.3 Métriques Prometheus

```python
# metrics_exporter.py (koursk-1)
rsync_job_duration_seconds    # Durée des jobs
rsync_job_status              # Succès/échec
rsync_bytes_transferred       # Volume transféré
rsync_files_transferred       # Nombre de fichiers
```

---

## 9. NFS (Vladimir)

### 9.1 Architecture

- **vladimir** : Serveur NFS (Dockerfile + supervisord + start-nfs.sh)
- **vladimir-1** : Client NFS v1 (entrypoint.sh + run.sh)
- **vladimir-2** : Client NFS v2 (docker-compose)
- **nfs-exports/** : Répertoires de montage

---

## 10. Blockchain Audit Trail (Karacho)

### 10.1 API Flask

```
POST /block                  - Créer un nouveau bloc
GET  /chain                  - Récupérer la chaîne complète
GET  /verify                 - Vérifier l'intégrité de la chaîne
GET  /block/{block_number}   - Récupérer un bloc spécifique
```

### 10.2 Logique

- Chaque déploiement (VM ou conteneur) génère un bloc
- Hash SHA-256 : `sha256(block_number + previous_hash + timestamp + data)`
- Stockage PostgreSQL (table `deployment_blocks`)
- Authentification par token (expiration 3600s)
- Port 5100

---

## 11. Cloud-Init Templates

### 11.1 Fichiers

```
cloud-init/
├── user-data              # Configuration principale
├── network-config         # Réseau DHCP
├── network-config-static  # Réseau IP statique
├── meta-data              # Métadonnées instance
└── templates/             # Templates Jinja2
```

### 11.2 Workflow

1. Template Jinja2 stocké dans Gitea (`cloud-init/{template}.yaml`)
2. Orchestrateur fetch le template via `gitea_client.py`
3. Variables injectées via `cloudinit_gen.py` (Jinja2)
4. Cloud-init rendu passé à XenAPI lors du déploiement VM

---

## 12. GitLab CI/CD (Zarovnik)

### 12.1 Pipeline Stages

```yaml
stages:
  - validate    # Syntaxe YAML, variables d'env
  - build       # Build images Docker
  - test        # Tests unitaires + intégration
  - security    # Trivy, OWASP ZAP, upload Faraday
  - deploy      # Staging auto, production manuelle
  - verify      # Health checks, métriques Prometheus
  - notify      # Annotations Grafana, Slack/Email
```

### 12.2 Ordre de déploiement

```
traefik → monitoring → crowdsec → suricata → faraday → (autres services)
```

### 12.3 Fichiers GitLab

```
zarovnik/
├── gitlab-stack.yml                # Stack de déploiement GitLab
├── deploy-gitlab.sh                # Script de déploiement
├── gitlab-maintenance.sh           # Script de maintenance
├── gitlab-ci-example.yml           # Template pipeline CI/CD
├── gitlab-runner-config-example.toml
└── GITLAB-SETUP.md
```

---

## 13. ML Threat Intelligence

### 13.1 Service

- API FastAPI pour classification d'IoC (Indicators of Compromise)
- Intégrations externes via Docker secrets :
  - VirusTotal API
  - AbuseIPDB API
  - AlienVault OTX
  - Shodan API

---

## 14. Configuration Monitoring (volumes/)

### 14.1 Prometheus

```yaml
# volumes/prometheus/prometheus.yml
# 100+ lignes de scrape configs
# Docker Swarm service discovery
# Scrape : node-exporter, cadvisor, postgres, postfix, redis, pentest, etc.
```

### 14.2 Alertmanager

```yaml
# volumes/alertmanager/alertmanager.yml
# Routing : sévérité → receiver
# Receivers : email (ProtonMail SMTP), Slack webhook
# Groupement par alertname, job
# Silences pendant les déploiements de stack
```

### 14.3 Grafana

```
volumes/grafana/
├── grafana.ini
└── provisioning/
    ├── dashboards/    # Dashboards auto-provisionnés
    └── datasources/   # Prometheus, Loki, Tempo
```

### 14.4 Suricata

```yaml
# volumes/suricata/suricata.yaml
# IDS/IPS en mode global (tous les noeuds)
# Règles ET Open + règles custom
# Logs vers Loki
```

### 14.5 Autres configs

| Fichier | Service |
|---------|---------|
| `loki/loki-config.yml` | Agrégation de logs |
| `tempo/config/tempo.yaml` | Tracing distribué |
| `alloy/config/config.alloy` | Collecteur OpenTelemetry |
| `traefik/` | Certificats SSL + config dynamique |
| `crowdsec/` | Détection d'intrusion |
| `postfix/main.cf` | Serveur mail |
| `faraday/config/server.ini` | Plateforme vulnérabilités |
| `dnsmask/dnsmask.conf` | DNS masquerading |
| `registry/config.yml` | Docker registry local |
| `openvpn/` | Configuration VPN |

---

## 15. Scripts Utilitaires

| Script | Rôle |
|--------|------|
| `CI_CD_deploy.sh` | Orchestration de déploiement production |
| `CI_CD_check.sh` | Validation pré-déploiement |
| `test_deploiement.sh` | Tests de déploiement |
| `sync-stack-images.sh` | Sync images vers registry local (localhost:5000) |
| `sync_registry.py` | Synchronisation registry Python |
| `cleaning_registry.sh` | Nettoyage du registry |
| `images_cross_build.py` | Builds cross-platform (arm64/amd64) |
| `check_image.py` | Validation d'images Docker |
| `init_postgres.sh` | Initialisation PostgreSQL |
| `create-nfs-volume.sh` | Création de volumes NFS |
| `send_email.sh` | Envoi de notifications email |
| `import_2_faraday.py` | Import de résultats vers Faraday |
| `tannenberg.py` | Orchestration custom |
| `download_ip.py` | Téléchargement base IP2Location |

---

## 16. Workflows de Déploiement

### 16.1 Déploiement VM

```
1. POST /deploy/vm/{vm_name} avec VMDeployRequest
2. Middleware IP validation vérifie le pays source
3. Fetch template cloud-init depuis Gitea
4. Rendu Jinja2 avec variables
5. Création VM sur XenServer via XenAPI
6. Log dans blockchain (SHA-256 hash chain)
7. Log dans PostgreSQL (table deployments)
8. Retour deployment_id + référence VM
```

### 16.2 Déploiement Conteneur

```
1. POST /deploy/container/{name} avec ContainerDeployRequest
2. IP validation
3. Création service Docker Swarm via docker-py
4. Log blockchain
5. Log PostgreSQL
6. Retour deployment_id + service ID
```

### 16.3 Scan Pentest

```
1. Configurer cible + type (full/web/network/vuln/cms)
2. PluginManager charge les plugins dynamiquement
3. Exécution séquentielle : Masscan → ZAP → Nuclei → VulnX
4. Agrégation résultats avec breakdown sévérité
5. Sauvegarde JSON locale
6. Import Faraday workspace
7. Stockage Redis pour async
```

---

## 17. Sécurité

| Mesure | Détail |
|--------|--------|
| IP Validation | Whitelist par pays (Europe occidentale par défaut) |
| Private IP Bypass | 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 skip géoloc |
| JWT Auth | Authentification API par tokens |
| CORS | Origines configurables |
| DB Credentials | Variables d'environnement, jamais hardcodées |
| XenServer SSL | Support certificats auto-signés |
| Docker Socket | Accès direct requis pour gestion services |
| Blockchain | SHA-256 hash chain = audit immuable |
| Suricata | IDS/IPS global sur tous les noeuds |
| CrowdSec | Détection d'intrusion communautaire |
| Traefik | TLS termination + Let's Encrypt |
| Basic Auth | Prometheus et endpoints sensibles |

---

## 18. Ports Clés

| Port | Service |
|------|---------|
| 80/443 | Traefik (HTTP/HTTPS) |
| 3000 | Grafana |
| 3100 | Loki |
| 3200 | Tempo |
| 5000 | Docker Registry local |
| 5100 | Karacho (Blockchain API) |
| 5432 | PostgreSQL |
| 5985 | Faraday |
| 8000/28080 | Orchestrator API |
| 8001 | Nuclei API / ML Threat Intel |
| 8080 | cAdvisor |
| 8090 | OWASP ZAP |
| 9090 | Prometheus |
| 9093 | Alertmanager |
| 9100 | Node Exporter |
| 9187 | Postgres Exporter |

---

## 19. Commandes de Lancement

```bash
# Déployer le stack core
docker stack deploy -c stack/01-service-hl.yml base --prune --resolve-image always

# Déployer le stack sécurité
docker stack deploy -c stack/40-service-borodino.yml security --prune --resolve-image always

# Déployer ML threat intel
docker stack deploy -c stack/45-service-ml-threat-intel.yml ml --prune --resolve-image always

# Démarrer l'orchestrateur en dev
cd provisioning && pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Démarrer le pentest orchestrator en daemon
cd samsonov/pentest_orchestrator
python main.py --daemon --workspace default

# Sync images vers registry local
./scripts/sync-stack-images.sh

# Tester l'API
curl http://localhost:8000/health
curl -X POST http://localhost:8000/deploy/vm/test-vm \
  -H "Content-Type: application/json" \
  -d '{"name":"test-vm","template":"webserver","os_type":"alpine","cpu":2,"memory":2048}'

# Vérifier la blockchain
curl http://localhost:5100/verify
```

---

## 20. Dockerfiles à Construire (26 images custom)

| Image | Répertoire | Base |
|-------|-----------|------|
| provisioning | provisioning/ | python:3.11-slim |
| samsonov | samsonov/ | python:3.11-slim |
| nuclei-api | samsonov/nuclei_api/ | python:3.11-slim |
| koursk-2 | koursk-2/ | alpine + rsync + python |
| koursk-1 | koursk-1/ | alpine + rsync |
| oblast | oblast/ | ghcr.io/zaproxy/zaproxy |
| oblast-1 | oblast-1/ | python:3.11-slim + zaproxy |
| kyiv | kyiv/ | burp suite base |
| tsushima | tsushima/ | alpine + masscan |
| borodino | borodino/ | custom (weapon services) |
| karacho | karacho/ | python:3.11-slim + flask |
| vladimir | vladimir/ | alpine + nfs-utils |
| vladimir-1 | vladimir-1/ | alpine + nfs client |
| narva | narva/ | custom |
| berezina | berezina/ | custom |
| stalingrad | stalingrad/ | custom |
| ml-threat-intel | ml-threat-intel/ | python:3.11-slim |

Toutes les images custom sont poussées vers `localhost:5000/{nom}`.

---

## 21. Documentation Wiki

| Page | Contenu |
|------|---------|
| Home.md | Vue d'ensemble + diagramme d'architecture |
| Docker-Swarm.md | Gestion du cluster Swarm |
| Pentest-Orchestrator.md | Types de scan et utilisation |
| Faraday.md | Gestion des vulnérabilités |
| Monitoring.md | Métriques et alerting |
| Alertes.md | Configuration des alertes |
| Claude-Skills.md | Commandes CLI Claude Code |

---

## 22. Résumé des Fonctionnalités Clés

1. **Infrastructure Hybride** - VM (XenServer) + Conteneurs (Docker Swarm)
2. **Orchestrateur Unifié** - API FastAPI pour tous les déploiements
3. **Pentest Orchestration** - 7+ outils de scanning intégrés via plugins
4. **Blockchain Audit** - Trail immuable SHA-256 pour chaque déploiement
5. **Monitoring Entreprise** - Métriques (Prometheus), Logs (Loki), Traces (Tempo)
6. **IDS/IPS** - Suricata (global) + CrowdSec
7. **GitOps** - Configuration via Gitea
8. **CI/CD** - Pipeline GitLab avec scanning sécurité
9. **Backup Distribué** - Rsync master/slave avec métriques
10. **NFS Partagé** - Volumes partagés entre noeuds
11. **Mail** - Postfix + ProtonMail Bridge + alerting
12. **ML Threat Intel** - Classification IoC (VirusTotal, AbuseIPDB, OTX, Shodan)
13. **Registry Local** - Images custom sur localhost:5000
14. **Cloud-Init** - Templates Jinja2 pour provisioning VMs
15. **Géolocalisation** - Filtrage d'accès par pays
