# Architecture — Bojemoi Lab

## Vue d'ensemble

Bojemoi Lab est une infrastructure as-code basée sur **Docker Swarm** (4 nœuds) combinant :
- Orchestration de services conteneurisés via YAML Swarm
- Pentest automatisé (scanning, exploitation, reporting)
- Threat intelligence (ML, CTI, OSINT, honeypots)
- Monitoring complet (métriques, logs, traces, alertes)
- Infrastructure C2 red team via redirecteurs Fly.io

---

## Topologie Swarm

```
                        ┌──────────────────────────────────────┐
                        │         meta-76 (Manager)            │
                        │  Intel i9-10900X · 8 cores · 16 GB   │
                        │  Alpine/BusyBox · Docker 29.1.5       │
                        │  IP: 192.168.1.121 (DHCP)            │
                        │                                       │
                        │  Services : base, boot stacks         │
                        │  Registre local : localhost:5000       │
                        └──────────────────┬───────────────────┘
                                           │ Swarm overlay
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
   ┌──────────▼──────────┐    ┌────────────▼────────┐    ┌─────────────▼───────┐
   │   meta-68 (Worker)  │    │  meta-69 (Worker)   │    │  meta-70 (Worker)   │
   │  pentest, storage   │    │  pentest, rsync     │    │  pentest, storage   │
   │  defectdojo, rsync  │    │  IP: dynamic        │    │  rsync.slave        │
   │  nvidia.vgpu (T400) │    │                     │    │  Suricata IDS       │
   └─────────────────────┘    └─────────────────────┘    └─────────────────────┘
         Workers only — tous les stacks sauf base/boot
```

**Accès SSH workers** : IPs dynamiques (DHCP) — résoudre via `docker node inspect <node> --format '{{.Status.Addr}}'`
```bash
ssh -p 4422 -i /home/docker/.ssh/meta76_ed25519 -o StrictHostKeyChecking=no docker@<IP>
```

---

## Stacks Docker Swarm

### Règles de placement
| Nœud | Rôle | Stacks |
|------|------|--------|
| meta-76 | Manager | `base` (01), `boot` (00) — services partagés |
| meta-68/69/70 | Workers | Tous les autres stacks (`node.role == worker`) |
| meta-68 seul | GPU | `ollama`, `dcgm-exporter` (`nvidia.vgpu == true`) |
| meta-70 seul | IDS | `suricata-exporter` (socket dépendant) |

### Inventaire des stacks

| Fichier | Stack | Services clés |
|---------|-------|---------------|
| `01-service-hl.yml` | **base** | postgres, prometheus, grafana, loki, tempo, alertmanager, alloy, node-exporter\*, cadvisor\*, postfix, protonmail-bridge, orchestrator, rsync-master, rsync-slave\* |
| `02-service-maintenance.yml` | maintenance | docker-cleanup (cron 03:00, global) |
| `02-init-ptaas.yml` | ptaas-init | init job (DB schema, DefectDojo bootstrap) |
| `40-service-borodino.yml` | borodino | zaproxy, zap-scanner, wg-gateway, ak47×5, bm12×15, msf-teamserver, uzi×3, karacho-blockchain, masscan\*, nuclei, nuclei-api, nuclei-worker, logpull, redis, pentest-orchestrator, pentest-exporter, c2-monitor |
| `70-service-defectdojo.yml` | **dojo** | DefectDojo (nginx, uWSGI, Celery Beat/Worker, initializer), dojo-triage |
| `41-service-nym.yml` | nym | nym-proxy (SOCKS5 mixnet) |
| `45-service-ml-threat-intel.yml` | ml-threat | ml-threat-intel-api |
| `46-service-razvedka.yml` | razvedka | razvedka (CTI Telegram/Twitter) |
| `47-service-vigie.yml` | vigie | vigie (ANSSI RSS watchlist) |
| `48-service-dozor.yml` | dozor | dozor (règles Suricata dynamiques) |
| `49-service-mcp.yml` | mcp | mcp-server (MCP HTTP/SSE, port 8001) |
| `50-service-trivy.yml` | trivy | trivy-scanner |
| `51-service-ollama.yml` | ollama | ollama (GPU), dcgm-exporter |
| `55-service-sentinel.yml` | sentinel | mosquitto (MQTT), sentinel-collector |
| `56-service-dvar.yml` | dvar | dvar (cible IoT vulnérable) |
| `60-service-telegram.yml` | telegram | telegram-bot |
| `65-service-medved.yml` | medved | medved-honeypot (SSH/HTTP/RDP/SMB/FTP/Telnet) |

