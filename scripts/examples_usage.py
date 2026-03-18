#!/usr/bin/env python3
"""
Breachforum Discovery Service - Test & Usage Examples
"""

import asyncio
import httpx
import json
from datetime import datetime

# ============== CONFIG ==============
API_BASE = "http://localhost:8000/api/cti/breachforum"

# ============== EXAMPLES ==============

async def example_1_get_current_onion():
    """
    Example 1: Récupérer l'adresse onion actuelle
    """
    print("\n[Example 1] GET current onion")
    print("-" * 60)
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/onion")
        data = resp.json()
        
        print(f"Status: {'✓ SUCCESS' if resp.status_code == 200 else '✗ FAILED'}")
        print(f"Primary Onion: {data.get('primary_onion', 'NOT_FOUND')}")
        print(f"Validated Candidates: {data.get('validated_count', 0)}")
        print(f"All Candidates: {json.dumps(data.get('all_candidates', []), indent=2)}")
        print(f"Discovery Sources: {', '.join(data.get('discovery_sources', []))}")
        print(f"Timestamp: {data.get('timestamp')}")

async def example_2_force_refresh():
    """
    Example 2: Forcer une redécouverte (avec refresh=true)
    """
    print("\n[Example 2] Force refresh discovery")
    print("-" * 60)
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/onion?refresh=true")
        data = resp.json()
        
        print(f"Status: {'✓ SUCCESS' if resp.status_code == 200 else '✗ FAILED'}")
        print(f"Refresh triggered: {data.get('success', False)}")
        print(f"Found: {data.get('validated_count', 0)} candidates")

async def example_3_trigger_manual_discovery():
    """
    Example 3: Déclencher une découverte manuelle (POST)
    """
    print("\n[Example 3] Trigger manual discovery")
    print("-" * 60)
    
    payload = {
        "force_refresh": True,
        "test_connectivity": True,
        "notify_telegram": True
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/discover",
            json=payload
        )
        data = resp.json()
        
        print(f"Status: {'✓ SUCCESS' if resp.status_code == 200 else '✗ FAILED'}")
        print(f"Response: {json.dumps(data, indent=2)}")
        print(f"Note: Discovery runs in background, check /status for results")

async def example_4_check_service_status():
    """
    Example 4: Vérifier le statut du service
    """
    print("\n[Example 4] Check service status")
    print("-" * 60)
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/status")
        data = resp.json()
        
        print(f"Service Status: {data.get('status', 'UNKNOWN')}")
        print(f"Current Onion: {data.get('current_onion', 'NONE')}")
        print(f"Recent Candidates: {json.dumps(data.get('recent_candidates', []), indent=2)}")
        print(f"Timestamp: {data.get('timestamp')}")

# ============== INTEGRATION WITH BOJEMOI LAB ==============

async def example_5_integration_with_telegram():
    """
    Example 5: Résultat de découverte + Alerte Telegram
    """
    print("\n[Example 5] Discovery with Telegram notification")
    print("-" * 60)
    
    # Ce payload déclenche une découverte
    # qui notifiera Telegram automatiquement
    payload = {
        "force_refresh": True,
        "test_connectivity": True,
        "notify_telegram": True  # ← Active la notification
    }
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_BASE}/discover",
            json=payload
        )
        
        print("✓ Discovery job queued")
        print("✓ Telegram notifications will be sent on new discovery")
        print(f"Response: {resp.json()}")

async def example_6_integration_with_postgresql():
    """
    Example 6: Vérifier les données dans PostgreSQL
    """
    print("\n[Example 6] PostgreSQL storage verification")
    print("-" * 60)
    
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="bojemoi_cti",
            user="cti_user",
            password="changeme"
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Récents découvertes
            cur.execute("""
                SELECT address, source, confidence, last_verified
                FROM onion_discoveries
                WHERE is_active = TRUE
                ORDER BY last_verified DESC NULLS LAST
                LIMIT 5
            """)
            
            print("Recent Discoveries:")
            for row in cur.fetchall():
                print(f"  {row['address']:60} | {row['source']:20} | {row['confidence']*100:5.0f}% | {row['last_verified']}")
            
            # Audit log
            cur.execute("""
                SELECT timestamp, onion, source, status
                FROM discovery_audit_log
                ORDER BY timestamp DESC
                LIMIT 5
            """)
            
            print("\nAudit Log:")
            for row in cur.fetchall():
                print(f"  {row['timestamp']} | {row['onion']} | {row['source']} | {row['status']}")
        
        conn.close()
    except Exception as e:
        print(f"✗ Database connection failed: {e}")

