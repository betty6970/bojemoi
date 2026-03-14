# Architecture Globale — Bojemoi Lab

```
┌──────────────────────────────────────────────────────────────────────┐
│                        INTERNET / EXTERNAL                           │
│  ANSSI/CERT-FR • Telegram Channels • VirusTotal • AbuseIPDB • OTX   │
│  Shodan • X/Twitter • MITRE ATT&CK feeds • XenServer (on-prem)      │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────┐
│                   LIGHTSAIL (bojemoi.me)                              │
│  Nginx (80/443) • Gitea (gitea.bojemoi.me) • Hugo blog               │
│  Apache (8080) • cloud-init/configs • Gitea Actions CI               │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ SSH/GitOps
┌────────────────────────────▼─────────────────────────────────────────┐
│                   DOCKER SWARM CLUSTER                                │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │  meta-76 (MANAGER) — Intel i9, 16 GB RAM                   │     │
│  │                                                              │     │
│  │  ┌─── BASE STACK ──────────────────────────────────────┐   │     │
│  │  │  PostgreSQL (msf, threat_intel, razvedka, vigie,    │   │     │
│  │  │             telegram_bot, deployments, ip2location) │   │     │
│  │  │  Prometheus • Grafana • Loki • Tempo • Alloy        │   │     │
│  │  │  Alertmanager • PgAdmin • cAdvisor • node-exporter  │   │     │
│  │  │  Postfix • Proton Mail Bridge • Koursk (rsync)      │   │     │
│  │  │  Provisioning API (FastAPI, port 8000→28080)        │   │     │
│  │  └─────────────────────────────────────────────────────┘   │     │
│  │                                                              │     │
│  │  ┌─── BOOT STACK ──┐  ┌─── MCP STACK ───────────────┐    │     │
│  │  │  Traefik (proxy) │  │  mcp-server (port 8001)     │    │     │
│  │  │  CrowdSec (WAF) │  │  Claude Code integration     │    │     │
│  │  └─────────────────┘  └─────────────────────────────┘    │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  WORKERS: meta-68, meta-69, meta-70                            │  │
│  │                                                                  │  │
│  │  ┌─── BORODINO STACK ──────────────────────────────────────┐  │  │
│  │  │  ak47  (x15) → Nmap CIDR scan → msf.hosts/services     │  │  │
│  │  │  bm12  (x15) → Deep fingerprint + NSE → classify hosts  │  │  │
│  │  │  uzi   (x3)  → Metasploit exploits (MODE_RUN=0)        │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │                                                                  │  │
│  │  ┌─── PENTEST STACK ──────────┐  ┌─── TELEGRAM ────────────┐ │  │
│  │  │  Faraday (port 5985)       │  │  telegram-bot            │ │  │
│  │  │  OWASP ZAP                 │  │  Redis pub/sub           │ │  │
│  │  │  Nuclei (25 templates)     │  │  Bot: @Betty_Bombers_bot │ │  │
│  │  │  Samsonov (import)         │  │  Group: Bojemoi PTaaS    │ │  │
│  │  │  Tsushima (aggregator)     │  └─────────────────────────┘ │  │
│  │  └────────────────────────────┘                               │  │
│  │                                                                  │  │
│  │  ┌─── THREAT INTEL ─────────────────────────────────────────┐ │  │
│  │  │  razvedka  → DDoS prediction (Telegram channels HU/RU)   │ │  │
│  │  │  vigie     → CERT-FR bulletin monitor (ANSSI RSS)        │ │  │
│  │  │  dozor     → Suricata rule generator (IoC feeds)         │ │  │
│  │  │  ml-threat → ML scoring + MITRE ATT&CK mapping          │ │  │
│  │  └─────────────────────────────────────────────────────────┘ │  │
│  │                                                                  │  │
│  │  ┌─── DEFENSE ──────────┐  ┌─── HONEYPOT ─────────────────┐ │  │
│  │  │  Suricata (host mode) │  │  medved (host mode)          │ │  │
│  │  │  EVE enricher         │  │  SSH/HTTP/RDP/SMB/FTP/Telnet │ │  │
│  │  │  CrowdSec (WAF)       │  │  → PostgreSQL + Faraday      │ │  │
│  │  └──────────────────────┘  └─────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Flux de Données — Pipeline de Scan

```
ip2location DB
      │
      ▼
  ak47 (x15)          ← scans CIDRs via db_nmap
      │ msf.hosts
      ▼
  bm12 (x15)          ← deep NSE fingerprinting (25 catégories)
      │ hosts.scan_details (JSON) + comments + scan_status='bm12_v2'
      ▼
  uzi (x3)            ← Metasploit exploits (désactivé)
      │
      ▼
  Faraday             ← workspace pentest
      │
      ▼
  Samsonov/Tsushima   ← import + agrégation
      │
      ▼
  Telegram Bot        ← notification + commandes manuelles
