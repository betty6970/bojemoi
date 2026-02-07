#!/usr/bin/env python3
"""
Script de scan ZAP pour les services web
Conçu pour fonctionner dans un container Alpine Linux
"""

import os
import sys
import time
import json
import logging
import psycopg2
import requests
from typing import List, Dict, Optional
from urllib.parse import urlparse

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Gestionnaire de connexion à la base de données PostgreSQL"""
    
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """Établir la connexion à la base de données"""
        try:
            self.connection = psycopg2.connect(
                host=os.getenv('DB_HOST', 'postgres'),
                port=os.getenv('DB_PORT', '5432'),
                database=os.getenv('DB_NAME', 'msg'),
                user=os.getenv('DB_USER', 'postgres'),
                password=os.getenv('DB_PASSWORD', 'password')
            )
            logger.info("Connexion à la base de données établie")
        except Exception as e:
            logger.error(f"Erreur de connexion à la base de données: {e}")
            sys.exit(1)
    
    def _ensure_connection(self):
        """Vérifier et rétablir la connexion si nécessaire"""
        try:
            if self.connection is None or self.connection.closed:
                self.connect()
                return
            # Test the connection
            with self.connection.cursor() as cur:
                cur.execute("SELECT 1")
        except Exception:
            logger.info("Connexion perdue, reconnexion...")
            self.connect()

    def get_all_hosts(self) -> List[Dict]:
        """Récupérer tous les hôtes de la base de données"""
        self._ensure_connection()
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, address, name, state, os_name, os_flavor,
                           workspace_id, purpose, info, last_scanned
                    FROM hosts TABLESAMPLE SYSTEM(0.02)
                    WHERE state = 'alive' OR state IS NULL
                    LIMIT 1000
                """)

                columns = [desc[0] for desc in cursor.description]
                hosts = []
                for row in cursor.fetchall():
                    hosts.append(dict(zip(columns, row)))

                logger.info(f"Récupération de {len(hosts)} hôtes")
                return hosts

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des hôtes: {e}")
            return []
    
    def get_host_services(self, host_id: int) -> List[Dict]:
        """Récupérer tous les services d'un hôte"""
        self._ensure_connection()
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, host_id, port, proto, state, name, info
                    FROM services
                    WHERE host_id = %s AND (state = 'open' OR state IS NULL)
                """, (host_id,))

                columns = [desc[0] for desc in cursor.description]
                services = []
                for row in cursor.fetchall():
                    services.append(dict(zip(columns, row)))

                return services

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des services pour l'hôte {host_id}: {e}")
            return []
    
    def close(self):
        """Fermer la connexion à la base de données"""
        if self.connection:
            self.connection.close()

class ZAPManager:
    """Gestionnaire pour interagir avec ZAP Proxy"""
    
    def __init__(self):
        self.zap_host = os.getenv('ZAP_HOST', 'zaproxy')
        self.zap_port = os.getenv('ZAP_PORT', '8080')
        self.zap_api_key = os.getenv('ZAP_API_KEY', '')
        self.base_url = f"http://{self.zap_host}:{self.zap_port}"
        
    def wait_for_zap(self, timeout: int = 300):
        """Attendre que ZAP soit disponible"""
        logger.info("Attente de la disponibilité de ZAP...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.base_url}/JSON/core/view/version/")
                if response.status_code == 200:
                    logger.info("ZAP est disponible")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(5)
        
        logger.error("Timeout en attendant ZAP")
        return False
    
    def start_spider_scan(self, target_url: str) -> Optional[str]:
        """Démarrer un scan spider"""
        try:
            params = {
                'url': target_url,
                'apikey': self.zap_api_key
            }
            
            response = requests.get(
                f"{self.base_url}/JSON/spider/action/scan/",
                params=params
            )
            
            if response.status_code == 200:
                scan_id = response.json().get('scan')
                logger.info(f"Spider scan démarré pour {target_url}, ID: {scan_id}")
                return scan_id
            else:
                logger.error(f"Erreur lors du démarrage du spider scan: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du spider scan: {e}")
            return None
    
    def wait_for_spider_completion(self, scan_id: str):
        """Attendre la fin du scan spider"""
        logger.info(f"Attente de la fin du spider scan {scan_id}")
        
        while True:
            try:
                params = {
                    'scanId': scan_id,
                    'apikey': self.zap_api_key
                }
                
                response = requests.get(
                    f"{self.base_url}/JSON/spider/view/status/",
                    params=params
                )
                
                if response.status_code == 200:
                    status = int(response.json().get('status', 0))
                    logger.info(f"Spider scan progression: {status}%")
                    
                    if status >= 100:
                        logger.info("Spider scan terminé")
                        break
                
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du statut spider: {e}")
            
            time.sleep(10)
    
    def start_active_scan(self, target_url: str) -> Optional[str]:
        """Démarrer un scan actif"""
        try:
            params = {
                'url': target_url,
                'apikey': self.zap_api_key
            }
            
            response = requests.get(
                f"{self.base_url}/JSON/ascan/action/scan/",
                params=params
            )
            
            if response.status_code == 200:
                scan_id = response.json().get('scan')
                logger.info(f"Scan actif démarré pour {target_url}, ID: {scan_id}")
                return scan_id
            else:
                logger.error(f"Erreur lors du démarrage du scan actif: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du scan actif: {e}")
            return None
    
    def wait_for_active_scan_completion(self, scan_id: str):
        """Attendre la fin du scan actif"""
        logger.info(f"Attente de la fin du scan actif {scan_id}")
        
        while True:
            try:
                params = {
                    'scanId': scan_id,
                    'apikey': self.zap_api_key
                }
                
                response = requests.get(
                    f"{self.base_url}/JSON/ascan/view/status/",
                    params=params
                )
                
                if response.status_code == 200:
                    status = int(response.json().get('status', 0))
                    logger.info(f"Scan actif progression: {status}%")
                    
                    if status >= 100:
                        logger.info("Scan actif terminé")
                        break
                
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du statut du scan actif: {e}")
            
            time.sleep(15)
    
    def get_scan_results(self, target_url: str) -> Dict:
        """Récupérer les résultats du scan"""
        try:
            params = {
                'baseurl': target_url,
                'apikey': self.zap_api_key
            }
            
            response = requests.get(
                f"{self.base_url}/JSON/core/view/alerts/",
                params=params
            )
            
            if response.status_code == 200:
                results = response.json()
                logger.info(f"Résultats récupérés pour {target_url}")
                return results
            else:
                logger.error(f"Erreur lors de la récupération des résultats: {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des résultats: {e}")
            return {}

class WebServiceScanner:
    """Scanner principal pour les services web"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.zap = ZAPManager()
        self.web_ports = [80, 443, 8080, 8443, 8000, 8008, 9000, 3000, 5000]
        self.web_services = ['http', 'https', 'http-proxy', 'http-alt', 'web', 'www']
    
    def is_web_service(self, service: Dict) -> bool:
        """Déterminer si un service est un service web"""
        port = service.get('port', 0)
        name = (service.get('name') or '').lower() 
        info = (service.get('info') or '').lower()
        
        # Vérification par port
        if port in self.web_ports:
            return True
        
        # Vérification par nom de service
        if any(web_service in name for web_service in self.web_services):
            return True
        
        # Vérification dans les informations
        if any(keyword in info for keyword in ['http', 'web', 'apache', 'nginx', 'iis']):
            return True
        
        return False
    
    def build_target_url(self, host_address: str, service: Dict) -> str:
        """Construire l'URL cible pour le scan"""
        port = service.get('port', 80)
        
        # Déterminer le protocole
        if port == 443 or 'https' in service.get('name', '').lower():
            protocol = 'https'
        else:
            protocol = 'http'
        
        # Construire l'URL
        if (protocol == 'http' and port == 80) or (protocol == 'https' and port == 443):
            return f"{protocol}://{host_address}"
        else:
            return f"{protocol}://{host_address}:{port}"
    
    def scan_web_service(self, host: Dict, service: Dict):
        """Scanner un service web spécifique"""
        target_url = self.build_target_url(host['address'], service)
        logger.info(f"Scan du service web: {target_url}")
        
        try:
            # Test de connectivité
            response = requests.get(target_url, timeout=10, verify=False)
            if response.status_code >= 400:
                logger.warning(f"Service non accessible: {target_url} (HTTP {response.status_code})")
                return
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Service non accessible: {target_url} - {e}")
            return
        
        # Démarrer le spider scan
        spider_scan_id = self.zap.start_spider_scan(target_url)
        if spider_scan_id:
            self.zap.wait_for_spider_completion(spider_scan_id)
        
        # Démarrer le scan actif
        active_scan_id = self.zap.start_active_scan(target_url)
        if active_scan_id:
            self.zap.wait_for_active_scan_completion(active_scan_id)
        
        # Récupérer les résultats
        results = self.zap.get_scan_results(target_url)
        
        # Sauvegarder les résultats
        self.save_scan_results(host, service, target_url, results)
    
    def save_scan_results(self, host: Dict, service: Dict, target_url: str, results: Dict):
        """Sauvegarder les résultats du scan"""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"scan_results_{host['id']}_{service['port']}_{timestamp}.json"
        
        result_data = {
            'host': host,
            'service': service,
            'target_url': target_url,
            'scan_timestamp': timestamp,
            'results': results
        }
        
        try:
            with open(f"/results/{filename}", 'w') as f:
                json.dump(result_data, f, indent=2, default=str)
            logger.info(f"Résultats sauvegardés: {filename}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde: {e}")
    
    def run(self):
        """Exécuter le scanner"""
        logger.info("Démarrage du scanner de services web")
        
        # Attendre que ZAP soit disponible
        if not self.zap.wait_for_zap():
            logger.error("ZAP non disponible, arrêt du scanner")
            return
        
        # Créer le répertoire de résultats
        os.makedirs('/results', exist_ok=True)
        
        try:
            # Récupérer tous les hôtes
            hosts = self.db.get_all_hosts()
            
            for host in hosts:
                logger.info(f"Traitement de l'hôte: {host['address']}")
                
                # Récupérer les services de l'hôte
                services = self.db.get_host_services(host['id'])
                
                # Filtrer les services web
                web_services = [s for s in services if self.is_web_service(s)]
                
                if web_services:
                    logger.info(f"Services web trouvés: {len(web_services)}")
                    
                    for service in web_services:
                        self.scan_web_service(host, service)
                else:
                    logger.info("Aucun service web trouvé pour cet hôte")
        
        finally:
            self.db.close()

if __name__ == "__main__":
    scanner = WebServiceScanner()
    scanner.run()


