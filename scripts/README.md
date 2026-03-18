# Bojemoi Lab - Breachforum Onion Discovery Service

## Overview

Service automatisé de découverte et validation des adresses onion Breachforum pour la pipeline CTI de Bojemoi Lab.

**Caractéristiques:**
- ✓ Scraping multi-source (Ahmia, Reddit, répertoires Tor)
- ✓ Validation format & connectivité via Tor SOCKS
- ✓ Persistence PostgreSQL avec versioning
- ✓ Alertes Telegram sur nouvelles découvertes
- ✓ API FastAPI pour intégration avec l'orchestrateur existant
- ✓ Conteneurisation Docker avec isolation Tor
- ✓ Scheduling automatique (cron-like)

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Bojemoi Lab Orchestrator (FastAPI)             │
├─────────────────────────────────────────────────┤
│  /api/cti/breachforum/onion                     │
│  /api/cti/breachforum/discover                  │
│  /api/cti/breachforum/status                    │
└─────────────────────────────────────────────────┘
           │
           ├──> breachforum_discovery_api.py (module)
           │
           ├──> breachforum_onion_discovery.py (service)
           │    ├─ AhmiaSource (scrape Ahmia API)
           │    ├─ RedditSource (scrape Reddit)
           │    └─ TorProjectListSource (scan directories)
           │
           └──> PostgreSQL (cti schema)
                ├─ onion_discoveries (table)
                ├─ discovery_audit_log (table)
                └─ onion_enrichment (MISP/TheHive)

├─ Tor SOCKS5 (:9050)
│  └─ Validation connectivité onions

└─ Telegram Bot
   └─ Alertes de découverte
```

---

## Installation

### 1. Prérequis

- Docker & Docker Compose
- PostgreSQL 13+ (ou intégré)
- Python 3.11+ (optionnel pour tests locaux)
- Tor (intégré dans Docker)

### 2. Déploiement Quick-Start

```bash
# Cloner/copier les fichiers
cp breachforum_onion_discovery.py .
cp breachforum_discovery_api.py .
cp Dockerfile.discovery .
cp docker-compose.discovery.yml .

# Configuration
export DB_PASSWORD=$(openssl rand -base64 32)
export TELEGRAM_BOT_TOKEN="your_token_here"
export TELEGRAM_CHAT_ID="-your_chat_id"

# Déployer
docker-compose -f docker-compose.discovery.yml up -d

# Vérifier
docker logs -f bojemoi_discovery
```

### 3. Intégration FastAPI existante

```python
# Dans main.py de l'orchestrateur Bojemoi Lab:

from breachforum_discovery_api import router, init_breachforum_discovery

@app.on_event("startup")
async def startup():
    init_breachforum_discovery(
        db_config={
            "host": os.getenv("DB_HOST"),
            "database": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASS"),
        },
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID")
    )

