# BUILD PROMPT: Recréer le projet Bojemoi Lab de zéro

> Ce document est un prompt complet permettant de recréer l'intégralité du projet Bojemoi Lab.
> Il peut être utilisé comme référence architecturale ou comme instruction pour un agent IA.

---

## 1. Vision du projet

**Bojemoi Lab** est une plateforme Infrastructure-as-Code (IaC) pour un lab de sécurité offensive/défensive sur infrastructure hybride. Elle orchestre :

- **VMs** sur XenServer/XCP-ng via XenAPI + cloud-init
- **Conteneurs** via Docker Swarm (3 nœuds)
- **Scanning de sécurité** avec orchestration multi-outils (Nmap, Metasploit, ZAP, Nuclei, Masscan, Burp, VulnX)
- **Monitoring** complet (Prometheus, Grafana, Loki, Tempo, Alertmanager, Suricata IDS)
- **Audit immuable** par blockchain SHA-256 stockée en PostgreSQL
- **Backup distribué** via rsync master/slaves avec Prometheus metrics

---

## 2. Infrastructure cible

### Swarm Cluster (3 nœuds)
```
meta-76 (manager/leader) : Intel i9-10900X, 8 cores, 16 GB RAM, Alpine Linux
meta-68 (worker)         : Nœud de travail pour scanning
meta-70 (worker)         : Nœud de travail pour scanning
```

### Services critiques
- **PostgreSQL 15** : base partagée (~9 GB), 6 bases (msf, ip2location, faraday, karacho, deployments, grafana)
- **Docker Registry** : localhost:5000, toutes les images poussées localement
- **Gitea** : gitea.bojemoi.me, source GitOps pour configs cloud-init
- **Traefik** : reverse proxy + TLS Let's Encrypt

---

## 3. Structure du projet

