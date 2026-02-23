# BUILD PROMPT: BOJEMOI LAB — Plateforme Infrastructure-as-Code

## Vue d'ensemble

**Bojemoi Lab** est une plateforme hybride d'Infrastructure-as-Code déployée sur Docker Swarm (4 nœuds). Elle combine sécurité offensive, CTI, monitoring et orchestration de déploiement.

**Environnement :**
- Manager : meta-76 (Alpine/BusyBox, i9-10900X, 16 GB RAM)
- Workers : meta-68, meta-69, meta-70 (contrainte `node.role == worker`)
- Registry local : `localhost:5000`
- Gitea : `gitea.bojemoi.me`

---

## Architecture des composants

### 1. Orchestrateur de déploiement (`provisioning/`)

```
provisioning/orchestrator/app/
├── main.py                    # FastAPI + lifespan, middleware IP, /metrics Prometheus
├── config.py                  # Pydantic BaseSettings (.env)
├── models/schemas.py          # Enums OSType, Environment, DeploymentStatus + modèles
├── services/
│   ├── gitea_client.py        # Templates cloud-init depuis Gitea
│   ├── xenserver_client_real.py # Déploiement VM via XenAPI
│   ├── docker_client.py       # Gestion services Docker Swarm
│   ├── cloudinit_gen.py       # Templates Jinja2 cloud-init
│   ├── database.py            # PostgreSQL asyncpg (table deployments)
│   ├── blockchain.py          # Chaîne SHA-256 (appels à karacho)
│   └── ip2location_client.py  # Validation géographique des requêtes
└── middleware/
    └── ip_validation.py       # Blocage par pays (whitelist Europe occidentale)
```

**Endpoints API :**
```
POST /api/v1/vm/deploy              # Déployer une VM sur XenServer
POST /api/v1/container/deploy       # Déployer un service Docker Swarm
GET  /api/v1/deployments            # Lister les déploiements (paginé)
GET  /api/v1/deployments/{id}       # Détail d'un déploiement
DELETE /api/v1/deployments/{id}     # Supprimer un déploiement
GET  /api/v1/blockchain/blocks      # Blocs de la chaîne d'audit
GET  /api/v1/blockchain/verify      # Vérifier l'intégrité de la chaîne
GET  /api/v1/blockchain/stats       # Statistiques de la chaîne
GET  /api/v1/templates              # Templates cloud-init disponibles (Gitea)
GET  /metrics                       # Prometheus metrics
GET  /health                        # Liveness probe
```

**Workflow déploiement VM :**
1. `POST /api/v1/vm/deploy` avec `VMDeployRequest`
2. Middleware valide l'IP source (pays autorisé ou réseau privé)
3. Template cloud-init récupéré depuis Gitea (`cloud-init/{template}.yaml`)
4. Rendu Jinja2 avec les variables du contexte
5. Création VM sur XenServer via XenAPI
6. Enregistrement blockchain (karacho) + PostgreSQL (deployments)
7. Retour `deployment_id` et référence VM

---

### 2. Borodino — Workers de scan Metasploit (`borodino/`)

Image : `ruby:3.3-alpine`, MSF Framework depuis GitHub, nmap, pymetasploit3, ProtonVPN.

```
borodino/
├── Dockerfile.borodino
├── thearm_ak47          # Ash : scan CIDR nmap via msfconsole (15 répliques)
├── thearm_bm12          # Python : fingerprinting profond + classification (15 répliques)
├── thearm_uzi           # Python : exploitation MSF + alertes Telegram (1 réplique)
├── start_uzi.sh         # Wrapper : lance msfrpcd + rebuild cache + thearm_uzi
└── list_vpn/            # Configs ProtonVPN .ovpn
```

**ak47** (ash) : sélectionne des CIDRs depuis `ip2location_db1` via `TABLESAMPLE SYSTEM(1)`, exécute `db_nmap -sS -A -O` via msfconsole, marque le statut nmap (1→2).

**bm12 v2** (Python) : sélectionne un host aléatoire (`TABLESAMPLE SYSTEM(0.001)`), identifie ses services ouverts, mappe vers 25 catégories NSE ciblées (http, ssh, smtp, smb, dns, mysql, rdp…), lance un seul msfconsole par host (timeout 600s), classifie le serveur (web/mail/dns/database/file_server/vpn_proxy/voip/iot_embedded/remote_access), stocke dans `hosts.comments`, `hosts.scan_details` (JSON), `hosts.scan_status='bm12_v2'`.

**uzi** (Python) : MsfRpcClient sur port 55553 (local via `start_uzi.sh`), sélectionne des hosts Linux aléatoires, itère les modules exploit Linux post-2021, tente chaque exploit avec chaque payload linux, alerte Telegram en cas de session ouverte.

---

### 3. Samsonov — Orchestrateur Pentest (`samsonov/`)