\* = mode global (un replica par nœud)

---

## Réseaux overlay

| Réseau | Sous-réseau | Usage |
|--------|-------------|-------|
| `monitoring` | — | Prometheus → Grafana/Loki/Tempo |
| `backend` | — | PostgreSQL, communications inter-services |
| `proxy` | — | Traefik (ingress) |
| `pentest` | — | DefectDojo, Redis, MSF, ZAP |
| `borodino_scan_net` | 10.11.0.0/24 | Scans sortants via wg-gateway (ProtonVPN) |
| `rsync_network` | — | Sauvegardes rsync master ↔ slaves |
| `mail` | — | Alertmanager ↔ Postfix ↔ ProtonMail bridge |
| `iot` | — | Mosquitto MQTT (sentinel) |
| `boot_socket_proxy` | — | Proxy Docker socket (externe) |

**Routage scan** : `route-setup.sh` — RFC1918 via overlay GW, internet via `wg-gateway` (exit IP ~149.102.244.100 FR)

---

## Flux de données — Pentest Pipeline

```
IP2Location CIDRs
      │
      ▼
 ak47×5 replicas ──── nmap scan ──────────────────────────────────────────┐
                                                                           │
 bm12×15 replicas ─── nmap services + OSINT (VT/OTX/AbuseIPDB/Shodan) ───┤
                       │ (optionnel: via Nym SOCKS5 proxy)                │
                       ▼                                                   │
             PostgreSQL (6.15M hosts, 33.7M services)                     │
                       │                                                   │
                       ├──── masscan (global) ─────────────────────────────┘
                       │
                       ├──── zaproxy + zap-scanner (web apps)
                       │
                       ├──── nuclei + nuclei-api (templates CVE)
                       │
                       └──── uzi×3 (MSF brute-force SSH/FTP/SMB/DB/HTTP + Meterpreter C2)
                                    │
                                    ▼
                             msf-teamserver (RPC :55553)
                                    │
                                    ├── c2-monitor → Telegram + DefectDojo findings
                                    │
                                    └── DefectDojo (vuln management)
                                             │
                                        dojo-triage (IA — Ollama mistral:7b)
                                             │
                                        Prometheus metrics ──── Grafana dashboards
```

---

## DefectDojo — Vulnerability Management

**Stack** : `dojo` (`70-service-defectdojo.yml`)

```
DefectDojo nginx (ingress :8080)
       │
       ▼
DefectDojo uWSGI (application Python)
       │
       ├── Celery Worker  — traitement asynchrone des imports
       ├── Celery Beat    — tâches planifiées
       └── dojo-triage    — agent IA (Ollama mistral:7b-instruct)
                            re-triage automatique des findings
```

**Sources de findings importées** :
| Source | Type | Intégration |
|--------|------|-------------|
| OWASP ZAP | DAST | zap-scanner → API v2 |
| Nuclei | CVE templates | nuclei-api → API v2 |
| Metasploit/uzi | Exploitation | c2-monitor → API v2 |
| ml-threat-intel | IoC enrichissement | API v2 |
| Trivy | Container CVEs | trivy-scanner → API v2 |

**API** : `http://defectdojo.bojemoi.lab.local/api/v2/`
**Auth** : Docker secret `dojo_api_token`

---

## Threat Intelligence Pipeline

```
Telegram/Twitter channels ──── razvedka ──── Alertmanager (DDoS FR détecté)
ANSSI RSS feeds ───────────── vigie ─────── Alertmanager (bulletins sécurité)
Logs Fly.io/Lightsail ─────── logpull ───── PostgreSQL

IoC (IP/URL/hash) ─────────── ml-threat-intel-api ─── ML classifier
                                    │                  + OSINT enrichment
                                    └─────────────────── DefectDojo / alertes

ESP32 probes ──── MQTT (Mosquitto) ─── sentinel-collector ─── PostgreSQL + Prometheus
```