```
/opt/bojemoi/
│
├── provisioning/              # Orchestrateur FastAPI (composant central)
│   ├── orchestrator/
│   │   ├── app/
│   │   │   ├── main.py              # App FastAPI, lifespan, health, metrics
│   │   │   ├── config.py            # Pydantic BaseSettings
│   │   │   ├── models/
│   │   │   │   └── schemas.py       # VMDeployRequest, ContainerDeployRequest, enums
│   │   │   ├── services/
│   │   │   │   ├── gitea_client.py       # Client Gitea (cache ETag, raw file API)
│   │   │   │   ├── xenserver_client_real.py  # XenAPI avec retry, 23 codes erreur
│   │   │   │   ├── docker_client.py      # Docker Swarm service management
│   │   │   │   ├── cloudinit_gen.py      # Templates Jinja2 cloud-init
│   │   │   │   ├── database.py           # PostgreSQL async (asyncpg + SQLAlchemy 2.0)
│   │   │   │   ├── blockchain.py         # Chaîne SHA-256 immuable
│   │   │   │   └── ip2location_client.py # Validation géolocalisation
│   │   │   ├── middleware/
│   │   │   │   ├── ip_validation.py      # Contrôle d'accès par pays
│   │   │   │   └── metrics.py            # Prometheus metrics middleware
│   │   │   └── auth/                     # JWT authentication
│   │   ├── alembic/                      # Migrations DB
│   │   └── requirements.txt
│   └── Dockerfile.provisioning
│
├── samsonov/                  # Orchestrateur Pentest (plugin architecture)
│   ├── pentest_orchestrator/
│   │   ├── main.py                  # PluginManager + PentestOrchestrator (~24KB)
│   │   ├── import_results.py        # Import vers Faraday
│   │   ├── config/config.json       # Registry des plugins
│   │   └── plugins/
│   │       ├── base.py              # Classes de base (ScanType, Severity, Finding)
│   │       ├── plugin_nuclei.py     # Scanner de vulns par templates
│   │       ├── plugin_masscan.py    # Port scanner rapide (10K-100K pps)
│   │       ├── plugin_zap.py        # OWASP ZAP automation
│   │       ├── plugin_burp.py       # Burp Suite API
│   │       ├── plugin_vulnx.py      # Scanner CMS
│   │       ├── plugin_metasploit.py # Client RPC Metasploit
│   │       ├── plugin_faraday.py    # Plateforme d'agrégation
│   │       └── plugin_nmap.py       # Network mapping
│   ├── nuclei_api/                  # API REST wrapper pour Nuclei + Redis
│   ├── vulnx_wrapper/               # Wrapper CMS scanning
│   ├── faraday-security-stack/       # Intégration Faraday
│   └── Dockerfile.samsonov
│
├── borodino/                  # Services de scanning armé (nmap + metasploit)
│   ├── Dockerfile.borodino          # Alpine + Ruby 3.5 + Rust + Metasploit from source
│   ├── thearm_ak47                  # Scanner nmap CIDR (ash script, 15 replicas)
│   ├── thearm_bm12                  # Scanner nmap services (python, 15 replicas)
│   ├── thearm_uzi                   # Runner Metasploit RPC (python, 5 replicas)
│   └── list_vpn/                    # Credentials OpenVPN (ProtonVPN)
│
├── karacho/                   # Service Blockchain
│   ├── Dockerfile.karacho
│   ├── blockchain_postgres_api.py   # FastAPI pour gestion de blocs (~33KB)
│   ├── blockchain_service.py        # Service daemon avec auto-restart (~11KB)
│   └── client_api.py                # Client REST
│
├── oblast/                    # OWASP ZAP Proxy
│   ├── Dockerfile.zaproxy
│   ├── zap-script.sh               # Orchestration scanning
│   ├── zap_scanner.py              # Moteur de scan Python
│   └── docker-compose.yaml
│
├── oblast-1/                  # ZAP Scanner (variante)
│   ├── Dockerfile.oblast-1
│   ├── zap_scanner.py
│   └── entrypoint.sh
│
├── tsushima/                  # Scanner Masscan + VPN
│   ├── Dockerfile.tsushima          # Alpine + Python + masscan + VPN
│   ├── vpn_masscan_pipeline.py      # Pipeline VPN + CIDR + masscan + MSF (~37KB)
│   ├── masscan_msf_script.py        # Agrégation résultats
│   └── entrypoint.sh
│
├── kyiv/                      # Intégration Burp Suite
│   ├── Dockerfile.burp              # Burp Enterprise headless
│   ├── burpsuite-daemon/
│   │   └── api_server.py            # API REST wrapper (~6KB)
│   └── docker-compose.yml
│
├── koursk-2/                  # Rsync Master (backup distribué)
│   ├── Dockerfile.koursk-2          # Alpine + Python + rsync + prometheus-client
│   ├── config/rsync_jobs.json       # Jobs de backup (cycle 10 min)
│   └── scripts/
│       ├── rsync-master.py          # Orchestrateur master
│       └── rsync-start.sh           # Entrypoint
│
├── koursk/ & koursk-1/        # Rsync Slaves
│
├── narva/                     # Gateway VPN
│   └── Dockerfile.narva
│
├── stalingrad/                # Gestion règles IDS
│   └── Dockerfile.stalingrad
│
├── vladimir/ & vladimir-1/    # Répliques de services
│
├── berezina/                  # Versions legacy des scanners
│
├── zarovnik/                  # Intégration GitLab CI/CD
│   ├── gitlab-stack.yml
│   ├── deploy-gitlab.sh
│   └── gitlab-maintenance.sh
│
├── ml-threat-intel/           # Intelligence de menaces ML
│
├── cloud-init/                # Templates cloud-init pour VMs
│
├── scripts/                   # ~50 utilitaires
│   ├── bojemoiBuild.sh              # Build orchestrator complet
│   ├── cccp.sh / cccp-v2.sh         # Automatisation build
│   ├── push_registry_onebyone.sh    # Push images au registry
│   ├── check_image*.py              # Validation images (3 versions)
│   ├── download_ip.py               # Sync DB IP2Location
│   ├── sync_registry.py             # Synchronisation registry
│   ├── cleanDocker.sh               # Nettoyage conteneurs/images
│   ├── init_postgres.sh             # Init DB
│   ├── bojemoi2.py                  # Orchestration avancée (~34KB)
│   └── ...
│
├── stack/                     # Fichiers Docker Swarm Stack
│   ├── 01-service-hl.yml            # Infrastructure core (~1125 lignes)
│   ├── 40-service-borodino.yml      # Services pentest (~545 lignes)
│   ├── 45-service-ml-threat-intel.yml # ML threat intel (~75 lignes)
│   └── .gitlab-ci.yml               # Pipeline CI/CD
│
├── volumes/                   # Données persistantes (26 sous-dossiers)
│   ├── alertmanager/                # Règles d'alerte + TLS
│   ├── prometheus/                  # Config + recording rules
│   ├── grafana/                     # Dashboards + provisioning
│   ├── loki/                        # Config pipeline logs
│   ├── tempo/                       # Config tracing distribué
│   ├── faraday/                     # Config serveur vulns
│   ├── nuclei/                      # Templates Nuclei
│   ├── suricata/                    # Règles IDS (emerging-threats)
│   ├── traefik/                     # Config reverse proxy + TLS
│   ├── postfix/                     # Config relay email
│   ├── provisioning/                # .env orchestrateur
│   ├── telegram_bot/                # État et logs bot
│   └── ...
│
├── CLAUDE.md                  # Instructions pour Claude Code
├── BUILD_PROMPT.md            # CE FICHIER
├── .gitignore
└── README.md
```

