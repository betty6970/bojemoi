---
title: "Bojemoi Lab : l'architecture complète d'un homelab offensif/défensif sur Docker Swarm"
date: 2026-03-12T20:00:00+00:00
lastmod: 2026-10-30T22:00:00+00:00
draft: false
tags: ["homelab", "docker", "docker-swarm", "devops", "gitops", "selfhosted", "opensource", "cybersecurity", "infosec", "threat-intelligence", "osint", "machine-learning", "blue-team", "soc", "build-in-public", "french-tech"]
summary: "Tour d'horizon complet de Bojemoi Lab : 2 nœuds Docker Swarm, 50+ services, un pipeline de scan réseau massif, un orchestrateur d'attaque LLM autonome et un stack d'observabilité full."
description: "Architecture détaillée de Bojemoi Lab — cluster Docker Swarm 2 nœuds, pipeline de reconnaissance (nmap → fingerprinting NSE → MyAI orchestrateur LLM), threat intelligence ML, C2 Sliver/MSF, IDS Suricata, honeypot multi-protocole, observabilité Prometheus/Grafana/Loki."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

J'ai construit Bojemoi Lab brique par brique depuis plusieurs mois. Il est temps de documenter ce que ça donne vraiment — pas juste un composant, mais l'ensemble du système.

Voici l'architecture complète — mise à jour octobre 2026.

---

## Vue d'ensemble

Bojemoi Lab est un cluster **Docker Swarm de 2 nœuds** qui fait tourner en permanence :

- Un **pipeline de reconnaissance réseau** (scan CIDR → fingerprinting → exploitation autonome par LLM)
- Un **orchestrateur d'attaque LLM** (MyAI) qui planifie et exécute des campagnes complètes OSINT → RECON → VULN_SCAN → EXPLOIT → REPORT
- Une **infrastructure C2** (Sliver + Metasploit, relay Fly.io)
- Une **plateforme de threat intelligence** multi-sources (CTI, ML, OSINT, CERT)
- Un **stack défensif** (IDS, WAF, honeypot, règles dynamiques)
- Une **observabilité complète** (métriques GPU/CPU/réseau, logs, GPU monitoring DCGM)
- Des **interfaces de contrôle** (Telegram, MCP Claude, API REST)

Le tout sur des machines physiques à la maison, avec une infrastructure as code complète versionnée sur Gitea.

---

## Infrastructure physique

```
meta-76 (MANAGER)    Intel i9-10900X, 8 cores, 8 GB RAM, Alpine Linux
meta-68 (WORKER)     31.3 GB RAM, RTX 3060 12 GB + T400 4 GB (GPU passthrough XenServer)
```

**Règle de placement :**
- `meta-76` (manager) : PostgreSQL, Prometheus, Grafana, Loki, Traefik, Alertmanager, registry
- `meta-68` (worker) : tout le reste — scanning, LLM, GPU, DefectDojo, C2

**Registry local** : `localhost:5000`. Toutes les images sont buildées et poussées localement avant déploiement.

**Lightsail** (bojemoi.me) : Amazon Linux 2023, eu-central-1. Nginx reverse proxy pour Gitea et le blog Hugo.

---

## GPU — Stack IA locale

meta-68 fait tourner deux instances Ollama en parallèle, une par GPU :

| Service | GPU | Modèles | Usage |
|---------|-----|---------|-------|
| `ollama_ollama` | RTX 3060 (12 GB) | phi4:14B, qwen2.5:3b | MyAI orchestrateur principal |
| `ollama_ollama-judge` | T400 (4 GB) | qwen2.5:3b | LLM judge — valide les outputs MyAI |

`NVIDIA_VISIBLE_DEVICES` isole chaque container sur son GPU. `KEEP_ALIVE=10m` décharge les modèles après inactivité.

Monitoring GPU : DCGM exporter (métriques `DCGM_FI_DEV_FB_USED`) → Prometheus → Grafana dashboard "Ollama LLM".

---

## Les stacks Docker

### Base — Services partagés (manager)

Le cœur du lab. Tout ce qui est partagé entre les services.

**PostgreSQL** — une seule instance, plusieurs bases :

| Base | Contenu |
|------|---------|
| `msf` | 6,15M hôtes, 6,8M services scannés, ~2,5 GB |
| `myai` | Attacks, findings, embeddings pgvector (384 dims), llm_validations |
| `bojemoi_threat_intel` | IoC classifiés, scores ML, cache OSINT |
| `ip2location` | CIDRs géolocalisés |
| `razvedka` | Mentions hacktivistes |
| `vigie` | Bulletins CERT-FR |

Tuning PG : `shared_buffers=1GB`, `work_mem=32MB`, `max_connections=200`.

**Observabilité :**
- Prometheus — scraping métriques (node, postgres, cadvisor, dcgm-exporter, honeypot, mcp, pentest-exporter)
- Grafana 12 — dashboards provisionnés automatiquement (infra, pentest, LLM, GPU)
- Loki — agrégation logs (tous les services via Alloy)
- Alloy — collecteur unifié pipeline Loki

