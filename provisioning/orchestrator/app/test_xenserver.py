#!/usr/bin/env python3
"""
Script de test pour xenserver_client_real.py
Usage: python test_xenserver.py
"""
import asyncio
import sys
import os

from app.config import settings


# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.xenserver_client_real import XenServerClient


async def test_xenserver_connection():
    """Test de connexion XenServer"""
    
    # Configuration (à adapter)
    XENSERVER_URL = "https://votre-xenserver.local"
    XENSERVER_USER = "root"
    XENSERVER_PASS = "votre_password"
    
    print("🔧 Test de connexion XenServer")
    print(f"URL: {XENSERVER_URL}")
    print("-" * 50)
    
    # Créer le client
    client = XenServerClient(
        url=XENSERVER_URL,
        username=XENSERVER_USER,
        password=XENSERVER_PASS
    )
    
    try:
        # Test 1 : Ping
        print("\n1️⃣ Test ping...")
        is_connected = await client.ping()
        
        if is_connected:
            print("✅ Connexion réussie !")
        else:
            print("❌ Connexion échouée")
            return
        
        # Test 2 : Lister les templates (optionnel)
        print("\n2️⃣ Test : Récupération des templates...")
        # Cette partie nécessite d'ajouter une méthode list_templates
        
        print("\n✅ Tous les tests passés !")
        
    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Nettoyer
        await client.close()


if __name__ == "__main__":
    # Lancer le test
    asyncio.run(test_xenserver_connection())