---

## 4. Stack Docker Swarm détaillé

### 4.1 Stack Core — `01-service-hl.yml` (déployé comme `base`)

#### Réseaux overlay
```yaml
networks:
  monitoring:    # Prometheus scraping, metrics collection
    driver: overlay
  backend:       # Communication inter-services
    driver: overlay
  proxy:         # Ingress Traefik
    driver: overlay
  rsync_network: # Réplication backup
    driver: overlay
  mail:          # Services email
    driver: overlay
    attachable: true
```

#### Services (18+)

| Service | Image | Placement | Réseaux | Ports | Notes |
|---------|-------|-----------|---------|-------|-------|
| **PostgreSQL** | postgres:15 | manager | backend | 5432 | Volume externe `bojemoi`, 6 bases |
| **PgAdmin** | dpage/pgadmin4 | manager | backend, proxy | - | Traefik: pgadmin.bojemoi.lab |
| **Prometheus** | prom/prometheus | manager | monitoring, rsync | 9090 | Rétention 15j, max 10GB, WAL compression |
| **Grafana** | grafana/grafana | manager | monitoring, proxy | 3000 | Backend PostgreSQL |
| **Loki** | grafana/loki | worker | monitoring | 3100 | Agrégation logs |
| **Tempo** | grafana/tempo | manager | monitoring, proxy | 4317/4318/9411 | OTLP gRPC + HTTP + Zipkin |
| **Alertmanager** | prom/alertmanager | manager | monitoring | 9093 | Config: volumes/alertmanager/ |
| **Suricata** | jasonish/suricata | global | monitoring | - | IDS/IPS, CAP_NET_ADMIN, raw sockets |
| **Suricata Exporter** | - | global | monitoring | 9917 | Métriques Prometheus IDS |
| **Traefik** | traefik:v2 | manager | proxy | 80/443 | Let's Encrypt auto-TLS |
| **Provisioning API** | localhost:5000/provisioning | manager | backend, proxy | 28080/9000 | Orchestrateur principal |
| **Node Exporter** | prom/node-exporter | global | monitoring | 9100 | Métriques host |
| **cAdvisor** | gcr.io/cadvisor | global | monitoring | 8080 | Métriques conteneurs |
| **Postgres Exporter** | wrouesnel/postgres_exporter | manager | monitoring | 9187 | Métriques DB |
| **Postfix** | - | manager | mail | 25 | Relay TLS ProtonMail |
| **ProtonMail Bridge** | - | manager | mail | - | SMTP relay sécurisé |
| **Alloy** | grafana/alloy | - | monitoring | - | Agent observabilité |
| **Docker Registry** | registry:2 | manager | - | 5000 | Registry privé local |

### 4.2 Stack Pentest — `40-service-borodino.yml` (déployé comme `borodino`)

#### Réseau additionnel
```yaml
networks:
  pentest:
    driver: overlay
    attachable: true
```

#### Services (13)

| Service | Image | Replicas | Placement | Notes |
|---------|-------|----------|-----------|-------|
| **ak47-service** | localhost:5000/borodino | 15 | workers | Scanner nmap CIDR, max 5/node, CPU 0.5/0.1, RAM 512M/256M |
| **bm12-service** | localhost:5000/borodino | 15 | workers | Scanner nmap services, même contraintes |
| **uzi-service** | localhost:5000/borodino | 5 | workers | Runner Metasploit RPC (msfrpc 192.168.1.47:55553) |
| **zaproxy** | localhost:5000/zaproxy | 1 | - | OWASP ZAP proxy (port 8090) |
| **zap-scanner** | localhost:5000/zap-scanner | 1 | - | Orchestration ZAP automatisée |
| **masscan-scanner** | localhost:5000/tsushima | global | - | Port scanner rapide + VPN |
| **nuclei** | localhost:5000/nuclei | 1 | workers | Scanner vuln par templates |
| **nuclei-api** | localhost:5000/nuclei-api | 1 | - | API REST (port 8001), Traefik route |
| **vulnx** | localhost:5000/vulnx | 1 | workers | Scanner CMS |
| **redis** | redis:7-alpine | 1 | - | Queue jobs pentest |
| **pentest-orchestrator** | localhost:5000/samsonov | 1 | - | Plugin orchestrator daemon |
| **faraday** | localhost:5000/faraday | 1 | - | Vulns management (port 5985), Traefik route |
| **karacho-blockchain** | localhost:5000/karacho | 1 | - | Audit trail (port 5100), Traefik route |

### 4.3 Stack ML — `45-service-ml-threat-intel.yml` (déployé comme `ml-threat-intel`)