---

## Infrastructure C2 Red Team

```
Implants
   │
   ▼
Redirecteurs Fly.io (nginx + OpenVPN client)
   │  - Filtre UA : scanners → 302 google.com
   │  - Paths C2 : /api /update /assets /cdn /upload /download /v*
   │
   │ VPN OpenVPN (UDP 1194)
   ▼
bojemoi.me (Lightsail) — openvpn-c2 container
   │
   │ Route 192.168.1.0/24 via VPN
   ▼
192.168.1.121:4444 (meta-76 Traefik TCP)
   │
   ▼
msf-teamserver (multi/handler :4444)
   │
   ├── c2-monitor (sessions Meterpreter → Telegram + DefectDojo)
   └── uzi×3 (post-exploitation automatisé)
```

**PKI** : `/opt/bojemoi/volumes/c2-vpn/{pki,server,clients,ccd}`
**Scripts** : `scripts/c2-vpn-init-pki.sh`, `scripts/provision-redirector.sh`

---

## Monitoring Stack

```
Services (all nodes)
  node-exporter (9100) ─────────────────────────────┐
  cadvisor (8080) ──────────────────────────────────┤
  postgres-exporter (9187) ─────────────────────────┤
  redis-exporter (9634) ────────────────────────────┤
  pentest-exporter ─────────────────────────────────┤
  c2-monitor (9305) ─────────────────────────────────┤
  suricata-exporter (9917, meta-70) ────────────────┤
  dcgm-exporter (meta-68, GPU) ─────────────────────┤
                                                     │
                                              Prometheus (9090, 15d, 10GB)
                                                     │
                            ┌────────────────────────┼───────────────────────┐
                            │                        │                       │
                         Grafana                   Loki                   Tempo
                        (dashboards)             (logs)              (traces OTLP)
                            │
                       Alertmanager
                       │           │
                  Telegram      ProtonMail
                  (alertes)     (rapports)
```

**Collecteur** : Alloy (agent Grafana) — scrape logs → Loki, métriques → Prometheus

---

## Services sur bojemoi.me (Lightsail)

**Hôte** : Amazon Linux 2023, 2 vCPU, 916 MB RAM, eu-central-1