```
samsonov/
├── Dockerfile.samsonov
├── pentest_orchestrator/
│   ├── main.py              # PentestOrchestrator + PluginManager (daemon Redis)
│   └── plugins/
│       ├── plugin_nuclei.py
│       ├── plugin_masscan.py
│       ├── plugin_zap.py
│       ├── plugin_burp.py
│       ├── plugin_vulnx.py
│       ├── plugin_metasploit.py
│       └── plugin_faraday.py
├── nuclei_api/              # FastAPI wrapper Nuclei
├── vulnx_wrapper/           # Wrapper VulnX CMS scanner
├── bojemoi-mitre-attack/    # Copie de la lib partagée
└── scripts/
    ├── metrics_exporter.py  # Prometheus metrics pentest
    └── task_queue.py        # File Redis
```

**Pipeline scan :** Masscan → ZAP spider/active → Burp passive → Nuclei → VulnX → Metasploit

**Commandes Redis** (`pentest:commands`) : `scan`, `russia_scan`, `country_scan`, `status`, `list`, `reload`

**Types de scan :** `full`, `web`, `network`, `vuln`, `cms`

---

### 4. Bibliothèque MITRE ATT&CK (`bojemoi-mitre-attack/`)

Package Python partagé `bojemoi-mitre-attack` v1.0.0, embarqué dans plusieurs images.

```
bojemoi_mitre_attack/
├── models.py           # TechniqueMapping, AttackMapping
├── mapper.py           # Logique de mapping générique
├── formatters.py       # Formatage des résultats
└── mappings/
    ├── suricata.py     # 35+ catégories Suricata → ATT&CK (technique_id, tactic, confiance)
    ├── vulnerability.py
    └── osint.py
```

Utilisé par : `suricata-attack-enricher`, `samsonov`, `vigie`.

---

### 5. Suricata Attack Enricher (`suricata-attack-enricher/`)

Service Python async qui suit `eve.json` de Suricata en temps réel, mappe chaque alerte vers ATT&CK via `bojemoi_mitre_attack`, insère en batch dans PostgreSQL (`bojemoi_threat_intel.suricata_attack_alerts`). Batch 50 entrées / flush 5s.

Déployé en `docker-compose` avec Suricata (`network_mode: host`).

---

### 6. Services CTI

| Service | Rôle |
|---|---|
| **razvedka** | Surveille canaux Telegram/Twitter hacktvistes (KillNet, CyberArmyOfRussia…), score l'intention DDoS ciblant la France, alerte Alertmanager + Telegram |
| **vigie** | Scrape flux RSS ANSSI/CERT-FR, filtre par watchlist produits, alerte sur nouvelles vulnérabilités |
| **dozor** | Génère les règles blocklist Suricata depuis threat intel, reload via socket Unix |
| **ml-threat-intel** | Classificateur ML d'IoC (VT/AbuseIPDB/OTX/Shodan/Anthropic APIs), API FastAPI |

---

### 7. Honeypot (`medved/`)

Multi-protocole : SSH :22, HTTP :8888, RDP :3389, SMB :445, FTP :2121, Telnet :2323, Elasticsearch :9200. Logs dans `msf` DB + Faraday.

---

### 8. Karacho — Blockchain Audit (`karacho/`)

API REST PostgreSQL pour la chaîne d'audit immuable SHA-256. Chaque déploiement VM/container crée un bloc lié au précédent. Appelé par l'orchestrateur provisioning.

---

### 9. Scanners complémentaires

| Service | Rôle |
|---|---|
| **tsushima** | Masscan rapide par CIDR/pays depuis `ip2location` DB |
| **oblast / oblast-1** | OWASP ZAP proxy + scanner actif, résultats → Faraday |
| **medved** | Honeypot multi-protocoles |

---

## Stacks Docker Swarm (`stack/`)

| Fichier | Stack | Services principaux |
|---|---|---|
| `01-service-hl.yml` | **base** (manager) | postgres, grafana, prometheus, loki, tempo, alloy, alertmanager, cadvisor, node-exporter, postfix, rsync-master/slave, orchestrator, pgadmin, suricata-exporter, postgres-exporter |
| `01-suricata-host.yml` | **suricata** (compose, host net) | suricata, suricata-attack-enricher |
| `40-service-borodino.yml` | **borodino** (workers) | ak47-service×15, bm12-service×15, uzi-service×1, karacho-blockchain, masscan-scanner, nuclei, nuclei-api, vulnx, redis, pentest-orchestrator, faraday, zaproxy, zap-scanner, redis-exporter, pentest-exporter |
| `45-service-ml-threat-intel.yml` | **ml-threat-intel** (workers) | ml-threat-intel-api |
| `46-service-razvedka.yml` | **razvedka** (workers) | razvedka |
| `47-service-vigie.yml` | **vigie** (workers) | vigie |
| `48-service-dozor.yml` | **dozor** (workers) | dozor |
| `60-service-telegram.yml` | **telegram** (workers) | telegram-bot |
| `65-service-medved.yml` | **medved** (workers) | medved-honeypot |