| Service | Image | Notes |
|---------|-------|-------|
| **ml-threat-intel-api** | localhost:5000/ml-threat-intel | DB: bojemoi_threat_intel, secrets: VT/AbuseIPDB/OTX/Shodan API keys |

---

## 5. Composant : Orchestrateur de Provisioning (FastAPI)

### 5.1 Configuration (Pydantic BaseSettings)

```python
class Settings(BaseSettings):
    # PostgreSQL
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str            # REQUIS
    POSTGRES_DB: str = "deployments"

    # Gitea (source GitOps)
    GITEA_URL: str                    # https://gitea.bojemoi.me
    GITEA_TOKEN: str                  # REQUIS
    GITEA_REPO_OWNER: str = "bojemoi"
    GITEA_REPO: str = "bojemoi-configs"

    # XenServer
    XENSERVER_URL: str
    XENSERVER_HOST: str
    XENSERVER_USER: str = "root"
    XENSERVER_PASS: str               # REQUIS

    # Docker Swarm
    DOCKER_HOST: str = "unix:///var/run/docker.sock"
    DOCKER_SWARM_MANAGER: bool = True

    # Sécurité
    IP_VALIDATION_ENABLED: bool = True
    ALLOWED_COUNTRIES: str = "FR,DE,CH,BE,LU,NL,AT"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Scheduler
    CHECK_INTERVAL_MINUTES: int = 5
    ENABLE_SCHEDULER: bool = True
```

### 5.2 Modèles de données

```python
# Enums
class OSType(str, Enum):
    ALPINE = "alpine"
    UBUNTU = "ubuntu"
    DEBIAN = "debian"

class Environment(str, Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEV = "dev"

class DeploymentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"

# Requêtes
class VMDeployRequest(BaseModel):
    name: str                         # Nom de la VM
    template: str                     # Template cloud-init
    os_type: OSType
    cpu: int = 2                      # 1-32
    memory: int = 2048                # MB, min 512, max 131072
    disk: int = 20                    # GB, min 10, max 2048
    network: str = "default"
    environment: Environment
    variables: Dict[str, Any] = {}    # Variables Jinja2 additionnelles

class ContainerDeployRequest(BaseModel):
    name: str
    image: str
    replicas: int = 1
    environment: Dict[str, str] = {}
    ports: List[str] = []             # "80:80"
    networks: List[str] = []
    labels: Dict[str, str] = {}       # Labels Traefik etc.
```

### 5.3 Endpoints API

```
POST /api/v1/vm/deploy                    # Déployer VM sur XenServer
POST /api/v1/container/deploy             # Déployer service Docker Swarm
POST /api/v1/service/deploy               # Déployer service Swarm
POST /deploy/all                          # Déploiement complet infra
GET  /api/v1/deployments                  # Lister déploiements (paginé)
GET  /api/v1/blockchain/verify            # Vérifier intégrité chaîne audit
GET  /health                              # Probe liveness
GET  /metrics                             # Métriques Prometheus (port 9000)
GET  /status                              # Santé des connexions
```

### 5.4 Schéma base de données

```sql
-- Table des déploiements
CREATE TABLE deployments (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,          -- 'vm', 'container', 'service'
    name VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,
    resource_ref VARCHAR(255),          -- ID XenServer ou Docker
    status VARCHAR(50) NOT NULL,        -- pending/running/success/failed
    error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_deployments_type ON deployments(type);
CREATE INDEX idx_deployments_status ON deployments(status);

-- Blockchain d'audit
CREATE TABLE deployment_blocks (
    id SERIAL PRIMARY KEY,
    block_number INTEGER UNIQUE NOT NULL,
    previous_hash VARCHAR(64),
    current_hash VARCHAR(64) NOT NULL,  -- SHA-256
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

### 5.5 Services internes

| Service | Rôle | Détails clés |
|---------|------|--------------|
| **gitea_client** | Fetch configs depuis Git | Cache ETag en mémoire, TTL 5min, API raw file |
| **xenserver_client** | Déploiement VM XenAPI | 23 codes erreur documentés, retry auto, SSL self-signed |
| **docker_client** | Gestion Swarm | Création services avec replicas, networks, labels Traefik |
| **cloudinit_gen** | Templating cloud-init | Jinja2, validation variables (bloque eval/exec/__import__) |
| **database** | PostgreSQL async | asyncpg + SQLAlchemy 2.0 ORM, connection pool |
| **blockchain** | Audit trail | SHA-256 chain, vérification intégrité, immutable |
| **ip2location_client** | Géolocalisation | Validation pays source, bypass IP privées |

### 5.6 Middleware

- **IP Validation** : Bloque requêtes hors pays autorisés (FR/DE/CH/BE/LU/NL/AT). Bypass pour IPs privées (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
- **Metrics** : Enregistrement automatique latence/status code vers Prometheus

### 5.7 Flux de déploiement VM

```
1. POST /api/v1/vm/deploy avec VMDeployRequest
2. Middleware vérifie IP source (géolocalisation)
3. Fetch template cloud-init depuis Gitea (cache ETag)
4. Rendu Jinja2 avec variables utilisateur
5. Appel XenAPI pour création VM
6. Polling statut VM jusqu'au boot
7. Enregistrement dans blockchain (hash SHA-256 chaîné)
8. Mise à jour table deployments en PostgreSQL
9. Métriques Prometheus incrémentées
10. Retour deployment_id + référence VM
```

---

## 6. Composant : Orchestrateur Pentest (Plugin Architecture)

### 6.1 Architecture

```python
class PluginManager:
    """Auto-découverte des plugins depuis plugins/plugin_*.py"""
    # Charge dynamiquement chaque module
    # Extrait les fonctions callables avec métadonnées
    # Gère le cycle de vie des plugins