| Service | Port | Technologie |
|---------|------|-------------|
| Nginx | 80/443 | Reverse proxy + TLS (Let's Encrypt) |
| Gitea | :3000 (interne) | Git + CI/CD (Gitea Actions) |
| gitea-db | — | PostgreSQL 15 |
| gitea-runner | — | act_runner (Docker jobs) |
| openvpn-c2 | UDP 1194 | Serveur VPN C2 |
| Apache | :8080 | cloud-init / configs / MSF files |

**Vhosts nginx** :
- `gitea.bojemoi.me` → proxy :3000
- `blog.bojemoi.me` → `/var/www/blog.bojemoi.me/` (Hugo/PaperMod, build via CI)
- `bojemoi.me` → proxy Apache :8080

---

## Orchestrateur de déploiement (FastAPI)

**Source** : `provisioning/orchestrator/`
**Endpoint** : port 8000 (exposé 28080 via Swarm)

```
Requête HTTP
     │
     ▼
FastAPI (main.py)
     │
     ├── POST /deploy/vm/{name}       → gitea_client → cloud-init → XenServer API
     ├── POST /deploy/container/{n}   → container_deployer
     ├── POST /deploy/service/{n}     → swarm_deployer
     ├── POST /deploy/all             → pipeline complet
     ├── GET  /deployments            → SQLAlchemy (PostgreSQL)
     ├── GET  /status / /health       → healthcheck
     └── GET  /metrics                → Prometheus client

Base de données : PostgreSQL (SQLAlchemy 2.0, Alembic migrations)
Background jobs : APScheduler
Config source   : Gitea (GitOps — vms/*.yaml, cloud-init/*.yaml)
```

---

## MCP Server (Intégration Claude)

**Source** : `mcp-server/` | **Port** : 8001 (HTTP/SSE)
**Stack** : `49-service-mcp.yml` | **Service** : `mcp_mcp-server` (manager)

| Outil MCP | Description |
|-----------|-------------|
| `query_hosts` | Filtrer hôtes MSF (OS, status, range, purpose) |
| `query_services` | Services d'un hôte |
| `get_host_details` | Détails + scan_details JSON bm12 |
| `get_scan_stats` | Stats globales DB |
| `run_nmap` | Scan nmap (basic/full/stealth/udp/quick) |
| `lookup_ip` | OSINT enrichment (ip-api, OTX, ThreatCrowd, +AbuseIPDB/VT/Shodan) |
| `list_products` / `get_findings` / `add_finding` | API DefectDojo v2 |

---

## Structure des répertoires

```
/opt/bojemoi/
├── stack/                  # Stacks Docker Swarm (YAML)
├── provisioning/           # Orchestrateur FastAPI (legacy)
├── borodino/               # Outils pentest (ak47, bm12, uzi, nuclei, logpull, redirector)
├── oblast/ oblast-1/       # OWASP ZAP scanning
├── samsonov/               # pentest-orchestrator, nuclei-api, MITRE ATT&CK
├── mcp-server/             # Serveur MCP (database, DefectDojo, nmap, osint tools)
├── c2-monitor/             # Monitoring sessions C2 (Metasploit/Meterpreter)
├── ptaas-init/             # Init job PTaaS (DB schema, DefectDojo bootstrap)
├── razvedka/               # CTI Telegram/Twitter
├── vigie/                  # ANSSI RSS monitor
├── dozor/                  # Gestionnaire règles Suricata
├── sentinel/               # Collecteur MQTT IoT
├── medved/                 # Honeypot multi-protocoles
├── karacho/                # API blockchain analytics
├── nym-proxy/              # Proxy Nym mixnet
├── redirector/             # Configs nginx redirecteur C2
├── discord/                # Scripts setup serveur Discord PTaaS
├── scripts/                # CI/CD, build, PKI, provisioning
├── cloud-init/             # Templates cloud-init pour VMs XenServer
├── configs/                # Templates de configuration
├── SecLists/               # Wordlists (git submodule)
├── volumes/                # Données persistantes (gitignored)
│   ├── grafana/            # Dashboards + provisioning
│   ├── prometheus/         # Règles + scrape configs
│   ├── alertmanager/       # Config alertes + TLS
│   ├── loki/ tempo/        # Config logs/traces
│   ├── suricata/           # Règles IDS (41 MB+)
│   ├── c2-vpn/             # PKI OpenVPN C2
│   └── postgres/           # PostgreSQL config + entrypoint SSL
└── CLAUDE.md               # Instructions Claude Code
```

---

## Stack technique

| Catégorie | Technologies |
|-----------|--------------|
| Orchestration | Docker Swarm 29.1.5 |
| API | FastAPI, Uvicorn, Starlette |
| Base de données | PostgreSQL 15, SQLAlchemy 2.0, Alembic |
| Monitoring | Prometheus, Grafana, Loki, Tempo, Alloy, cAdvisor |
| Alerting | Alertmanager → Telegram + ProtonMail |
| Reverse proxy | Traefik + Let's Encrypt |
| Sécurité périmètre | Suricata IDS (host mode, tous les workers) |
| Vuln management | DefectDojo + dojo-triage (Ollama mistral:7b) |
| Scanning | Nmap, Masscan, OWASP ZAP, Nuclei, Trivy |
| Exploitation | Metasploit Framework (RPC), Meterpreter |
| OSINT | VirusTotal, AbuseIPDB, OTX, ip-api, Shodan |
| Anonymisation | Nym Mixnet SOCKS5, ProtonVPN OpenVPN |
| C2 | Fly.io redirecteurs (nginx + OpenVPN) |
| LLM | Ollama (mistral:7b, GPU NVIDIA T400) |
| IoT | MQTT Mosquitto, ESP32, détection smartphones |
| File queue | Redis, APScheduler |
| Langages | Python 3.11, Bash, Ruby, Go |
| CI/CD | GitLab CI + Gitea Actions |
