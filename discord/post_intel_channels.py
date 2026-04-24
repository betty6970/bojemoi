#!/usr/bin/env python3
"""Crée #grafana et #defectdojo dans la catégorie Intelligence et les peuple."""
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

def create_channel(name, topic, category_id):
    return api("POST", f"/guilds/{GUILD_ID}/channels", json={
        "name": name, "type": 0, "topic": topic, "parent_id": category_id,
    })

# Récupère tous les channels
channels = api("GET", f"/guilds/{GUILD_ID}/channels")

# Trouve la catégorie Intelligence
intel_cat = next((c for c in channels if c["type"] == 4 and "intelligence" in c["name"].lower()), None)
if not intel_cat:
    print("Catégorie Intelligence introuvable")
    exit(1)
print(f"Catégorie : {intel_cat['name']} (id={intel_cat['id']})")

# Vérifie si les channels existent déjà
existing = {c["name"]: c["id"] for c in channels if c["type"] == 0}

# ── Crée #grafana ────────────────────────────────────────────────────────────
if "grafana" not in existing:
    ch = create_channel("grafana", "Dashboards Grafana — monitoring, pentest, CTI, C2", intel_cat["id"])
    grafana_id = ch["id"]
    print(f"✓ Créé #grafana ({grafana_id})")
else:
    grafana_id = existing["grafana"]
    print(f"→ #grafana existe déjà ({grafana_id})")
time.sleep(0.5)

# ── Crée #defectdojo ─────────────────────────────────────────────────────────
if "defectdojo" not in existing:
    ch = create_channel("defectdojo", "Vulnerability management — cycle de vie des findings", intel_cat["id"])
    dojo_id = ch["id"]
    print(f"✓ Créé #defectdojo ({dojo_id})")
else:
    dojo_id = existing["defectdojo"]
    print(f"→ #defectdojo existe déjà ({dojo_id})")
time.sleep(0.5)

# ── Contenu #grafana ─────────────────────────────────────────────────────────
GRAFANA = [
    """\
📊 **Grafana — Observabilité du lab**

Grafana centralise toutes les métriques, logs et traces du cluster.
Accessible via Traefik sur le réseau `monitoring`.

```
Prometheus  ──► Grafana (métriques temps réel)
Loki        ──► Grafana (logs centralisés)
Tempo       ──► Grafana (traces distribuées)
```""",

    """\
**Dashboards disponibles**

📁 **Pentest**
```
Pentest Overview          Vue globale : services, redis, honeypot, IDS,
                          hosts découverts, vulns, feeds blocklist

Scan Results              Activité récente par outil :
                          Nuclei · ZAP · UZI · EVE alerts temps réel

C2 Sessions               Sessions Meterpreter actives et historique,
                          msfrpcd up/down, timeline sessions

Pentest & Vuln Mgmt       Tableau de bord consolidé :
                          ZAP · Nuclei · UZI · IDS · Honeypot · DefectDojo
```""",

    """\
📁 **Sécurité**
```
Security Monitoring       Alertes Suricata IDS — total, top signatures,
                          timeline

Vigie — CERT-FR           Bulletins ANSSI/CERT-FR sur 30j,
                          catégories, rate/heure, produits matchés

Sentinel — IoT            Devices inconnus/connus, alertes proximité,
                          heatmap détections par heure (7j)
```

📁 **ATT&CK**
```
MITRE ATT&CK Coverage     Heatmap techniques détectées (Suricata),
                          timeline, top 10 techniques, source breakdown
```

📁 **General**
```
GPU Temperature           NVIDIA T400 (meta-68) — température, utilisation
Loki — Ingestion          Volume de logs ingérés, débit, erreurs
```""",

    """\
**Sources de métriques scrappées**

```
Exporter               Port    Données
──────────────────────────────────────────────────────
node-exporter          9100    CPU · RAM · disk · réseau (par nœud)
cadvisor               8080    Métriques containers Docker
postgres-exporter      9187    Queries · connexions · locks · cache
redis-exporter         9634    Mémoire · hits · commandes/s
pentest-exporter       9999    Stats borodino (scans, findings, pwned)
c2-monitor             9305    Sessions MSF · msfrpcd status
suricata-exporter      9917    Alertes IDS · flows · protocoles
dcgm-exporter          GPU     Température · utilisation GPU (meta-68)
```

Collecteur : **Alloy** (agent Grafana unifié) — scrape logs → Loki · métriques → Prometheus""",
]

# ── Contenu #defectdojo ──────────────────────────────────────────────────────
DOJO = [
    """\
🐛 **DefectDojo — Vulnerability Management**

Plateforme centrale de gestion des vulnérabilités du lab.
Reçoit les findings de tous les outils offensifs et défensifs.

**Stack** : `dojo` (`70-service-defectdojo.yml`)
**API** : `http://defectdojo.bojemoi.lab.local/api/v2/`
**Auth** : Docker secret `dojo_api_token`""",

    """\
**Sources de findings**

```
Outil              Type          Import
──────────────────────────────────────────────────
OWASP ZAP          DAST          zap-scanner → API v2
Nuclei             CVE           nuclei-api  → API v2
Metasploit / uzi   Exploitation  c2-monitor  → API v2
Trivy              Container     trivy-scan  → API v2
ml-threat-intel    IoC           API v2
```""",

    """\
**Cycle de vie d'un finding**

```
1. IMPORT
   Outil détecte une vulnérabilité
         │
         ▼
2. CRÉATION
   DefectDojo API v2 → finding créé
   Statut : Active · Non vérifié
   Sévérité : Critical / High / Medium / Low / Info
         │
         ▼
3. TRIAGE AUTOMATIQUE (dojo-triage)
   Ollama mistral:7b-instruct analyse le finding
   ├── Déduplication (même vuln, même host)
   ├── Scoring de risque contextuel
   ├── Enrichissement description
   └── Priorisation recommandée
         │
         ▼
4. REVUE MANUELLE
   Statut → Verified (confirmé) ou False Positive
         │
         ├── False Positive → Closed
         └── Confirmed → Active · Verified
                   │
                   ▼
5. REMÉDIATION
   Fix appliqué → Statut : Mitigated ou Resolved
         │
         ▼
6. CLÔTURE
   Statut : Inactive · Resolved
   Conservé dans l'historique de l'engagement
```""",

    """\
**Structure organisationnelle**

```
Product (= cible / scope PTaaS)
  └── Engagement (= campagne de pentest)
        └── Test (= type de scan)
              └── Finding (= vulnérabilité individuelle)
                    ├── Titre
                    ├── Sévérité (Critical→Info)
                    ├── Description + PoC
                    ├── CWE / CVE
                    ├── Statut (Active / Mitigated / False Positive)
                    └── Notes de revue
```

**dojo-triage** tourne toutes les 6h — re-analyse les findings `Active · Non vérifié`
et met à jour automatiquement sévérité + notes via l'API DefectDojo.

**Métriques Grafana** : dashboard `Pentest & Vulnerability Management`
→ Critical/High/Medium pending · findings par outil · triage errors""",
]

print("\n─── #grafana ───")
for msg in GRAFANA:
    print(f"  → {msg[:50].strip()!r}...")
    post(grafana_id, msg)

print("\n─── #defectdojo ───")
for msg in DOJO:
    print(f"  → {msg[:50].strip()!r}...")
    post(dojo_id, msg)

print("\n✅ Done.")