class PentestOrchestrator:
    """Orchestre les scans multi-outils"""
    # Mode daemon via Redis pour exécution async
    # Agrégation des résultats vers Faraday
    # Gestion des sessions de scan
```

### 6.2 Classes de base

```python
class ScanType(str, Enum):
    FULL = "full"
    WEB = "web"
    NETWORK = "network"
    VULN = "vuln"
    CMS = "cms"
    RECON = "recon"
    API = "api"

class Severity(str, Enum):
    CRITICAL = "critical"    # CVSS 9.0-10.0
    HIGH = "high"            # CVSS 7.0-8.9
    MEDIUM = "medium"        # CVSS 4.0-6.9
    LOW = "low"              # CVSS 0.1-3.9
    INFO = "info"            # Informatif

@dataclass
class Finding:
    """Résultat de vulnérabilité normalisé"""
    name: str
    severity: Severity
    description: str
    target: str
    port: Optional[int]
    cvss: Optional[float]
    cve: Optional[str]
    evidence: Optional[str]
    remediation: Optional[str]
    plugin_name: str
```

### 6.3 Plugins

| Plugin | Outil | Fonctionnalité |
|--------|-------|----------------|
| **plugin_nuclei** | Nuclei | Scan par templates YAML, détection vulns connues |
| **plugin_masscan** | Masscan | Port scan ultra-rapide (10K-100K pps), découverte réseau |
| **plugin_zap** | OWASP ZAP | Scan apps web automatisé, spider + active scan |
| **plugin_burp** | Burp Suite | Scan Enterprise via API, crawl + audit |
| **plugin_vulnx** | VulnX | Détection vulnérabilités CMS (WordPress, Joomla, etc.) |
| **plugin_metasploit** | Metasploit | Exploitation automatisée via MSFRPC |
| **plugin_faraday** | Faraday | Agrégation et gestion des vulnérabilités |
| **plugin_nmap** | Nmap | Cartographie réseau, détection OS et services |

### 6.4 Flux de scan

```
1. Configuration cible + type de scan (ScanType)
2. PluginManager charge plugins depuis plugins/plugin_*.py
3. Exécution séquence de scan (ex: Masscan → Nmap → ZAP → Nuclei)
4. Chaque plugin retourne List[Finding] normalisé
5. Agrégation résultats avec breakdown par sévérité
6. Sauvegarde locale JSON
7. Import vers workspace Faraday (import_results.py)
8. Stockage Redis pour traitement async
```

---

## 7. Composant : Borodino (Scanning armé)

### 7.1 Image Docker

```dockerfile
# Dockerfile.borodino
FROM alpine:3.22
# Ruby 3.5.0-preview compilé from source (pour Metasploit)
# Rust compiler (dépendance MSF)
# Metasploit Framework depuis git
# PostgreSQL client (psql pour requêtes directes)
# Nmap avec scripts
# OpenVPN client
```

### 7.2 Scripts de scanning

#### thearm_ak47 (ash/shell) — Scanner CIDR
- Sélectionne un CIDR aléatoire depuis `ip2location` DB
- Utilise `TABLESAMPLE SYSTEM()` (pas `ORDER BY RANDOM()` — critique pour performance)
- Lance `nmap` sur le CIDR
- Insère résultats dans base `msf` (tables hosts/services)
- **15 replicas** sur workers

#### thearm_bm12 (python) — Scanner Services
- Sélectionne un host aléatoire depuis `msf.hosts` via `TABLESAMPLE SYSTEM()`
- Lance `nmap` avec scripts de détection de services
- Met à jour table `services` dans base `msf`
- **15 replicas** sur workers

#### thearm_uzi (python) — Runner Metasploit
- Sélectionne un host Linux aléatoire via `TABLESAMPLE SYSTEM()`
- Se connecte à MSFRPC (192.168.1.47:55553)
- Exécute exploits adaptés à l'OS détecté
- Requêtes SQL paramétrées (pas d'injection)
- **5 replicas** sur workers

### 7.3 Optimisation critique

> **IMPORTANT** : Ne JAMAIS utiliser `ORDER BY RANDOM() LIMIT 1` sur les tables msf (6.15M hosts, 33.7M services).
> Utiliser `TABLESAMPLE SYSTEM(0.001)` avec fallback. Cette optimisation a réduit le CPU PostgreSQL de 459% à 29%.

---

## 8. Composant : Karacho (Blockchain Audit)

### 8.1 Architecture
- **FastAPI** service (~33KB) exposé port 5100
- **PostgreSQL** backend (base `karacho`)
- Chaîne de blocs SHA-256 avec hash du bloc précédent
- Service daemon avec auto-restart
- Client REST pour intégration avec l'orchestrateur

### 8.2 Structure d'un bloc
```python
{
    "block_number": int,            # Séquentiel
    "previous_hash": str,           # SHA-256 du bloc N-1
    "current_hash": str,            # SHA-256(previous_hash + data)
    "deployment_type": str,         # "vm" | "container"
    "name": str,                    # Nom de la ressource
    "config": dict,                 # Configuration complète
    "resource_ref": str,            # ID XenServer ou Docker
    "status": str,                  # Statut du déploiement
    "source_ip": str,               # IP de l'appelant
    "source_country": str,          # Pays (2 lettres)
    "created_at": datetime
}
```

---

## 9. Composant : Koursk (Backup distribué)

### 9.1 Architecture Master/Slave
- **koursk-2** : Master, orchestre les jobs rsync
- **koursk/koursk-1** : Slaves, reçoivent les réplications

### 9.2 Configuration des jobs
```json
{
    "jobs": [
        {"name": "bojemoi", "source": "/opt/bojemoi/", "interval_minutes": 10},
        {"name": "bojemoi_boot", "source": "/opt/bojemoi_boot/", "interval_minutes": 10},
        {"name": "bojemoi-telegram", "source": "/opt/bojemoi-telegram/", "interval_minutes": 10},
        {"name": "bojemoi-ml-threat", "source": "/opt/bojemoi-ml-threat/", "interval_minutes": 10}
    ]
}
```

### 9.3 Métriques
- Prometheus metrics pour chaque job (succès/échec, durée, taille)

---

## 10. Monitoring & Observabilité

### 10.1 Stack complète

```
Prometheus (métriques) ──→ Grafana (visualisation)
     ↑                          ↑