**Mail :**
- Postfix (SMTP) + Proton Mail Bridge — alertes critiques chiffrées

---

### Boot — Proxy et protection (manager)

- **Traefik** — reverse proxy, TLS automatique, routing vers Lightsail
- **CrowdSec** — WAF collaboratif

---

### Borodino — Pipeline de reconnaissance (workers)

#### ak47 — Scan CIDR massif (15 replicas)

Script ash qui tire un CIDR aléatoire depuis `ip2location` et lance `db_nmap -sS -A -O` via Metasploit. Résultats stockés dans `msf.hosts` / `msf.services`.

#### bm12 — Fingerprinting profond (15 replicas)

Script Python qui sélectionne un hôte non fingerprinté, lance des scripts NSE ciblés selon les services détectés (25 catégories), classifie et enrichit avec des scores OSINT.

#### DefectDojo — Workspace findings

Port 8080 sur meta-68 (`defectdojo-nginx`). Reçoit tous les findings du pipeline. API v2 utilisée par MyAI pour pousser les résultats d'exploitation.

#### dojo-triage — Triage LLM automatique

Service Python qui lit les nouveaux findings DefectDojo et les fait analyser par `qwen2.5:3b` sur `ollama-judge` (T400). Classifie chaque finding en `accepted` / `needs-review` / `false-positive`.

#### dojo-broker — Queue Valkey

Instance Valkey dédiée aux queues pentest et à la communication DefectDojo. Remplace l'ancien Redis générique.

---

### MyAI — Orchestrateur d'attaque LLM autonome

C'est la pièce centrale ajoutée en 2026. Un service FastAPI (`myai_api`, 2 replicas) qui orchestre des campagnes d'attaque complètes de bout en bout.

**Endpoint principal :**
```
POST /attack {"target": "ip", "objective": "full|recon|exploit"}
```

**Flow d'exécution :**

```
OSINT (lookup_ip + plan_attack via phi4)
    ↓
RECON (MSF DB + Nuclei port scan + socket scan)
    ↓
VULN_SCAN (LLM choisit les plugins selon les services détectés)
    ↓
EXPLOIT? (si CVSS suffisant)
    ↓
POST_EXPLOIT? (Sliver beacon)
    ↓
REPORT → DefectDojo
```

**LLM Judge :** chaque décision de phase (plan_attack, decide_vuln_scan) est validée par `qwen2.5:3b` sur `ollama-judge` avant exécution. Fail-open (max 2 retries).

**RAG :** pgvector (`finding_embeddings`) enrichit le prompt avec les findings similaires passés — améliore la pertinence des décisions d'exploitation.

**Plugin system — hot-reload :**

Les plugins sont montés depuis `/opt/bojemoi/volumes/myai-plugins/` (bind-mount meta-68). Auto-sync meta-76→meta-68 via rsync (cron `*/5 * * * *` + git post-commit hook).

| Plugin | Type | Description |
|--------|------|-------------|
| `nuclei` | network | Scan Nuclei via API HTTP |
| `zap` | web | OWASP ZAP spider + active scan |
| `kali` | sandbox | Container Kali (sqlmap, nikto, medusa, hydra) |
| `snmp` | network | Probe SNMP v2c OID sysDescr |
| `impacket` | network | SMB/Kerberos via Impacket |
| `sliver` | post-exploit | Génération + déploiement implants Sliver |
| `php_uaf` | exploit | CVE-2026-109618 PHP 8.3.x OOM longjmp UAF |
| `uzi` | exploit | Metasploit RPC exploitation |

**ThreadPoolExecutor :** `max_workers=16` (I/O-bound — Ollama HTTP, psycopg2, subprocess). Valeur initiale de 4 causait une famine : les LLM calls (30-60s) saturaient le pool, bloquant même les updates DB (<1ms).

**Campaign dispatcher :**

Service Python (`pentest_campaign-dispatcher`) qui tire des hosts de la MSF DB toutes les 2 minutes et dispatch des attacks sur MyAI, avec tracking de 6 slots concurrents.

---

### C2 — Infrastructure de commande

#### MSF Teamserver

`borodino-msf_msf-teamserver` — Metasploit Framework avec RPC SSL (port 55553) et handler C2 (port 4444). 6 GB RAM.

#### Sliver

C2 framework gRPC. Configurations et implants dans des volumes Docker dédiés. Intégré au plugin `sliver` de MyAI pour le post-exploitation automatisé.

#### Tunnel C2

Chain complète : implant → LHOST=37.16.12.4:443 (Fly.io redirector) → VPN → Traefik:4444 → msf-teamserver.

`lab-tunnel` container sur meta-76 (network_mode:host) maintient le VPN OpenVPN vers bojemoi.me.

---

### Pentest — Services annexes

