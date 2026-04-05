# Bojemoi Lab

Infrastructure-as-Code for a Docker Swarm-based offensive security lab.
Automated network reconnaissance, vulnerability scanning, exploitation, and threat intelligence — all self-hosted.

## Architecture

```
                   ┌─────────────────────────────────────────┐
                   │  Docker Swarm (4 nodes)                  │
                   │                                          │
                   │  Manager (meta-76)                       │
                   │  ├─ Traefik (reverse proxy + TLS)        │
                   │  ├─ Prometheus / Grafana / Loki          │
                   │  ├─ PostgreSQL (msf, grafana, ip2loc)    │
                   │  ├─ Alertmanager + Proton Mail Bridge    │
                   │  └─ Orchestrator API (FastAPI)           │
                   │                                          │
                   │  Workers (meta-68/69/70)                 │
                   │  ├─ ak47   → CIDR sweep (nmap -sS -A)   │
                   │  ├─ bm12   → service fingerprint + OSINT │
                   │  ├─ nuclei → template vulnerability scan │
                   │  ├─ uzi    → Metasploit exploitation     │
                   │  ├─ ZAP    → web app scanning            │
                   │  ├─ Faraday → vuln management            │
                   │  └─ wg-gateway → ProtonVPN exit          │
                   └─────────────────────────────────────────┘
                              ↕ VPN tunnel
                   ┌─────────────────────────────────────────┐
                   │  Fly.io redirectors (C2)                 │
                   │  nginx (UA filter + GeoIP) → MSF handler │
                   └─────────────────────────────────────────┘
```

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Docker Engine | 29.x+ | |
| Docker Swarm | active | `docker swarm init` |
| Local registry | running | `docker run -d -p 5000:5000 registry:2` |
| All images built | — | push to `localhost:5000/` before deploy |

**Node labels** (set before deploying worker stacks):
```bash
docker node update --label-add rsync.slave=true --label-add pentest=true --label-add faraday=true meta-68
docker node update --label-add rsync.slave=true --label-add pentest=true --label-add faraday=true meta-69
docker node update --label-add rsync.slave=true --label-add pentest=true --label-add storage=true  meta-70
```

## Quick Start

```bash
git clone <repo> bojemoi && cd bojemoi

# 1. Configure
./install.sh            # interactive wizard → generates .env

# 2. Create Docker secrets
./scripts/create-secrets.sh

# 3. Deploy (or let install.sh do it)
./install.sh --deploy-only
```

### Manual step-by-step

```bash
# Copy and edit configuration
cp .env.example .env
chmod 600 .env
$EDITOR .env             # fill in POSTGRES_PASSWORD, FARADAY_PASSWORD, etc.

# Load env
set -a && source .env && set +a

# Create secrets
./scripts/create-secrets.sh

# Deploy base stack (monitoring + DB + Traefik)
docker stack deploy -c stack/01-service-hl.yml base --prune --resolve-image always

# Deploy scanning stack
docker stack deploy -c stack/40-service-borodino.yml borodino --prune --resolve-image always

# Deploy other stacks as needed
docker stack deploy -c stack/49-service-mcp.yml        mcp      --prune --resolve-image always
docker stack deploy -c stack/51-service-ollama.yml     ollama   --prune --resolve-image always
docker stack deploy -c stack/60-service-telegram.yml   telegram --prune --resolve-image always
```

## Stack Reference

| File | Stack name | Description |
|---|---|---|
| `01-service-hl.yml` | `base` | Core: Postgres, Grafana, Prometheus, Loki, Alertmanager, Traefik |
| `40-service-borodino.yml` | `borodino` | Scanning: ak47, bm12, nuclei, uzi, ZAP, Faraday, MSF teamserver |
| `45-service-ml-threat-intel.yml` | `ml-threat` | ML threat intelligence pipeline |
| `46-service-razvedka.yml` | `razvedka` | Telegram channel monitoring (OSINT) |
| `47-service-vigie.yml` | `vigie` | RSS/CVE feed watcher |
| `48-service-dozor.yml` | `dozor` | IoT/Suricata event processor |
| `49-service-mcp.yml` | `mcp` | Claude Code MCP server (query lab data) |
| `50-service-trivy.yml` | `trivy` | Container image scanning |
| `51-service-ollama.yml` | `ollama` | Local LLM inference (Mistral) |
| `55-service-sentinel.yml` | `sentinel` | MQTT-based IoT sensor collector |
| `56-service-dvar.yml` | `dvar` | IoT network monitoring |
| `60-service-telegram.yml` | `telegram` | PTaaS Telegram bot |
| `65-service-medved.yml` | `medved` | Bear — additional recon service |