Node Exporter (host)        Loki (logs)
cAdvisor (containers)       Tempo (traces)
Postgres Exporter (DB)      Alertmanager (alertes)
Suricata Exporter (IDS)
Alloy (multi-signal)
Postfix Exporter (mail)
```

### 10.2 Configuration Prometheus
- **Rétention** : 15 jours
- **Taille max TSDB** : 10 GB
- **WAL compression** : activée
- **Scrape targets** : tous les exporters + services avec /metrics
- **Recording rules** : volumes/prometheus/

### 10.3 Alertmanager
- Configuration : `volumes/alertmanager/alertmanager.yml`
- Notifications via email (Postfix → ProtonMail Bridge)
- API de silence pour suppression d'alertes pendant les déploiements

### 10.4 Suricata IDS
- Déploiement global (1 instance par nœud)
- Règles : emerging-threats + custom
- CAP_NET_ADMIN pour accès raw sockets
- Métriques exportées vers Prometheus (port 9917)

---

## 11. Sécurité

### 11.1 Couches de sécurité

| Couche | Mécanisme | Détails |
|--------|-----------|---------|
| **Réseau** | Overlay networks | Segmentation monitoring/backend/proxy/pentest/mail |
| **Ingress** | Traefik + TLS | Let's Encrypt automatique, terminaison TLS |
| **API** | IP Validation | Contrôle par pays (géolocalisation IP2Location) |
| **Auth** | JWT | Framework d'authentification |
| **Audit** | Blockchain | SHA-256 hash chain immuable |
| **IDS/IPS** | Suricata | Détection intrusions, déployé globalement |
| **Threat Intel** | CrowdSec | IP blocking basé sur réputation |
| **Secrets** | Docker Secrets | ssh_private_key, telegram tokens, API keys |
| **Cloud-init** | Validation Jinja2 | Bloque eval(), exec(), __import__() dans templates |
| **DB** | Requêtes paramétrées | Protection injection SQL (fix borodino/uzi) |
| **Email** | ProtonMail Bridge | Chiffrement email via relay TLS |

### 11.2 Docker Secrets (externes)
```
ssh_private_key          # Opérations Git
telegram_bot_token       # Notifications Telegram
telegram_api_credentials # Auth API Telegram
proton_username          # Credentials email
proton_password
vt_api_key               # VirusTotal
abuseipdb_api_key        # AbuseIPDB
otx_api_key              # AlienVault OTX
shodan_api_key           # Shodan
```

---

## 12. CI/CD Pipeline

### 12.1 GitLab CI Stages
```yaml
stages:
  - validate    # Docker Compose syntax + env vars
  - build       # Image compilation + registry push
  - test        # Unit + integration tests
  - security    # Trivy vulnerability scanning
  - deploy      # docker stack deploy
  - verify      # Health checks post-déploiement
  - notify      # Notifications succès/échec
