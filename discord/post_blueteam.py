#!/usr/bin/env python3
"""Ajoute un chapitre Blue Team dans #architecture."""
import os, time, requests
from pathlib import Path

TOKEN    = Path("/run/secrets/discord_bot_token").read_text().strip()
GUILD_ID = os.environ["GUILD_ID"]
BASE     = "https://discord.com/api/v10"
HDR      = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}

def api(method, path, retries=3, **kw):
    for attempt in range(retries):
        try:
            r = requests.request(method, f"{BASE}{path}", headers=HDR, timeout=15, **kw)
            if r.status_code == 429:
                wait = r.json().get("retry_after", 1)
                time.sleep(wait + 0.2)
                continue
            if r.status_code == 204:
                return {}
            r.raise_for_status()
            return r.json() if r.content else {}
        except requests.exceptions.ConnectionError as e:
            print(f"  [retry {attempt+1}/{retries}] {e}")
            time.sleep(2 ** attempt)
    return {}

def post(channel_id, content):
    api("POST", f"/channels/{channel_id}/messages", json={"content": content})
    time.sleep(0.8)

channels = api("GET", f"/guilds/{GUILD_ID}/channels")
ch = {c["name"]: c["id"] for c in channels if c["type"] == 0}
arch_id = ch.get("architecture")

SECTIONS = [
    """\
─────────────────────────────────────────────
## 🔵 Blue Team
─────────────────────────────────────────────""",

    """\
### Détection — Suricata IDS

Suricata tourne en **mode host** sur chaque worker (meta-68, meta-69, meta-70).
Il inspecte tout le trafic de la carte réseau physique en temps réel.

```
Trafic réseau (LAN + internet)
       │
       ▼
  Suricata (host network)
       │
       ├── eve.json → suricata-attack-enricher
       │                    │
       │              Enrichissement MITRE ATT&CK
       │              (technique, tactic, severity)
       │                    │
       │              PostgreSQL (events)
       │
       ├── suricata-exporter → Prometheus → Grafana
       │
       └── eve-cleaner (cron) → rotation logs
```

**Règles** :
- Emerging Threats (ET Open) — ~41 MB de règles
- Règles dynamiques générées par **dozor** (IoC feeds → règles Suricata)""",

    """\
### Détection — Honeypot medved

Honeypot multi-protocoles en **mode host** sur les workers.
Capture les tentatives d'intrusion sur les ports standards.

```
Ports exposés (host network)
  :22   SSH
  :8000 HTTP
  :3389 RDP
  :445  SMB
  :21   FTP
  :23   Telnet
       │
       ▼
  medved-honeypot
       │
       ▼
  PostgreSQL (honeypot_events)
  + Prometheus metrics
```""",

    """\
### Threat Intelligence

```
Sources externes                Pipeline
──────────────────              ──────────────────────────────────────
Telegram RU/HU channels ──────► razvedka → détection DDoS hacktivist
ANSSI/CERT-FR RSS feeds  ──────► vigie   → alertes bulletins sécurité
IoC feeds (OTX, etc.)    ──────► dozor   → règles Suricata dynamiques
IP / URL / Hash          ──────► ml-threat-intel-api
                                    │
                                    ├── ML classifier (score menace)
                                    ├── OSINT enrichment
                                    │   (VT · AbuseIPDB · Shodan · OTX)
                                    └── DefectDojo findings
```""",

    """\
### Monitoring & Alerting

```
Exporters (tous les nœuds)
  node-exporter   CPU · RAM · disk · réseau
  cadvisor        métriques containers
  postgres-exp    queries · connexions · locks
  redis-exporter  mémoire · hits/misses
  pentest-exp     stats scan borodino
  c2-monitor      sessions MSF · msfrpcd up/down
  suricata-exp    alertes IDS · événements réseau
  dcgm-exporter   GPU meta-68 (NVIDIA T400)
       │
       ▼
  Prometheus (15 jours de rétention, 10 GB)
       │
       ├── Grafana (dashboards · alertes visuelles)
       ├── Loki    (logs centralisés via Alloy)
       └── Tempo   (distributed tracing OTLP)

  Alertmanager
       ├── ProtonMail (email chiffré)
       └── Telegram @Betty_Bombers_bot
```""",

    """\
### Vulnerability Management — DefectDojo

Centralise tous les findings issus des outils offensifs **et** défensifs.

```
Sources                   →  DefectDojo  →  dojo-triage (IA)
──────────────────────────────────────────────────────────────
ZAP (DAST web)                               Ollama mistral:7b
Nuclei (CVE templates)                       Re-triage automatique
uzi/MSF (exploitation)                       Déduplication
Trivy (container CVEs)                       Scoring
ml-threat (IoC)                              Priorisation
```

**API** : `http://defectdojo.bojemoi.lab.local/api/v2/`""",

    """\
### Résumé Blue Team

| Couche | Outil | Rôle |
|--------|-------|------|
| Réseau | Suricata IDS | Détection intrusion temps réel |
| Réseau | dozor | Règles IDS dynamiques depuis IoC |
| Déception | medved | Honeypot multi-protocoles |
| CTI | razvedka | Veille hacktivisme DDoS |
| CTI | vigie | Alertes ANSSI/CERT-FR |
| CTI | ml-threat | Classification IoC par ML |
| Metrics | Prometheus + Grafana | Observabilité cluster |
| Logs | Loki + Alloy | Logs centralisés |
| Alertes | Alertmanager | Mail chiffré + Telegram |
| Vulns | DefectDojo + dojo-triage | Gestion et triage IA |""",
]

print("Envoi du chapitre Blue Team dans #architecture...")
for s in SECTIONS:
    print(f"  → {s[:50].strip()!r}...")
    post(arch_id, s)

print("\n✅ Done.")
