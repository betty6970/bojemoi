#!/usr/bin/env python3
"""Crée #prometheus, #traefik et #dnsmasq dans la catégorie Intelligence et les peuple."""
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

existing = {c["name"]: c["id"] for c in channels if c["type"] == 0}

# ── Crée les channels ─────────────────────────────────────────────────────────
for name, topic in [
    ("prometheus",  "Métriques et alerting — scrape config, rules, targets"),
    ("traefik",     "Reverse proxy — routing, TLS, entrypoints, middlewares"),
    ("dnsmasq",     "DNS interne — domaines .bojemoi.lab, résolution locale"),
]:
    if name not in existing:
        ch = create_channel(name, topic, intel_cat["id"])
        existing[name] = ch["id"]
        print(f"✓ Créé #{name} ({ch['id']})")
    else:
        print(f"→ #{name} existe déjà ({existing[name]})")
    time.sleep(0.5)

# ── Contenu #prometheus ────────────────────────────────────────────────────────
PROMETHEUS = [
    """\
📈 **Prometheus — Métriques & Alerting**

Collecte et stocke toutes les métriques du cluster. Expose un endpoint de requêtes PromQL.
Accessible via Traefik : `https://prometheus.bojemoi.lab` (Basic Auth)

```
Stack    : base  (01-service-hl.yml)
Image    : localhost:5000/prometheus:latest  ← prom/prometheus
Port     : 9090  (interne, via Traefik)
Rétention: 15 jours · 10 GB max
WAL      : compressé
```""",

    """\
**Découverte des cibles (Service Discovery)**

```
Méthode                  Cibles découvertes
─────────────────────────────────────────────────────────────────
dockerswarm_sd (nodes)   node-exporter :9100 sur chaque nœud
                         dcgm-exporter :9400 (nœuds nvidia.vgpu=true)
dockerswarm_sd (tasks)   Tous les services avec label
                             prometheus.enable=true
                         Filtre réseau : monitoring uniquement
                         Port depuis label prometheus.port=<n>
dns_sd tasks.*           cadvisor       tasks.base_cadvisor :8080
                         suricata-exp   tasks.base_suricata-exporter :9917
static_configs           alertmanager   :9093
                         grafana        :3000
                         loki           :3100
                         tempo          :3200
                         alloy          :12345
                         postfix-exp    :9154
                         postgres-exp   :9187
                         sentinel       sentinel_collector:9101
```""",

    """\
**Jobs actifs (prometheus.yml)**

```
Job                   Méthode          Détail
────────────────────────────────────────────────────────────────
prometheus            static           localhost:9090 (self)
alertmanager          static           alertmanager:9093
grafana               static           grafana:3000
loki / tempo / alloy  static           ports 3100 / 3200 / 12345
postfix               static           postfix-exporter:9154
postgresql            static           postgres-exporter:9187
sentinel-collector    static           sentinel_collector:9101
docker-swarm-nodes    dockerswarm/node node-exporter auto-découverte
docker-swarm-services dockerswarm/task label prometheus.enable=true
cadvisor              dns_sd           tasks.base_cadvisor :8080
suricata              dns_sd           tasks.base_suricata-exporter :9917
node-exporter         dockerswarm/node :9100 sur chaque nœud
dcgm-exporter         dockerswarm/node :9400 (nœuds NVIDIA)
```""",

    """\
**Labels Prometheus sur les services Docker**

Chaque service déclare ses labels dans le stack YAML :
```
prometheus.enable=true          # Active le scrape
prometheus.port=9999            # Port de l'exporter
prometheus.path=/metrics        # Chemin (défaut /metrics)
prometheus.label.team=security  # Label custom → label PromQL
prometheus.label.component=ids  # Idem
prometheus.label.stack=base     # Idem
```

**Règles d'alerte** (`/etc/prometheus/rules/*.yml`)
```
alert_rules.yml    NodeDown · NodeHighCPU · NodeHighMemory · DiskFull
alerts.yml         Alertes services (containers, stacks critiques)
recording_rules.yml  Agrégations pré-calculées (swarm:node:cpu_usage_percent…)
sentinel_alerts.yml  Détections IoT proximité (ESP32/BLE)
```

**Alertmanager** → ProtonMail chiffré + Telegram @Betty_Bombers_bot""",
]