## Configuration

All configuration lives in `.env` (generated from `.env.example`).

**Required variables** (must be set, no defaults):
- `POSTGRES_PASSWORD` — PostgreSQL master password
- `GRAFANA_ADMIN_PASSWORD` — Grafana admin password
- `PGADMIN_PASSWORD` — PgAdmin password
- `FARADAY_PASSWORD` — Faraday vuln management password
- `MSF_RPC_PASSWORD` — Metasploit RPC password
- `KARACHO_SECRET_KEY` — Karacho blockchain service key

**Key variables with defaults**:
- `LAB_DOMAIN` — Internal domain (default: `bojemoi.lab`)
- `PUBLIC_DOMAIN` — External domain (default: `bojemoi.me`)
- `IMAGE_REGISTRY` — Docker registry (default: `localhost:5000`)
- `BOJEMOI_BASE_PATH` — Project root (default: `/opt/bojemoi`)

See `.env.example` for the full list with documentation.

## Docker Secrets

Secrets are stored in Docker Swarm's encrypted store (not in `.env`).
Run `./scripts/create-secrets.sh` to create them interactively.

```bash
./scripts/create-secrets.sh --list    # check which secrets exist
./scripts/create-secrets.sh           # create missing secrets
```

Key secrets:
| Secret | Used by |
|---|---|
| `telegram_bot_token` | alertmanager, telegram-bot, uzi |
| `proton_username` / `proton_password` | protonmail-bridge |
| `alertmanager_smtp_pass` | alertmanager |
| `protonvpn_ovpn` / `protonvpn_auth` | wg-gateway (scan VPN) |
| `fly_api_token` | logpull (C2 redirector logs) |
| `anthropic_api_key` | nuclei AI template gen, uzi |
| `ssh_private_key` | rsync-master/slave |

## Operations

```bash
# Service status
docker service ls
docker stack ls

# Logs
docker service logs -f borodino_ak47-service
docker service logs -f base_grafana

# Update a stack after config change
set -a && source .env && set +a
docker stack deploy -c stack/40-service-borodino.yml borodino --prune --resolve-image always

# Force rolling update (when image tag didn't change)
docker service update --force --image localhost:5000/borodino:latest borodino_ak47-service

# Scale a service
docker service scale borodino_bm12-service=10

# SSH to a worker node
NODE_IP=$(docker node inspect meta-68 --format '{{.Status.Addr}}')
ssh -p 4422 -i ~/.ssh/meta76_ed25519 docker@$NODE_IP
```

## DNS Setup

Add to `/etc/hosts` on any machine that needs access to the lab UI:

```
<MANAGER_IP>  grafana.bojemoi.lab prometheus.bojemoi.lab faraday.bojemoi.lab
<MANAGER_IP>  pgadmin.bojemoi.lab alertmanager.bojemoi.lab karacho.bojemoi.lab
<MANAGER_IP>  nuclei.bojemoi.lab redis.bojemoi.lab cadvisor.bojemoi.lab
```

Or configure a local DNS resolver (dnsmasq/Pi-hole) to point `*.bojemoi.lab` at the manager IP.

## Directory Structure

```
bojemoi/
├── install.sh                  # Bootstrap installer
├── .env.example                # Configuration template
├── .env                        # Your config (gitignored)
├── stack/                      # Docker Swarm stack files
├── borodino/                   # Scan worker sources + Dockerfiles
├── samsonov/                   # Pentest orchestrator + nuclei API
├── mcp-server/                 # Claude Code MCP server
├── scripts/
│   ├── create-secrets.sh       # Docker secrets setup
│   ├── c2-vpn-init-pki.sh      # C2 VPN PKI initialization
│   └── provision-redirector.sh # Fly.io redirector provisioning
├── provisioning1/              # Orchestrator API (FastAPI + PostgreSQL)
├── volumes/                    # Runtime data (gitignored)
│   ├── grafana/                # Dashboards + provisioning
│   ├── prometheus/             # Rules + config
│   ├── alertmanager/           # Config + certs
│   └── loki/                   # Loki config
└── cloud-init/                 # VM and redirector templates
```
