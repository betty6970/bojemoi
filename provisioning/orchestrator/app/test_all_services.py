#!/usr/bin/env python3
"""
Script de test complet pour Bojemoi Orchestrator
Usage: python test_all_services.py

Ce script teste tous les services indépendamment de l'application FastAPI
"""
import asyncio
import sys
from pathlib import Path
import os

from app.config import settings

# Ajouter le répertoire parent au path Python
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Couleurs pour le terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Affiche un en-tête"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")


def print_section(text):
    """Affiche une section"""
    print(f"\n{Colors.BOLD}{text}{Colors.END}")
    print(f"{'-' * 60}")


def print_success(text):
    """Affiche un succès"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    """Affiche une erreur"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    """Affiche un avertissement"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


async def test_xenserver():
    """Test de connexion XenServer"""
    print_section("🔧 Test XenServer")
    
    # Configuration - À ADAPTER
    XENSERVER_URL = os.getenv('XENSERVER_URL', 'https://xenserver.local')
    XENSERVER_USER = os.getenv('XENSERVER_USER', 'root')
    XENSERVER_PASS = os.getenv('XENSERVER_PASS', 'password')
    
    print(f"URL: {XENSERVER_URL}")
    print(f"User: {XENSERVER_USER}")
    
    try:
        # Importer le module
        from app.services.xenserver_client_real import XenServerClient
        
        # Créer le client
        client = XenServerClient(
            url=XENSERVER_URL,
            username=XENSERVER_USER,
            password=XENSERVER_PASS
        )
        
        # Test de connexion
        print("Tentative de connexion...")
        result = await client.ping()
        
        if result:
            print_success("XenServer connecté et fonctionnel")
            return True
        else:
            print_error("XenServer ne répond pas")
            return False
            
    except ImportError as e:
        print_error(f"Impossible d'importer xenserver_client_real: {e}")
        print_warning("Assurez-vous que XenAPI est installé: pip install XenAPI")
        return False
    except Exception as e:
        print_error(f"Erreur lors du test XenServer: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            await client.close()
        except:
            pass


async def test_gitea():
    """Test de connexion Gitea"""
    print_section("📚 Test Gitea")
    
    # Configuration - À ADAPTER
    GITEA_URL = os.getenv('GITEA_URL', 'https://gitea.bojemoi.me')
    GITEA_TOKEN = os.getenv('GITEA_TOKEN', 'votre_token_ici')
    GITEA_REPO = os.getenv('GITEA_REPO', 'bojemoi-configs')
    
    print(f"URL: {GITEA_URL}")
    print(f"Repo: {GITEA_REPO}")
    
    try:
        from app.services.gitea_client import GiteaClient
        
        client = GiteaClient(
            base_url=GITEA_URL,
            token=GITEA_TOKEN,
            repo=GITEA_REPO
        )
        
        print("Tentative de connexion...")
        result = await client.ping()
        
        if result:
            print_success("Gitea connecté et fonctionnel")
            return True
        else:
            print_error("Gitea ne répond pas")
            return False
            
    except Exception as e:
        print_error(f"Erreur lors du test Gitea: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_docker():
    """Test de connexion Docker Swarm"""
    print_section("🐋 Test Docker Swarm")
    
    DOCKER_URL = os.getenv('DOCKER_SWARM_URL', 'unix:///var/run/docker.sock')
    print(f"Socket: {DOCKER_URL}")
    
    try:
        from app.services.docker_client import DockerSwarmClient
        
        client = DockerSwarmClient(base_url=DOCKER_URL)
        
        print("Tentative de connexion...")
        result = await client.ping()
        
        if result:
            print_success("Docker Swarm connecté et actif")
            return True
        else:
            print_error("Docker Swarm non actif ou inaccessible")
            print_warning("Initialisez Swarm avec: docker swarm init")
            return False
            
    except Exception as e:
        print_error(f"Erreur lors du test Docker: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            await client.close()
        except:
            pass


async def test_database():
    """Test de connexion PostgreSQL"""
    print_section("💾 Test PostgreSQL")
    
    DATABASE_URL = os.getenv(
        'DATABASE_URL',
        'postgresql://bojemoi:password@localhost:5432/bojemoi'
    )
    
    # Masquer le mot de passe dans l'affichage
    safe_url = DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL
    print(f"Database: {safe_url}")
    
    try:
        from app.services.database import Database
        
        db = Database(DATABASE_URL)
        
        print("Tentative de connexion...")
        await db.init_db()
        
        result = await db.ping()
        
        if result:
            print_success("PostgreSQL connecté et fonctionnel")
            return True
        else:
            print_error("PostgreSQL ne répond pas")
            return False
            
    except Exception as e:
        print_error(f"Erreur lors du test PostgreSQL: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            await db.close()
        except:
            pass


async def main():
    """Fonction principale - test de tous les services"""
    
    print_header("🧪 Test de tous les services - Bojemoi Orchestrator")
    
    print(f"\n{Colors.YELLOW}💡 Configuration via variables d'environnement:{Colors.END}")
    print("   XENSERVER_URL, XENSERVER_USER, XENSERVER_PASS")
    print("   GITEA_URL, GITEA_TOKEN, GITEA_REPO")
    print("   DATABASE_URL, DOCKER_SWARM_URL")
    print("\n   Ou éditez ce script pour mettre vos valeurs par défaut")
    
    # Exécuter tous les tests
    results = {}
    
    results['xenserver'] = await test_xenserver()
    results['gitea'] = await test_gitea()
    results['docker'] = await test_docker()
    results['database'] = await test_database()
    
    # Résumé
    print_header("📊 Résumé des tests")
    
    for service, result in results.items():
        status = f"{Colors.GREEN}✅ OK{Colors.END}" if result else f"{Colors.RED}❌ FAIL{Colors.END}"
        service_name = service.capitalize().ljust(15)
        print(f"  {service_name} : {status}")
    
    # Statut global
    all_ok = all(results.values())
    any_ok = any(results.values())
    
    print()
    if all_ok:
        print_success("Tous les services sont opérationnels !")
        return 0
    elif any_ok:
        print_warning("Certains services ne sont pas opérationnels")
        return 1
    else:
        print_error("Aucun service n'est opérationnel")
        return 2


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Test interrompu par l'utilisateur{Colors.END}")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n{Colors.RED}❌ Erreur fatale: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
