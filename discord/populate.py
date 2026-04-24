#!/usr/bin/env python3
"""Popule les salons Discord du lab Bojemoi via l'API REST."""
import os, sys, time, json
import requests
from pathlib import Path

TOKEN    = Path("/run/secrets/discord_bot_token").read_text().strip()
GUILD_ID = os.environ["GUILD_ID"]
BASE     = "https://discord.com/api/v10"
HDR      = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}

def api(method, path, **kw):
    r = requests.request(method, f"{BASE}{path}", headers=HDR, **kw)
    if r.status_code == 429:
        wait = r.json().get("retry_after", 1)
        print(f"  [rate-limit] {wait}s...")
        time.sleep(wait + 0.2)
        return api(method, path, **kw)
    r.raise_for_status()
    return r.json() if r.content else {}

def post(channel_id, content):
    api("POST", f"/channels/{channel_id}/messages", json={"content": content})
    time.sleep(0.8)

# Récupère les channels existants
channels = api("GET", f"/guilds/{GUILD_ID}/channels")
ch = {c["name"]: c["id"] for c in channels if c["type"] == 0}
print(f"Salons trouvés : {list(ch.keys())}\n")

MESSAGES = {
    "annonces": """\
📣 **Bojemoi Lab — PTaaS**

Infrastructure offensive self-hosted basée sur Docker Swarm (4 nœuds).
Pipeline complet : **reconnaissance → exploitation → reporting → threat intelligence**

🔗 Gitea : https://gitea.bojemoi.me
📊 Grafana : http://grafana.bojemoi.lab.local
🐛 DefectDojo : http://defectdojo.bojemoi.lab.local
📖 Blog : https://blog.bojemoi.me""",

    "règles": """\
📋 **Règles du serveur**

1. Ce serveur est réservé au projet **Bojemoi Lab** — infra, sécurité, threat intel.
2. Les outils et techniques discutés ici sont utilisés dans un cadre **légal et contrôlé**.
3. Ne jamais partager de credentials, tokens ou secrets en clair.
4. Respecter les channels — poster dans le bon salon.
5. Build in public, partager les apprentissages.""",

    "général": """\
👋 **Bienvenue sur le serveur Bojemoi PTaaS**

Ce lab est un projet **build in public** autour de la cybersécurité offensive et défensive :
🔴 Red team automatisé (Metasploit, Nuclei, ZAP, Masscan)
🔵 Blue team (Suricata IDS, Grafana, Loki, Alertmanager)
🧠 Threat intelligence (ML, OSINT, CTI Telegram/Twitter)
🏗️ Infrastructure as Code (Docker Swarm, GitOps, Gitea)""",

    "off-topic": """\
💬 **Off-topic**

Tout ce qui n'a rien à voir avec le lab — détente, veille perso, liens intéressants.""",

    "architecture": """\
🏗️ **Topologie Docker Swarm**

```
meta-76 (Manager) — Intel i9-10900X · 8 cores · 16 GB
├── Services : base stack (postgres, prometheus, grafana, loki, traefik...)
└── Registre local : localhost:5000

Workers (node.role == worker uniquement)
├── meta-68 — pentest · faraday · storage · GPU NVIDIA T400 (ollama)
├── meta-69 — pentest · faraday · rsync.slave
└── meta-70 — pentest · storage · rsync.slave · Suricata IDS
```

**Réseaux overlay** :
`monitoring` · `backend` · `proxy` · `pentest` · `scan_net` (10.11.0.0/24) · `mail` · `rsync_network` · `iot`

**Règle absolue** : tout via Docker secrets + configs — jamais de .env en production.""",

    "docker-swarm": """\
⚙️ **Inventaire des stacks déployées**

```
Stack         Services clés
──────────────────────────────────────────────────────────────────
base          postgres · prometheus · grafana · loki · tempo
              alertmanager · alloy · node-exporter · cadvisor
              postfix · protonmail-bridge · traefik · rsync

borodino      ak47×5 · bm12×15 · uzi×3 · msf-teamserver
              nuclei · nuclei-api · zaproxy · masscan
              redis · pentest-orchestrator · c2-monitor · karacho

dojo          DefectDojo (nginx/uWSGI/Celery) + dojo-triage IA

ml-threat     ml-threat-intel-api (classificateur ML IoC)
razvedka      CTI Telegram RU + Twitter DDoS hacktivist
vigie         ANSSI/CERT-FR RSS watchlist
dozor         Génération dynamique règles Suricata
ollama        LLM local GPU mistral:7b (meta-68, NVIDIA T400)
telegram      Bot Betty_Bombers — commandes pentest
mcp           MCP HTTP/SSE — intégration Claude Code :8001
medved        Honeypot SSH/HTTP/RDP/SMB/FTP/Telnet
```

**Deploy** : `docker stack deploy -c stack/<file>.yml <name> --prune --resolve-image always`""",

    "deployments": """\
🚀 **Workflow de déploiement**

```bash
# 1. Build + push image locale
docker build -t localhost:5000/<image>:latest .
docker push localhost:5000/<image>:latest

# 2. Deploy stack
docker stack deploy -c stack/<file>.yml <stack> --prune --resolve-image always

# 3. Force update (même tag :latest)
DIGEST=$(docker inspect localhost:5000/<img>:latest \\
  --format '{{index .RepoDigests 0}}' | cut -d@ -f2)
docker service update \\
  --image localhost:5000/<img>:latest@$DIGEST \\
  --force <service>
```

**Secrets** : `echo 'val' | docker secret create <name> -`
**Configs** : `docker config create <name> <file>`""",

    "gitops": """\
🔄 **GitOps — Gitea**

Dépôt principal : `gitea.bojemoi.me`

**Pipeline blog** :
```
push → Gitea Actions → Alpine container
     → hugo --minify
     → volume mount /var/www/blog.bojemoi.me/
```

**SSH Git** : `ssh -p 2222 git@bojemoi.me`
**Runner** : `gitea-runner` (act_runner, Docker-in-Docker)

Les stacks YAML sont la source de vérité — pas de modification manuelle en prod.""",

    "ci-cd": """\
⚡ **CI/CD**

**Gitea Actions** (actif) :
- Blog Hugo : build + deploy automatique sur push vers `main`
- Images Docker : build → push `localhost:5000` → redeploy service

**GitLab CI** (legacy, `stack/.gitlab-ci.yml`) :
- Validate : `docker-compose config --quiet`
- Deploy SSH : `docker stack deploy` via clé SSH sur meta-76

**Makefile** (`provisioning1/`) :
```bash
make install   # pip install -r requirements.txt
make start     # docker-compose up --build
make logs      # docker-compose logs -f
make health    # health check API
```""",

    "borodino": """\
🤖 **Pipeline Borodino — Pentest automatisé**

```
IP2Location CIDRs (par pays / ASN)
       │
       ▼
  ak47 ×5     nmap -sS -A sweep par CIDR
       │
       ▼
  bm12 ×15    fingerprinting services + OSINT
              (VT · OTX · AbuseIPDB · Shodan — via Nym Mixnet)
       │
       ▼
  PostgreSQL  6.15M hôtes · 33.7M services · ~9 GB
       │
       ├── nuclei       scan CVE templates (critical/high)
       ├── zaproxy      web app active scan + DAST
       └── uzi ×3       MSF brute-force (SSH/FTP/SMB/HTTP/DB)
                        + Meterpreter reverse HTTPS C2
                               │
                         msf-teamserver :55553 (RPC)
                               │
                         c2-monitor → DefectDojo + Telegram
                               │
                         karacho blockchain (incident ledger)
```

**Stats** : 6.15M hôtes · 33.7M services · PostgreSQL ~9 GB""",

    "ml-threat": """\
🧠 **ML Threat Intelligence**

API REST de classification d'IoC par machine learning.

**Types d'IoC** : IP · URL · Hash de fichier

**Enrichissement OSINT** :
- ip-api.com (géolocalisation ASN)
- AlienVault OTX (threat feeds)
- ThreatCrowd (IP/domain correlation)
- AbuseIPDB (score de réputation)
- VirusTotal (analyse fichiers/URLs)
- Shodan (banner grabbing services)

**Stack** : `ml-threat` → service `ml-threat-intel-api`
**Intégration** : MCP tool `lookup_ip` · DefectDojo findings · Alertmanager""",

    "osint": """\
🔍 **Sources OSINT intégrées**

```
Source          Usage                          Via
──────────────────────────────────────────────────────────
AbuseIPDB       Score de réputation IP         bm12 + ml-threat
VirusTotal      Hash / URL / IP analysis       bm12 + ml-threat
Shodan          Banner grabbing, services      bm12 + ml-threat
AlienVault OTX  Threat feeds IoC               ml-threat
ThreatCrowd     IP/domain correlation          ml-threat
ip-api.com      Géolocalisation ASN            ml-threat
IP2Location     CIDRs par pays/ASN             ak47 (source CIDRs)
```

**Anonymisation** :
Requêtes OSINT routées via **Nym Mixnet** (SOCKS5 :1080) ou **ProtonVPN** (wg-gateway, exit FR ~149.102.244.100)""",

    "mitre-attack": """\
🎯 **MITRE ATT&CK — TTPs couverts**

```
Tactique            Technique                   Outil
──────────────────────────────────────────────────────────────────────
Reconnaissance      T1595 Active Scanning       ak47 (nmap) · masscan
Reconnaissance      T1592 Gather Host Info      bm12 (fingerprint + OSINT)
Initial Access      T1190 Exploit Public App    nuclei · uzi (MSF)
Credential Access   T1110 Brute Force           uzi (ssh/http/smb/db login)
C2                  T1071 App Layer Protocol    msf-teamserver · Fly.io
C2                  T1090 Proxy                 wg-gateway (ProtonVPN) · Nym
Defense Evasion     T1036 Masquerading          Meterpreter reverse HTTPS
Collection          T1005 Data from Local Sys   post-exploitation MSF
```

**Logging** : Suricata IDS détecte les TTPs · karacho blockchain log les incidents""",

    "monitoring": """\
📊 **Stack Monitoring**

```
Prometheus  scrape toutes les 15s
    ├── node-exporter    CPU/RAM/disk par nœud (global)
    ├── cadvisor         métriques containers (global)
    ├── postgres-exporter
    ├── redis-exporter
    ├── pentest-exporter stats scan borodino
    ├── c2-monitor       sessions MSF · msfrpcd up/down
    ├── dcgm-exporter    GPU meta-68 (NVIDIA T400)
    └── suricata-exporter

Grafana      dashboards · alertes visuelles
Loki         logs centralisés via Alloy (push)
Tempo        distributed tracing
Alertmanager routing → Proton Mail + Telegram
```

**Accès** : Grafana :3000 via Traefik · Prometheus :9090 (interne)""",

    "alertes": """\
🚨 **Pipeline d'alertes**

```
Règles Prometheus
       │
       ▼
 Alertmanager
       │
       ├── Proton Mail Bridge → email chiffré (réseau mail)
       └── Telegram → @Betty_Bombers_bot
```

**Alertes configurées** :
- `HostDiskSpaceWarning` / `HostDiskSpaceCritical`
- `ServiceDown` — replica manquant
- `HighCPU` — charge système élevée
- `MsfrpcdDown` — msf-teamserver hors ligne
- `C2SessionOpened` — nouvelle session Meterpreter

⚠️ Proton Mail Bridge : si SMTP rejette (`454 4.7.0`), re-login nécessaire via container one-shot.""",

    "security": """\
🔒 **Posture de sécurité**

**Détection active** :
- Suricata IDS/IPS (mode host, tous les workers) — règles ET + règles Dozor dynamiques
- medved honeypot — détection probes SSH/HTTP/RDP/SMB/FTP/Telnet

**Gestion des secrets** :
- Tout via `docker secret` — jamais de .env en production
- Rotation : `service rm → secret rm → secret create → redeploy`
- Accès : `/run/secrets/<name>` dans le container

**Réseau** :
- Ingress : Traefik (TLS Let's Encrypt)
- C2 : implants → redirecteurs Fly.io (nginx UA/GeoIP filter) → VPN → msf-teamserver LAN
- Scans sortants via ProtonVPN (exit FR ~149.102.244.100)
- OSINT via Nym Mixnet (SOCKS5, anonymisation)""",

    "faraday": """\
🐛 **DefectDojo — Vulnerability Management**

**Stack** : `dojo` → nginx + uWSGI + Celery Beat/Worker + dojo-triage

**Sources de findings importées** :
- OWASP ZAP → DAST web app findings
- Nuclei → CVE template findings
- uzi/MSF → sessions C2 (via c2-monitor)
- ml-threat → IoC enrichissement

**dojo-triage** :
Agent IA (Ollama mistral:7b-instruct) qui re-triage et classifie automatiquement les findings DefectDojo.

**API** : `http://defectdojo.bojemoi.lab.local/api/v2/`
Token via Docker secret `dojo_api_token`""",

    "trivy": """\
🔍 **Trivy — Container Security Scanner**

Scan automatique des images Docker buildées localement.

**Stack** : `trivy` → service `trivy-scanner`
**Scope** : toutes les images `localhost:5000/*`
**Intégration** : résultats exportés vers DefectDojo pour suivi CVE dans les dépendances

```bash
# Scan manuel d'une image
trivy image localhost:5000/<image>:latest
```""",

    "blog": """\
📝 **Blog — blog.bojemoi.me**

Blog technique **build in public** sur Hugo + thème PaperMod.

**CI/CD** : push Gitea → Gitea Actions → `hugo --minify` → deploy volume Docker

**Thèmes** :
- Threat intelligence & machine learning
- Infrastructure Docker Swarm / homelab
- Red team / pentest automatisé
- OSINT & CTI hacktivist
- DevOps & GitOps

**Tags standards** :
`threat-intelligence` · `cybersecurity` · `machine-learning` · `homelab` · `docker-swarm` · `build-in-public` · `french-tech`""",

    "projets": """\
🗺️ **Roadmap & Projets**

✅ **Terminé** :
- Pipeline borodino complet (ak47 → bm12 → nuclei → uzi)
- Infrastructure C2 multi-redirecteurs (Fly.io + WireGuard)
- DefectDojo + dojo-triage IA (mistral:7b)
- ML threat intel API (classificateur IoC)
- MCP server (intégration Claude Code)
- Honeypot medved multi-protocoles
- Blog Hugo CI/CD automatisé
- Discord serveur PTaaS

🔄 **En cours** :
- Optimisation uzi (post-exploitation, sessions persistantes)
- Enrichissement razvedka (Twitter CTI)
- Discord bot intégration lab (alertes, commandes)

📋 **Backlog** :
- Dashboard Grafana C2 amélioré
- Export MITRE ATT&CK automatisé
- Sentinel IoT (ESP32 WiFi probes)""",

    "ressources": """\
🔗 **Ressources & Liens utiles**

**Lab** :
- Gitea : https://gitea.bojemoi.me
- Blog : https://blog.bojemoi.me
- Telegram : @bojemoi_ptaas
- Bot : @Betty_Bombers_bot

**Outils** :
- Metasploit : https://docs.metasploit.com
- Nuclei : https://projectdiscovery.io/nuclei
- OWASP ZAP : https://zaproxy.org
- DefectDojo : https://defectdojo.com
- Suricata : https://suricata.io
- Nym Mixnet : https://nymtech.net

**Références sécurité** :
- MITRE ATT&CK : https://attack.mitre.org
- ANSSI/CERT-FR : https://cert.ssi.gouv.fr
- NVD CVEs : https://nvd.nist.gov
- OWASP Top 10 : https://owasp.org""",
}

for name, content in MESSAGES.items():
    if name in ch:
        print(f"→ #{name}...")
        post(ch[name], content)
        print(f"  ✓")
    else:
        print(f"  ⚠ #{name} introuvable")

print("\n✅ Done.")