---

## Base de données PostgreSQL

**Instance partagée** : `base_postgres` sur manager (meta-76), port 5432.

| Base | Usage |
|---|---|
| `msf` | Metasploit DB — hosts (6,15M), services (33,7M) — 9 GB |
| `ip2location` | CIDRs géolocalisation pour ciblage des scans |
| `faraday` | Findings sécurité |
| `deployments` | État orchestrateur |
| `grafana` | Config dashboards |
| `bojemoi_threat_intel` | Alertes Suricata enrichies ATT&CK |
| `karacho` | Blockchain audit déploiements |

**Colonnes clés `msf.hosts` pour classification bm12 :**
- `purpose` : server/device/firewall/router/client
- `comments` : texte libre — bm12 écrit `"bm12: {type} (confidence: N%)"`
- `scan_details` : JSON — classification complète avec scores et evidence
- `scan_status` : `"bm12_v2"` marque les hosts scannés par la v2
- `last_scanned` : date de dernier scan

---

## Variables d'environnement

```env
# PostgreSQL
POSTGRES_HOST=192.168.1.76
POSTGRES_PORT=5432
POSTGRES_DB=deployments
POSTGRES_USER=orchestrator
POSTGRES_PASSWORD=secret

# Gitea
GITEA_URL=https://gitea.bojemoi.me
GITEA_TOKEN=xxx
GITEA_REPO=bojemoi-configs

# XenServer
XENSERVER_URL=https://xenserver.local
XENSERVER_USER=root
XENSERVER_PASSWORD=xxx

# IP Validation
IP_VALIDATION_ENABLED=true
ALLOWED_COUNTRIES=FR,DE,CH,BE,LU,NL,AT

# MSF RPC (uzi)
MSF_HOST=127.0.0.1
MSF_PORT=55553
MSF_USER=msf
MSF_PASS=xxx

# Mode
MODE_RUN=1          # 0=disabled, 1=enabled (uzi)
SCAN_TIMEOUT=600    # bm12 timeout en secondes
PYTHONUNBUFFERED=1
```

---

## Réseaux Overlay

| Réseau | Usage |
|---|---|
| `monitoring` | Prometheus, Grafana, Loki, exporters |
| `backend` | Services internes, bases de données |
| `frontend` | Services exposés publiquement |
| `proxy` | Routage Traefik |
| `mail` | Postfix, ProtonMail Bridge |
| `rsync_network` | Synchronisation koursk master/slave |

**Ports clés :**
- 80/443 — Traefik
- 8000/28080 — Orchestrateur API
- 9090 — Prometheus
- 3000 — Grafana
- 3100 — Loki
- 4317/4318 — Tempo (OTLP)
- 5432 — PostgreSQL
- 55553 — MSF RPC (local, uzi)

---

## Déploiement

### Build & push image borodino
```bash
cd /opt/bojemoi/borodino
docker build -f Dockerfile.borodino -t localhost:5000/borodino:latest .
docker push localhost:5000/borodino:latest
DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' localhost:5000/borodino:latest | cut -d@ -f2)
docker service update --image localhost:5000/borodino:latest@$DIGEST \
  --force --update-parallelism 5 borodino_ak47-service
```

### Deploy stack
```bash
docker stack deploy -c stack/40-service-borodino.yml borodino \
  --resolve-image always --prune
```

### Accès workers (IP dynamique)
```bash
IP=$(docker node inspect meta-68 --format '{{.Status.Addr}}')
ssh -p 4422 -i /home/docker/.ssh/meta76_ed25519 \
  -o StrictHostKeyChecking=no docker@$IP
```

### Orchestrateur
```bash
cd provisioning
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Test API
```bash
# Déployer une VM
curl -X POST http://localhost:8000/api/v1/vm/deploy \
  -H "Content-Type: application/json" \
  -d '{"name":"test-vm","template":"webserver","os_type":"alpine","cpu":2,"memory":2048,"environment":"dev","variables":{}}'

# Vérifier la chaîne blockchain
curl http://localhost:8000/api/v1/blockchain/verify

# Santé
curl http://localhost:8000/health
```

---

## Sécurité

- **Validation IP** : whitelist par pays (Europe Occ.), bypass pour IPs privées RFC1918
- **Blockchain** : chaîne SHA-256 immuable pour chaque déploiement (karacho)
- **Secrets Docker** : mots de passe injectés via `docker secret` (jamais en clair dans les stacks)
- **VPN** : ak47/bm12/uzi tournent via ProtonVPN (.ovpn embarqué)
- **CORS** : configurer les origines autorisées en production
- **Socket Docker** : accès via `docker-socket-proxy` (telegram-bot)