- **nuclei-api** — API FastAPI wrappant Nuclei. Détecte automatiquement le gateway ProtonVPN pour router les scans anonymisés.
- **zaproxy** — OWASP ZAP 2.x, utilisé par le plugin `zap`
- **wg-gateway** — ProtonVPN WireGuard client (standalone docker-compose, pas Swarm). IP sortante anonymisée pour les scans.

---

### Threat Intelligence (workers)

#### razvedka — Prédiction DDoS

Surveille des canaux Telegram hacktivistes via Telethon. Alerte si buzz DDoS ciblant la France (3 canaux actifs + 5 mentions).

#### vigie — Veille CERT-FR

Scrute les flux RSS ANSSI et croise avec une watchlist de composants du lab. Alerte si un CVE concerne un composant utilisé.

#### alert-agent — Alertes intelligentes

Service Python qui reçoit les alertes Prometheus et les fait analyser par Claude Haiku (`LLM_BACKEND=claude`). Évalue la sévérité dynamiquement et envoie vers `@bojemoi_ptaas` avec emoji contextuel.

#### ml-threat-intel — Scoring ML

API FastAPI classifiant les IoC (malware, C2, phishing, scanner) avec un modèle ML + enrichissement OSINT multi-sources.

---

### Défense réseau (hors Swarm, host mode)

**Suricata** tourne en `docker-compose` classique avec `network_mode: host` sur les 2 nœuds. Rules dynamiques générées par dozor (feeds IoC). `eve.json` actif, eve-cleaner à 5 GB.

---

### Honeypot — medved

Multi-protocole : SSH/22, HTTP/8000, RDP/3389, SMB/445, FTP/2121, Telnet/2323. Métriques port 9200.

---

### MCP Server — Intégration Claude Code

Serveur Model Context Protocol (port 8001) qui expose les données du lab dans Claude Code via HTTP/SSE.

Outils : `query_hosts`, `query_services`, `get_host_details`, `lookup_ip`, `list_workspaces`, `get_vulns`, `add_vuln`, `run_nmap`.

---

## Flux de données — pipeline complet

```
ip2location DB (CIDRs)
        │
        ▼
    ak47 (×15)        ── db_nmap ──────────────────────→ msf.hosts / msf.services
        │
        ▼
    bm12 (×15)        ── NSE + OSINT ──────────────────→ hosts.scan_details (JSON)
        │
        ▼
campaign-dispatcher   ── POST /attack ─────────────────→ MyAI
        │
        ▼
    MyAI              ── OSINT → RECON → VULN_SCAN ───→ findings
    (phi4 + plugins)     └── EXPLOIT → POST_EXPLOIT ──→ sessions Sliver/MSF
        │
        ▼
    DefectDojo        ── workspace pentest findings
        │
        ▼
    dojo-triage       ── qwen2.5:3b ───────────────────→ triage auto (accepted/false-positive)
```

En parallèle :

```
Canaux Telegram hacktivistes → razvedka → alert-agent → @bojemoi_ptaas
Flux RSS ANSSI              → vigie    → alert-agent → @bojemoi_ptaas
Alertes Prometheus          → alert-agent (Claude Haiku) → @bojemoi_ptaas
Feeds IoC                   → dozor    → règles Suricata dynamiques
Trafic réseau               → Suricata → EVE enricher → threat_intel DB
Attaquants                  → medved   → PostgreSQL + DefectDojo
```

---

## Observabilité

```
Services → métriques → Prometheus
GPU      → DCGM exporter → Prometheus
                               │
                               └→ Grafana (dashboards : infra, pentest, LLM judge, GPU)
                               └→ Alertmanager → alert-agent → Telegram

Services → logs (stdout) → Alloy collector → Loki → Grafana explore
```

---

## État en octobre 2026

| Métrique | Valeur |
|----------|--------|
| Nœuds Swarm | 2 (1 manager + 1 worker) |
| Stacks Docker | 14 |
| Services actifs | ~50 |
| Hôtes scannés en DB | 6,15M |
| Services réseau en DB | 6,8M |
| Taille PostgreSQL | ~5 GB |
| Images Docker custom | 35+ |
| GPU | RTX 3060 12 GB + T400 4 GB |
| Modèles LLM actifs | phi4:14B, qwen2.5:3b ×2 |
| Findings DefectDojo | 35 000+ |
| Plugins MyAI | 8 (hot-reload) |

---

## Et maintenant ?

MyAI tourne en continu — campaign-dispatcher dispatch des cibles toutes les 2 minutes, phi4 planifie les attaques, les plugins exécutent et les findings remontent automatiquement dans DefectDojo.

La prochaine étape : améliorer le taux de findings Critical (actuellement dominé par Info/Medium) en affinant la sélection des cibles (hosts avec CVE connus) et les seuils d'exploitation.

Build in public. Tout est versionné sur Gitea.

→ **blog.bojemoi.me** pour les articles détaillés sur chaque composant.