# ============== ADVANCED: CONTINUOUS MONITORING ==============

async def example_7_continuous_monitoring():
    """
    Example 7: Monitoring continu des changements d'adresse
    """
    print("\n[Example 7] Continuous monitoring (polling mode)")
    print("-" * 60)
    print("Running 5 iterations with 60s interval...")
    
    import time
    
    last_onion = None
    
    for i in range(5):
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/onion")
            data = resp.json()
            current = data.get('primary_onion')
            
            timestamp = datetime.now().isoformat()
            
            if current != last_onion:
                print(f"\n[{timestamp}] 🔄 CHANGE DETECTED!")
                print(f"  Old: {last_onion}")
                print(f"  New: {current}")
                last_onion = current
            else:
                print(f"[{timestamp}] No change (current: {current})")
        
        if i < 4:  # Ne pas attendre après la dernière itération
            await asyncio.sleep(60)

# ============== INTEGRATION WITH GITEA WEBHOOK ==============

def example_8_gitea_webhook_payload():
    """
    Example 8: Payload Gitea pour déclencher discovery au push
    """
    print("\n[Example 8] Gitea Webhook Integration")
    print("-" * 60)
    
    # À configurer dans Bojemoi Lab Gitea > cti_config repo > Settings > Webhooks
    webhook_config = {
        "Payload URL": "http://bojemoi-orchestrator:8000/api/cti/breachforum/discover",
        "HTTP Method": "POST",
        "Content Type": "application/json",
        "Secret": "your-webhook-secret",
        "Events": [
            "push"  # Déclencher à chaque push sur cti_config
        ],
        "Active": True
    }
    
    example_payload = {
        "force_refresh": True,
        "test_connectivity": True,
        "notify_telegram": True
    }
    
    print("Gitea Webhook Configuration:")
    print(json.dumps(webhook_config, indent=2))
    print("\nPayload sent on push:")
    print(json.dumps(example_payload, indent=2))

# ============== INTEGRATION WITH MISP/THEHIVE ==============

async def example_9_cti_platform_integration():
    """
    Example 9: Intégration avec MISP/TheHive
    """
    print("\n[Example 9] CTI Platform Integration")
    print("-" * 60)
    
    print("""
Breachforum onion discoveries peuvent être enrichies avec:

1. MISP Integration:
   - POST événement MISP avec IoC (onion address)
   - Tagger: "breach_forum", "threat_actor"
   - Mapping: Malware.Generic → Exploit.Breachforum
   
2. TheHive Integration:
   - Créer Observable (domain) avec onion address
   - Auto-link avec cas de DDoS/Threat Intelligence
   - TLP: Amber (internal)
   
3. AbuseIPDB/VirusTotal:
   - Enricher onion avec reputation scores
   - Alerter si malveillance détectée
   - Corréler avec IPs de proxy Tor
   
Script de mapping MISP:
    from pymisp import PyMISP
    misp = PyMISP(misp_url, misp_key)
    event = misp.get_event(event_id)
    event.add_attribute('url', onion_address, comment='Breachforum discovery')
    misp.update_event(event)
""")

# ============== MAIN TEST RUNNER ==============

async def main():
    """Exécuter tous les exemples"""
    
    print("=" * 60)
    print("Bojemoi Lab - Breachforum Discovery Service - EXAMPLES")
    print("=" * 60)
    
    try:
        # Vérifier la connexion API
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{API_BASE}/status", timeout=5)
            if resp.status_code != 200:
                print("✗ API unreachable (service not running?)")
                return
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("  Make sure the API is running: docker-compose up -d")
        return
    
    # Exemples
    await example_1_get_current_onion()
    await example_2_force_refresh()
    await example_3_trigger_manual_discovery()
    await example_4_check_service_status()
    await example_5_integration_with_telegram()
    await example_6_integration_with_postgresql()
    # await example_7_continuous_monitoring()  # Long-running, décommenter pour test
    example_8_gitea_webhook_payload()
    await example_9_cti_platform_integration()
    
    print("\n" + "=" * 60)
    print("✓ All examples completed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