```

### 12.2 Processus de build et déploiement
```bash
# 1. Build image
cd /opt/bojemoi/<composant>
docker build -f Dockerfile.<composant> -t localhost:5000/<composant>:latest .

# 2. Push au registry local
docker push localhost:5000/<composant>:latest

# 3. Déployer la stack
docker stack deploy -c stack/<stack-file>.yml <stack-name> --resolve-image always --prune

# 4. OU forcer la mise à jour d'un service spécifique (avec digest pour garantir le refresh)
docker service update \
    --image localhost:5000/<composant>:latest@sha256:<digest> \
    --force --detach --update-parallelism 5 \
    <stack>_<service>
```

---

## 13. Contraintes de ressources

### Règles de placement
- **Manager node** : PostgreSQL, Prometheus, Grafana, Traefik, PgAdmin, Tempo, Provisioning API
- **Worker nodes** : Tous les scanners (borodino, nuclei, vulnx, masscan)
- **Global** : Suricata, Node Exporter, cAdvisor, Suricata Exporter

### Limites par service
```yaml
# Borodino (ak47, bm12, uzi)
resources:
  limits: { cpus: "0.5", memory: "512M" }
  reservations: { cpus: "0.1", memory: "256M" }
deploy:
  replicas: 15  # (ak47/bm12) ou 5 (uzi)
  placement:
    max_replicas_per_node: 5
    constraints: [node.role == worker]

# Nuclei / VulnX
resources:
  limits: { cpus: "2", memory: "2G" }
  reservations: { cpus: "0.5", memory: "512M" }

# Prometheus
storage.tsdb.retention.time: 15d
storage.tsdb.retention.size: 10GB
```

---

## 14. Bases de données PostgreSQL

| Base | Usage | Taille estimée |
|------|-------|----------------|
| **msf** | Metasploit Framework — hosts (6.15M), services (33.7M) | ~9 GB |
| **ip2location** | Géolocalisation CIDR pour ciblage scan | Variable |
| **faraday** | Findings de vulnérabilités agrégés | Variable |
| **karacho** | Blockchain audit trail immuable | Croissante |
| **deployments** | État orchestrateur (VMs, conteneurs) | Petit |
| **grafana** | Configuration dashboards | Petit |
| **bojemoi_threat_intel** | Intelligence de menaces ML | Variable |

---

## 15. Routage Traefik

| Service | Route | Port interne |
|---------|-------|--------------|
| Grafana | grafana.bojemoi.lab | 3000 |
| Prometheus | prometheus.bojemoi.lab | 9090 |
| PgAdmin | pgadmin.bojemoi.lab | 5050 |
| Tempo | tempo.bojemoi.lab | 3200 |
| Faraday | faraday.bojemoi.lab | 5985 |
| Nuclei API | nuclei.bojemoi.lab | 8001 |
| Karacho | karacho.bojemoi.lab | 5100 |
| ZAP Proxy | zap.bojemoi.lab | 8090 |
| Threat Intel | threat-intel.bojemoi.lab.local | 8000 |
| Provisioning | (port direct 28080) | 8000 |

---

## 16. .gitignore

```gitignore
# Secrets et certificats
*.key
*.pem
*.crt
**/secrets/
**/*secret*
**/*password*
**/privatekey-*
**/id_rsa
**/id_ed25519

# Variables d'environnement
.env
*.env.local
*.env.production

# VPN credentials
**/auth.txt

# Fichiers temporaires
*.tmp
*.log
*.swp
*~
.DS_Store
*.socket
eve.json

# Sauvegardes
*.bak
*.backup

# Données sensibles
**/data/

