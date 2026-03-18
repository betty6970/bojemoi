#!/usr/bin/env bash
# Bojemoi Lab - Breachforum Onion Discovery Setup
# Intégration dans l'orchéstrateur FastAPI existant

# ============== 1. VARIABLES D'ENVIRONNEMENT ==============
# Ajouter à .env ou docker compose:

export DB_HOST="postgres.bojemoi.local"
export DB_NAME="bojemoi_cti"
export DB_USER="cti_user"
export DB_PASS="$(openssl rand -base64 32)"

export PROXY_URL="socks5://tor:9050"
export USER_AGENT="Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/109.0"

# Telegram alerting (optionnel mais recommandé)
export TELEGRAM_BOT_TOKEN="123456:ABCdefGHIjklmnoPQRstuvWXYZab"
export TELEGRAM_CHAT_ID="-987654321"

# ============== 2. INITIALISATION DB ==============
# Créer les tables CTI
cat > /tmp/init_cti_db.sql << 'EOF'
CREATE SCHEMA IF NOT EXISTS cti;

-- Table de découverte d'onions
CREATE TABLE IF NOT EXISTS cti.onion_discoveries (
    id SERIAL PRIMARY KEY,
    address VARCHAR(100) UNIQUE NOT NULL,
    source VARCHAR(50) NOT NULL,
    confidence FLOAT DEFAULT 0.5,
    discovered_at TIMESTAMP DEFAULT NOW(),
    last_verified TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB,
    verified_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Audit log
CREATE TABLE IF NOT EXISTS cti.discovery_audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    onion VARCHAR(100),
    source VARCHAR(50),
    status VARCHAR(50),
    message TEXT
);

-- Indices de performance
CREATE INDEX IF NOT EXISTS idx_onion_active ON cti.onion_discoveries(is_active, last_verified DESC);
CREATE INDEX IF NOT EXISTS idx_onion_confidence ON cti.onion_discoveries(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON cti.discovery_audit_log(timestamp DESC);

-- Intégration MISP/TheHive (optionnel)
CREATE TABLE IF NOT EXISTS cti.onion_enrichment (
    onion VARCHAR(100) REFERENCES cti.onion_discoveries(address) ON DELETE CASCADE,
    misp_event_id INT,
    thehive_case_id VARCHAR(100),
    threat_level VARCHAR(20),
    last_enriched TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (onion, misp_event_id)
);

GRANT ALL PRIVILEGES ON SCHEMA cti TO cti_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA cti TO cti_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA cti TO cti_user;
EOF

# Appliquer via PostgreSQL
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f /tmp/init_cti_db.sql

# ============== 3. INTÉGRATION FASTAPI ==============
# Ajouter au fichier main.py existant:

# === main.py ===
cat > /tmp/main_integration.py << 'EOF'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Import du module discovery
from breachforum_discovery_api import (
    router as breachforum_router,
    init_breachforum_discovery
)

app = FastAPI(title="Bojemoi Lab CTI Orchestrator")

# CORS (à adapter à ta config)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://bojemoi.lab"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    """Initialiser discovery service au démarrage"""
    db_config = {
        "host": os.getenv("DB_HOST"),
        "database": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASS"),
    }
    
    init_breachforum_discovery(
        db_config=db_config,
        telegram_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID")
    )
    
    # Autres services...
    print("✓ CTI services initialized")

# Routes
app.include_router(breachforum_router)

# tes autres routers...

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
EOF

# ============== 4. DOCKER DEPLOYMENT ==============

# Construire l'image discovery
docker build -f Dockerfile.discovery -t bojemoi/discovery:latest .

# Lancer avec docker-compose
docker-compose -f docker-compose.discovery.yml up -d

# Vérifier les logs
docker logs -f bojemoi_discovery

# ============== 5. WEBHOOK GITEA ==============
# Déclencher découverte au push (optionnel)
# Ajouter au .gitea/hooks/push

cat > .gitea/hooks/post-receive << 'EOF'
#!/bin/bash
# Trigger discovery on CTI repo push

REPO_NAME=$1
if [ "$REPO_NAME" == "bojemoi_lab/cti_config" ]; then
    echo "[Discovery] Triggering from Gitea hook..."
    curl -X POST http://localhost:8000/api/cti/breachforum/discover \
        -H "Content-Type: application/json" \
        -d '{"force_refresh": true, "notify_telegram": true}'
fi
EOF

chmod +x .gitea/hooks/post-receive

# ============== 6. ENDPOINTS DISPONIBLES ==============

echo "=== Breachforum Discovery API Endpoints ==="
echo ""
echo "GET /api/cti/breachforum/onion"
echo "  Récupère l'adresse onion actuelle"
echo "  ?refresh=true pour forcer la redécouverte"
echo ""
echo "POST /api/cti/breachforum/discover"
echo "  Déclenche une découverte manuelle"
echo "  Body: {\"force_refresh\": true, \"test_connectivity\": true, \"notify_telegram\": true}"
echo ""
echo "GET /api/cti/breachforum/status"
echo "  Status du service de découverte"
echo ""

# ============== 7. MONITORING ==============

# Ajouter à Prometheus/Grafana
cat > prometheus_discovery.yml << 'EOF'
- job_name: 'bojemoi_discovery'
  static_configs:
    - targets: ['localhost:8000']
  metrics_path: '/metrics'
  scrape_interval: 60s
EOF

# ============== 8. LOGS & DEBUGGING ==============

echo "Vérifier les découvertes stockées:"
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \
    "SELECT address, source, confidence, last_verified FROM cti.onion_discoveries ORDER BY last_verified DESC LIMIT 5;"

echo "Voir l'audit log:"
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \
    "SELECT * FROM cti.discovery_audit_log ORDER BY timestamp DESC LIMIT 10;"

# ============== 9. MAINTENANCE ==============

# Cleanup des adresses inactives (> 7 jours sans vérification)
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \
    "UPDATE cti.onion_discoveries SET is_active = FALSE WHERE last_verified < NOW() - INTERVAL '7 days';"

# Archivage des logs d'audit anciens
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c \
    "DELETE FROM cti.discovery_audit_log WHERE timestamp < NOW() - INTERVAL '90 days';"

echo "✓ Setup complete!"