# ── Contenu #traefik ──────────────────────────────────────────────────────────
TRAEFIK = [
    """\
🔀 **Traefik — Reverse Proxy**

Point d'entrée unique pour tous les services web du lab.
Auto-découverte des services via Docker Swarm labels.

```
Stack    : boot  (01-boot-service.yml)
Image    : traefik:latest
Mode     : global (manager uniquement)
Provider : Docker Swarm via docker-socket-proxy :2375
```""",

    """\
**Entrypoints**

```
Entrypoint    Port  Protocole  Usage
──────────────────────────────────────────────────────
web           80    HTTP       Redirige → websecure (HTTPS)
websecure     443   HTTPS      TLS wildcard *.bojemoi.lab
meterpreter   4444  TCP        Passthrough C2 → msf-teamserver
metrics       8085  HTTP       Métriques Prometheus Traefik
```

**TLS** : Certificat wildcard `*.bojemoi.lab` (mkcert, auto-signé)
Montage : `/opt/bojemoi/volumes/traefik/certs/`
Config dynamic : `dynamic-config.yml` → `/etc/traefik/dynamic/`""",

    """\
**Routing — Exemples de services exposés**

```
Hostname                       Service → Port
───────────────────────────────────────────────────────────────
traefik.bojemoi.lab            Dashboard Traefik :8080 (BasicAuth)
grafana.bojemoi.lab            Grafana :3000
prometheus.bojemoi.lab         Prometheus :9090 (BasicAuth)
pgadmin.bojemoi.lab            pgAdmin :80
tempo.bojemoi.lab              Tempo :3200
dnsmasq.bojemoi.lab            dnsmasq webproc :8080
defectdojo.bojemoi.lab         DefectDojo :80
```

Chaque service déclare son routage via labels Docker :
```yaml
traefik.enable=true
traefik.swarm.network=proxy
traefik.http.routers.<name>.rule=Host(`service.bojemoi.lab`)
traefik.http.routers.<name>.entrypoints=websecure
traefik.http.routers.<name>.tls=true
traefik.http.services.<name>.loadbalancer.server.port=<port>
```""",

    """\
**Middlewares**

```
Middleware                  Type         Effet
────────────────────────────────────────────────────────────────────
redirect-to-https          redirectScheme  HTTP → HTTPS permanent
prometheus-auth            basicAuth       Accès Prometheus (admin)
traefik-auth               basicAuth       Dashboard Traefik (admin)
security-headers           headers         HSTS · X-Frame-Options
                                           X-Content-Type-Options
                                           Referrer-Policy
                                           X-Robots-Tag noindex
```

**Métriques Prometheus** exposées sur `:8085/metrics`
→ Labels par entrypoint, par service, histogramme latences (buckets 0.1…5s)
→ Scraped par Prometheus via label `prometheus.enable=true`

**Réseau Swarm** : Traefik écoute sur le réseau `proxy` (overlay)
Toutes les communications inter-services passent par ce réseau.""",
]

# ── Contenu #dnsmasq ──────────────────────────────────────────────────────────
DNSMASQ = [
    """\
🌐 **dnsmasq — DNS Interne du Lab**

Serveur DNS autoritaire pour le domaine `bojemoi.lab`.
Résout tous les noms internes vers les IPs du cluster.

```
Stack    : boot  (01-boot-service.yml)
Image    : jpillora/dnsmasq:latest
Port     : 53/udp + 53/tcp  (exposé sur le manager)
UI Web   : dnsmasq.bojemoi.lab (via Traefik, BasicAuth)
Placement: manager uniquement (meta-76 — 192.168.1.121)
```

**Config** : montée depuis `/opt/bojemoi/volumes/dnsmask/`""",

    """\
**Configuration principale** (`dnsmasq.conf`)

```
domain=bojemoi.lab          # Domaine local
local=/bojemoi.lab/         # Autoritaire pour cette zone
expand-hosts                # Ajoute .bojemoi.lab aux noms courts
no-resolv                   # N'utilise pas /etc/resolv.conf
server=8.8.8.8              # Upstream DNS Google
server=1.1.1.1              # Upstream DNS Cloudflare
cache-size=10000            # Cache 10k entrées
neg-ttl=60                  # TTL négatif 60s
conf-dir=/etc/dnsmasq.d    # Fichiers de conf supplémentaires
```

**Clients DNS** : tous les nœuds Swarm + machines du LAN
pointent vers `192.168.1.121:53`""",

    """\
**Enregistrements A — Infrastructure** (`dnsmasq.d/01-base.conf`)

```
Nom                          IP               Rôle
───────────────────────────────────────────────────────────────
xenserver.bojemoi.lab        192.168.1.29     Hyperviseur XenServer
traefik.bojemoi.lab          192.168.1.121    Dashboard Traefik
prometheus.bojemoi.lab       192.168.1.121    Métriques Prometheus
grafana.bojemoi.lab          192.168.1.121    Dashboards Grafana
alertmanager.bojemoi.lab     192.168.1.121    Alertes Alertmanager
loki.bojemoi.lab             192.168.1.121    Logs Loki
tempo.bojemoi.lab            192.168.1.121    Traces Tempo
alloy.bojemoi.lab            192.168.1.121    Collecteur Alloy
pgadmin.bojemoi.lab          192.168.1.121    pgAdmin
registry.bojemoi.lab         192.168.1.121    Docker Registry
mail.bojemoi.lab             192.168.1.121    Postfix SMTP
dnsmasq.bojemoi.lab          192.168.1.121    UI dnsmasq
```""",

    """\
**Enregistrements A — Pentest & Sécurité**

```
Nom                          IP               Rôle
───────────────────────────────────────────────────────────────
zaproxy.bojemoi.lab          192.168.1.142    OWASP ZAP (worker)
                             192.168.1.145    (multi-instance)
                             192.168.1.196
defectdojo.bojemoi.lab       192.168.1.121    Vuln management
dojo.bojemoi.lab             192.168.1.121    (alias)
metasploit.bojemoi.lab       192.168.1.121    MSF/C2
lhost.bojemoi.lab            192.168.1.121    Listener meterpreter
pentest-exporter.bojemoi.lab 192.168.1.121    Métriques borodino
redis-exporter.bojemoi.lab   192.168.1.121    Redis metrics
```

**Environnements vulnérables (cibles de test)**
```
dvwa.bojemoi.lab · webgoat.bojemoi.lab · juice-shop.bojemoi.lab
target.bojemoi.lab · vulnerable.bojemoi.lab · test.bojemoi.lab
```

**VPN** : `vpn.bojemoi.lab` → `10.13.13.1` (tunnel C2 redirectors)""",
]

# ── Envoi ─────────────────────────────────────────────────────────────────────
for name, messages in [
    ("prometheus", PROMETHEUS),
    ("traefik",    TRAEFIK),
    ("dnsmasq",    DNSMASQ),
]:
    cid = existing[name]
    print(f"\n─── #{name} ───")
    for msg in messages:
        print(f"  → {msg[:50].strip()!r}...")
        post(cid, msg)

print("\n✅ Done.")