# IDE
.vscode/
.idea/
```

---

## 17. Tech Stack complet

| Catégorie | Technologies |
|-----------|-------------|
| **Langage principal** | Python 3.11 |
| **API** | FastAPI 0.109, Uvicorn 0.27, Pydantic 2.5 |
| **ORM** | SQLAlchemy 2.0.25, asyncpg 0.29 |
| **Base de données** | PostgreSQL 15 |
| **HTTP async** | httpx 0.26 |
| **Templates** | Jinja2 3.1.3, PyYAML 6.0.1 |
| **Scheduler** | APScheduler |
| **Docker** | docker-py 7.0, Docker Swarm |
| **VM** | XenAPI (XenServer/XCP-ng) |
| **Migrations** | Alembic 1.13.1 |
| **CLI** | Click + Rich |
| **Monitoring** | Prometheus, Grafana, Loki, Tempo, Alertmanager |
| **Sécurité** | Suricata, CrowdSec, Traefik TLS |
| **Scanning** | Nmap, Metasploit 6, OWASP ZAP, Nuclei, Masscan, Burp, VulnX |
| **Messaging** | Redis 7 |
| **Backup** | rsync (master/slave) |
| **CI/CD** | GitLab CI, Gitea |
| **Conteneurs** | Alpine Linux, Docker Registry v2 |
| **Email** | Postfix, ProtonMail Bridge |
| **ML** | Python ML stack (threat intel) |

---

## 18. Instructions de reconstruction

### Phase 1 : Infrastructure de base
1. Provisionner 3 nœuds (1 manager + 2 workers)
2. Initialiser Docker Swarm (`docker swarm init` sur manager, join sur workers)
3. Déployer registry local (`docker service create --name registry -p 5000:5000 registry:2`)
4. Créer réseaux overlay : monitoring, backend, proxy, rsync_network, mail, pentest
5. Créer volume externe PostgreSQL
6. Déployer stack `01-service-hl.yml` (PostgreSQL, Traefik, Prometheus, Grafana, etc.)
7. Initialiser les 7 bases PostgreSQL
8. Configurer Gitea avec repo `bojemoi-configs` pour templates cloud-init

### Phase 2 : Orchestrateur
1. Développer l'orchestrateur FastAPI (`provisioning/`)
2. Implémenter les 7 services (gitea, xenserver, docker, cloudinit, database, blockchain, ip2location)
3. Ajouter middleware IP validation + metrics
4. Configurer Alembic migrations
5. Builder et pusher image `localhost:5000/provisioning:latest`

### Phase 3 : Pentest Orchestrator
1. Développer le framework plugin (`samsonov/pentest_orchestrator/`)
2. Implémenter les 8 plugins (nuclei, masscan, zap, burp, vulnx, metasploit, faraday, nmap)
3. Développer Nuclei API wrapper (`samsonov/nuclei_api/`)
4. Builder images : samsonov, nuclei-api, vulnx

### Phase 4 : Scanners
1. Builder image Borodino (Alpine + Ruby + Metasploit from source)
2. Développer scripts ak47/bm12/uzi avec `TABLESAMPLE SYSTEM()`
3. Builder image Tsushima (masscan + VPN pipeline)
4. Builder images ZAP (oblast, oblast-1)
5. Déployer stack `40-service-borodino.yml`

### Phase 5 : Services auxiliaires
1. Développer et déployer Karacho (blockchain audit)
2. Configurer Koursk rsync master/slaves
3. Configurer Suricata IDS avec règles emerging-threats
4. Configurer Alertmanager + notifications email
5. Déployer stack ML threat intel `45-service-ml-threat-intel.yml`

### Phase 6 : CI/CD & Ops
1. Configurer GitLab CI pipeline
2. Configurer scripts de build (`scripts/bojemoiBuild.sh`, `cccp.sh`)
3. Configurer Grafana dashboards (provisioning automatique)
4. Tester flux end-to-end : déploiement VM → audit blockchain → monitoring

---

## 19. Leçons apprises et pièges à éviter

1. **`ORDER BY RANDOM()` est catastrophique** sur tables de millions de lignes → utiliser `TABLESAMPLE SYSTEM()`
2. **`docker stack deploy` avec tag `:latest`** ne force PAS le rolling update → utiliser `--force` avec digest d'image
3. **Rolling update parallelism 1** est très lent pour 15+ replicas → utiliser `--update-parallelism 5`
4. **`max_replicas_per_node: 5`** avec 2 workers = 10 max replicas (pas 15 comme configuré)
5. **BusyBox `top`** (Alpine) ne supporte pas `-o` → utiliser `top -bn1` simple
6. **Metasploit RPC** doit être accessible à 192.168.1.47:55553 pour que uzi-service fonctionne
7. **Toujours utiliser des requêtes SQL paramétrées** — l'injection SQL a été trouvée et corrigée dans thearm_uzi
8. **Prometheus consomme ~950 MB RAM** — c'est le plus gros consommateur mémoire après PostgreSQL
9. **PostgreSQL partage une seule instance** pour 7+ bases — surveiller CPU/RAM en continu