app.include_router(router)
```

---

## API Endpoints

### GET /api/cti/breachforum/onion

Récupérer l'adresse onion actuelle de Breachforum.

**Query Parameters:**
- `refresh` (bool, optional): Forcer une redécouverte

**Response:**
```json
{
  "success": true,
  "primary_onion": "xyz1234567890abcd.onion",
  "all_candidates": [
    "xyz1234567890abcd.onion",
    "abc9876543210xyz.onion"
  ],
  "validated_count": 2,
  "discovery_sources": ["ahmia", "reddit", "tor_directory"],
  "timestamp": "2024-03-18T14:30:00Z"
}
```

**Example:**
```bash
curl http://localhost:8000/api/cti/breachforum/onion
curl "http://localhost:8000/api/cti/breachforum/onion?refresh=true"
```

---

### POST /api/cti/breachforum/discover

Déclencher une découverte manuelle (s'exécute en background).

**Request Body:**
```json
{
  "force_refresh": true,
  "test_connectivity": true,
  "notify_telegram": true
}
```

**Response:**
```json
{
  "status": "discovery_queued",
  "message": "Discovery job started in background"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/cti/breachforum/discover \
  -H "Content-Type: application/json" \
  -d '{"force_refresh": true, "test_connectivity": true, "notify_telegram": true}'
```

---

### GET /api/cti/breachforum/status

Vérifier le statut et les logs récents du service.

**Response:**
```json
{
  "service": "breachforum_discovery",
  "status": "operational",
  "current_onion": "xyz1234567890abcd.onion",
  "recent_candidates": ["xyz1234567890abcd.onion", ...],
  "timestamp": "2024-03-18T14:30:00Z"
}
```

---

## Configuration

### Variables d'environnement

```bash
# PostgreSQL
DB_HOST=postgres.bojemoi.local
DB_NAME=bojemoi_cti
DB_USER=cti_user
DB_PASS=<generated>

# Tor Proxy (pour validation connectivité)
PROXY_URL=socks5://tor:9050
USER_AGENT="Mozilla/5.0..."

# Telegram Alerting
TELEGRAM_BOT_TOKEN=<your_bot_token>
TELEGRAM_CHAT_ID=<your_chat_id>

# Optionnel
LOG_LEVEL=INFO
DISCOVERY_INTERVAL=3600  # seconds
```

### PostgreSQL Schema

```sql
-- Tables créées automatiquement:

cti.onion_discoveries
├─ id (PK)
├─ address (VARCHAR, UNIQUE)
├─ source (VARCHAR)
├─ confidence (FLOAT 0.0-1.0)
├─ discovered_at (TIMESTAMP)
├─ last_verified (TIMESTAMP)
├─ is_active (BOOLEAN)
├─ metadata (JSONB)
└─ verified_hash (VARCHAR)

cti.discovery_audit_log
├─ id (PK)
├─ timestamp (TIMESTAMP)
├─ onion (VARCHAR)
├─ source (VARCHAR)
└─ status (VARCHAR)

cti.onion_enrichment  (optionnel)
├─ onion (FK)
├─ misp_event_id (INT)
├─ thehive_case_id (VARCHAR)
├─ threat_level (VARCHAR)
└─ last_enriched (TIMESTAMP)
```

---

## Sources de découverte

### 1. Ahmia (Onion Search Engine)

- **URL**: https://ahmia.fi/search/?q=breachforum&format=json
- **Confiance**: 0.7 (modérée)
- **Fréquence**: Public, non-authentifié
- **Avantage**: API JSON structurée

### 2. Reddit (r/darknet, r/Tor)

- **URL**: https://reddit.com/r/darknet/search?q=breachforum
- **Confiance**: 0.6 (basse à modérée)
- **Fréquence**: Discussions communautaires
- **Avantage**: Vérification par la communauté

### 3. Répertoires Tor

- **URL**: https://thehiddenwiki.com, https://deepweblinks.net
- **Confiance**: 0.65 (modérée)
- **Fréquence**: Maintenance manuelle, peut être obsolète
- **Avantage**: Base de données documentée

### 4. CTI Reports (optionnel)

- Intégrer Flashpoint, Digital Shadows, Mandiant
- Intégrer Shodan/Censys API si disponible

---

## Validation & Sécurité

### Format Validation
```python
# V2 onion (16 caractères)
regex: [a-z2-7]{16}\.onion

# V3 onion (56 caractères)
regex: [a-z2-7]{56}\.onion
```

### Connectivité Test
```python
# Via Tor SOCKS5 (optionnel)
- Vérifier HTTP 200/3xx
- Timeout: 10s
- Pas de follow-redirects (détection clones)
```

### Détection Phishing
```python
# Vérifier que l'adresse se trouve sur MULTIPLES sources
# Croiser avec base de données d'adresses connues
# Valider signatures PGP si disponibles
```

### Isolation de la Lab
```bash
# Tout scraping passe par Tor
# IP source: randomisée via Tor circuit
# User-Agent: Firefox standard (pas de signature Bojemoi)
# Logs: Pas de corrélation directe avec lab
```

---

## Exemples d'utilisation

### En Python (asyncio)

```python
import httpx
import asyncio

async def get_breachforum_onion():
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://localhost:8000/api/cti/breachforum/onion")
        data = resp.json()
        return data['primary_onion']

# Usage
onion = asyncio.run(get_breachforum_onion())
print(f"Breachforum: {onion}")
```

### En Bash

```bash
# Récupérer l'adresse
ONION=$(curl -s http://localhost:8000/api/cti/breachforum/onion | jq -r '.primary_onion')

# Configurer proxy Tor pour accès
export http_proxy="socks5://127.0.0.1:9050"
export https_proxy="socks5://127.0.0.1:9050"

# Scraper avec Tor
curl -x socks5h://localhost:9050 "http://${ONION}/"
```

### En Shell script Bojemoi Lab

```bash
#!/bin/bash
# Trigger discovery + récupérer adresse

curl -X POST http://bojemoi-orchestrator:8000/api/cti/breachforum/discover \
  -H "Content-Type: application/json" \
  -d '{"force_refresh": true, "notify_telegram": true}'

sleep 10

ONION=$(curl -s http://bojemoi-orchestrator:8000/api/cti/breachforum/onion | jq -r '.primary_onion')
echo "Current Breachforum: $ONION"
```

---

## Intégration Gitea Webhook

Déclencher découverte à chaque push sur la branche `cti_config`:

```json
{
  "Payload URL": "http://bojemoi-orchestrator:8000/api/cti/breachforum/discover",
  "HTTP Method": "POST",
  "Content Type": "application/json",
  "Events": ["push"],
  "Active": true
}
```

---

## Intégration MISP/TheHive

```python
from pymisp import PyMISP

def enrich_with_misp(onion_address):
    misp = PyMISP(misp_url, misp_key)
    
    # Créer événement
    event = misp.new_event(
        distribution=0,  # Internal
        threat_level_id=3,  # Amber
        analysis=1,  # Ongoing
        info=f"Breachforum Activity - {onion_address}"
    )
    
    # Ajouter observable
    event.add_attribute('url', f'http://{onion_address}', comment='Breachforum')
    event.add_attribute('comment', 'Automated discovery from Bojemoi CTI')
    event.add_tag('breach_forum')
    event.add_tag('threat_actor')
    
    # Sauvegarder
    response = misp.update_event(event)
    return response
```

---

## Maintenance

### Nettoyage régulier

```bash
# Désactiver adresses inactives (> 7 jours)
docker exec bojemoi_discovery python << 'EOF'
import psycopg2
conn = psycopg2.connect(...)
cur = conn.cursor()
cur.execute("""
    UPDATE cti.onion_discoveries 
    SET is_active = FALSE 
    WHERE last_verified < NOW() - INTERVAL '7 days'
""")
conn.commit()
EOF

# Archiver logs d'audit
docker exec bojemoi_discovery python << 'EOF'
import psycopg2
conn = psycopg2.connect(...)
cur = conn.cursor()
cur.execute("""
    DELETE FROM cti.discovery_audit_log 
    WHERE timestamp < NOW() - INTERVAL '90 days'
""")
conn.commit()
EOF
```

### Monitoring

```bash
# Vérifier la connexion à Tor
docker exec bojemoi_tor nc -z localhost 9050

# Logs du service
docker logs -f bojemoi_discovery

# Statut Postgres
docker exec bojemoi_discovery psql -h postgres -U cti_user -d bojemoi_cti \
  -c "SELECT COUNT(*) FROM cti.onion_discoveries WHERE is_active = TRUE;"
```

---

## Troubleshooting

### "PostgreSQL connection failed"
```bash
# Vérifier les crédentials
docker exec bojemoi_discovery psql -h postgres -U cti_user -d bojemoi_cti -c "SELECT 1"

# Attendre que Postgres soit prêt
docker-compose up -d && sleep 10
```

### "Tor SOCKS5 unreachable"
```bash
# Vérifier Tor
docker exec bojemoi_tor curl -x socks5h://localhost:9050 http://check.torproject.org/api/ip

# Redémarrer Tor
docker restart bojemoi_tor
```

### "No candidates found"
```bash
# Vérifier les sources
docker logs bojemoi_discovery | grep -i "ahmia\|reddit\|directory"

# Tester manuellement
curl "https://ahmia.fi/search/?q=breachforum&format=json"
```

---

## Performance & Scalabilité

- **Discovery interval**: 1h par défaut (configurable)
- **Concurrent sources**: 4 (Ahmia, Reddit x2, Directories)
- **Timeout par source**: 10s
- **DB retention**: 90 jours (audit), illimité (discoveries actives)
- **Throughput**: ~4-6 adresses/run

---

## Considérations opérationnelles

### Légales
- Scraping via Tor: Conforme (pas de signature directe)
- Consultation publique: Légale
- Stockage: Limiter à la metadata nécessaire

### OPSEC
- Ne PAS hardcoder l'adresse onion en clair dans le code
- Logs → PostgreSQL chiffré
- Telegram → Token stocké en env var sécurisé
- Rotation des proxies Tor

---

## Améliorations futures

- [ ] Support Breachforum v3 onion migré
- [ ] Intégration MISP/TheHive automatique
- [ ] Vérification PGP des signatures admin
- [ ] ML detection des clones malveillants
- [ ] Integration avec MISP feeds publics
- [ ] Métriques Prometheus/Grafana
- [ ] Support multi-forum (Exploit.in, RaidForums archives)

---

## Support & Documentation

**Test complet:**
```bash
python examples_usage.py
```

**Logs en temps réel:**
```bash
docker logs -f bojemoi_discovery
```

**Vérifier les données:**
```bash
docker exec bojemoi_discovery psql -h postgres -U cti_user -d bojemoi_cti \
  -c "SELECT * FROM cti.onion_discoveries LIMIT 5;"
```

---

**Auteur**: Bojemoi Lab CTI Team  
**Version**: 1.0  
**Last Updated**: 2024-03-18