```

---

## Stack Files → Services

| Stack | Services clés | Placement |
|-------|--------------|-----------|
| `01-service-hl.yml` | postgres, prometheus, grafana, loki, alertmanager, postfix, provisioning | manager |
| `boot stack` | traefik, crowdsec | manager |
| `40-service-borodino.yml` | ak47, bm12, uzi, faraday, zaproxy, nuclei | workers |
| `45-service-ml-threat-intel.yml` | ml-threat-intel-api | workers |
| `46-service-razvedka.yml` | razvedka | workers |
| `47-service-vigie.yml` | vigie | workers |
| `48-service-dozor.yml` | dozor, eve-cleaner | workers |
| `49-service-mcp.yml` | mcp-server | manager |
| `50-service-trivy.yml` | trivy scanner | CI/CD only |
| `60-service-telegram.yml` | telegram-bot, redis | workers |
| `65-service-medved.yml` | medved honeypot | manager (host ports) |
| `01-suricata-host.yml` | suricata, enricher | host compose (hors swarm) |

---

## Observabilité

```
Services → metrics → Prometheus → Grafana dashboards
Services → logs    → Loki       → Grafana explore
Services → traces  → Tempo      → Grafana explore
Alloy (collector unifié) → pipeline tout-en-un
Alertmanager → Postfix/ProtonBridge → Email chiffré
```

---

## Bases de Données (PostgreSQL)

| Database | Usage | Taille estimée |
|----------|-------|---------------|
| `msf` | Metasploit — hosts (6,15M), services (33,7M), vulns | 9 GB |
| `bojemoi_threat_intel` | ML scoring, OSINT cache, IoC | ~2 GB |
| `ip2location` | CIDRs géolocalisés pour scanning | ~500 MB |
| `razvedka` | Mentions hacktivist, alertes DDoS | ~100 MB |
| `vigie` | Bulletins CERT-FR, watchlist matches | ~50 MB |
| `telegram_bot` | Historique chats, commandes | ~500 MB |
| `honeypot_events` | Captures medved (SSH, HTTP, RDP...) | ~1 GB |
| `deployments` | Audit orchestrateur + blockchain | ~100 MB |

---

## Réseaux Overlay (Swarm)

| Réseau | Services |
|--------|---------|
| `backend` | postgres, redis, tous les services data |
| `monitoring` | prometheus, grafana, loki, tempo, alloy |
| `proxy` | traefik, crowdsec |
| `pentest` | faraday, zaproxy, nuclei, samsonov, mcp-server |
| `rsync_network` | koursk master/slave |
| `mail` | postfix, protonmail-bridge, alertmanager |
| `telegram_net` | telegram-bot |

---

## Résumé

- **4 nœuds Swarm** — 1 manager (meta-76) + 3 workers (meta-68/69/70)
- **12 stacks** — ~43 services distincts
- **9 GB de données** — 6,15M hosts scannés, 33,7M services
- **Pipeline CI/CD** — GitLab + Trivy + Gitea Actions
- **Interfaces de contrôle** — Telegram bot, MCP server (Claude), API REST
- **Threat Intel multi-sources** — OSINT, ML, CTI feeds, honeypot, IDS
