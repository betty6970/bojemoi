#!/usr/bin/env python3
"""
Script Alpine Linux - IP2Location + Masscan + Metasploit Integration
Lit des CIDR depuis IP2Location, effectue un scan Masscan, et enregistre dans MSF
"""

import subprocess
import json
import logging
import time
import os
import sys
import ipaddress
import tempfile
import socket
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import xml.etree.ElementTree as ET

# Imports pour les bases de données
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/masscan_msf.log'),
        logging.StreamHandler()
    ]
)
    # R..cup..rer l'adresse IP du serveur PostgreSQL
def get_host_ip( host):
    try:
        return socket.gethostbyname(host)
    except socket.gaierror as e:
       print(f"[ERREUR] Impossible de r..soudre {host} {e}")
       return None

logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Configuration des bases de données"""
    
    def __init__(self):
        # Configuration PostgreSQL IP2Location (container distant)
        self.ip2location_config = {
            'host': get_host_ip ( os.getenv('IP2LOCATION_DB_HOST', 'postgres')),
            'port': int(os.getenv('IP2LOCATION_DB_PORT', 5432)),
            'database': os.getenv('IP2LOCATION_DB_NAME', 'ip2location_db1'),
            'user': os.getenv('IP2LOCATION_DB_USER', 'postgres'),
            'password': os.getenv('IP2LOCATION_DB_PASSWORD', 'bojemoi')
        }
        
        # Configuration PostgreSQL Metasploit (container distant)
        self.msf_config = {
            'host': get_host_ip(os.getenv('MSF_DB_HOST', 'postgres')),
            'port': int(os.getenv('MSF_DB_PORT', 5432)),
            'database': os.getenv('MSF_DB_NAME', 'msf'),
            'user': os.getenv('MSF_DB_USER', 'postgres'),
            'password': os.getenv('MSF_DB_PASSWORD', 'bojemoi')
        }
                                                                                      
class IP2LocationReader:
    """Classe pour lire les données IP2Location"""
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
    
    @contextmanager
    def get_connection(self):
        """Gestionnaire de contexte pour les connexions DB"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
        except Exception as e:
            logger.error(f"Erreur de connexion IP2Location: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def get_cidr_by_country(self, country_code: str) -> List[str]:
        """
        Récupère les blocs CIDR pour un pays donné
        
        Args:
            country_code: Code pays ISO (ex: 'FR', 'US')
            
        Returns:
            Liste des blocs CIDR
        """
        query = """
        SELECT cidr_z 
        FROM ip2location_db1
        WHERE country_code like %s 
        AND nmap = '0'
        ORDER BY nmap
        LIMIT 1000;
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, (country_code.upper(),))
                    results = cur.fetchall()
                    
                    cidrs = []
                    for row in results:
                        try:
                            # Valider le CIDR
                            network = ipaddress.ip_network(row['cidr_z'], strict=False)
                            cidrs.append(str(network))
                        except ValueError as e:
                            logger.warning(f"CIDR invalide ignoré: {row['cidr_z']} - {e}")
                            continue
                    
                    logger.info(f"Trouvé {len(cidrs)} blocs CIDR")
                    return cidrs
                    
        except Exception as e:
            logger.error(f"Erreur lors de la lecture IP2Location: {e}")
            return []
    def update_cidr(self, code, cidr_list):
        """
        Met à jour plusieurs CIDR en une seule transaction
    
        Args:
            cidr_list: Liste des CIDR à mettre à jour
            code: Code nmap à assigner
    
        Returns:
            int: Nombre de lignes mises à jour
        """
        if not cidr_list:
            return 0
        
        logger.info(f"mise à jour {cidr_list} blocs CIDR ")

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    for cidr in cidr_list:
                    # Exemple de requête UPDATE
                        cur.execute("""
                        UPDATE ip2location_db1 
                        SET nmap = %s, date_nmap = now() 
                        WHERE cidr_z = %s::cidr
                        """, (code,cidr))
                        print(f"Traité: {cidr}")
    

                    rows_affected = cur.rowcount
                 
           # Validation de la transaction
                conn.commit()
                
                logger.info(f"Mise à jour réussie: {rows_affected} CIDR mis à jour")
                return rows_affected
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour IP2Location: {e}")
            return 0
                                            
        
 
    

class MasscanRunner:
    """Classe pour exécuter Masscan sur Alpine Linux"""
    
    def __init__(self):
        self.results_dir = "/tmp/masscan_results"
        os.makedirs(self.results_dir, exist_ok=True)
    
    def run_masscan(self, 
                   cidrs: List[str],
                   ports: str = "22,80,443,8080,8443,3389,5985,5986",
                   rate: int = 1000,
                   output_format: str = "json") -> str:
        """
        Exécute Masscan sur les blocs CIDR
        
        Args:
            cidrs: Liste des blocs CIDR à scanner
            ports: Ports à scanner
            rate: Taux de paquets par seconde
            output_format: Format de sortie
            
        Returns:
            Chemin vers le fichier de résultats
        """
        if not cidrs:
            raise ValueError("Aucun CIDR à scanner")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.results_dir, f"masscan_{timestamp}.{output_format}")
        
        # Créer un fichier temporaire avec la liste des cibles
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            targets_file = f.name
            for cidr in cidrs:
                f.write(f"{cidr}\n")
        
        try:
            # Commande Masscan
            cmd = [
                "masscan",
                "-iL", targets_file,  # Lire les cibles depuis le fichier
                "-p", ports,
                "--rate", str(rate),
                "--output-format", output_format,
                "--output-filename", output_file,
                "--wait", "10",  # Attendre 10 secondes après la fin
                "--retries", "3"
            ]
            
            logger.info(f"Démarrage du scan Masscan sur {len(cidrs)} CIDR(s)")
            logger.info(f"Commande: {' '.join(cmd)}")
            
            # Exécuter Masscan
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=17200  # 2 heures max
            )
            
            if result.returncode == 0:
                logger.info(f"Scan terminé avec succès: {output_file}")
                return output_file
            else:
                logger.error(f"Erreur Masscan: {result.stderr}")
                raise Exception(f"Masscan a échoué: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout du scan Masscan")
            raise Exception("Timeout Masscan")
        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(targets_file):
                os.unlink(targets_file)
    
    def parse_masscan_results(self, results_file: str) -> List[Dict]:
        """
        Parse les résultats Masscan
        
        Args:
            results_file: Fichier de résultats Masscan
            
        Returns:
            Liste des hosts trouvés
        """
        hosts = []
        
        try:
            if not os.path.exists(results_file):
                logger.warning(f"Fichier de résultats non trouvé: {results_file}")
                return hosts
            
            with open(results_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Format JSON de Masscan
                        if line.startswith('{'):
                            data = json.loads(line)
                            if 'ip' in data and 'ports' in data:
                                for port_info in data['ports']:
                                    host = {
                                        'ip': data['ip'],
                                        'port': port_info['port'],
                                        'protocol': port_info.get('proto', 'tcp'),
                                        'status': port_info.get('status', 'open'),
                                        'timestamp': data.get('timestamp', int(time.time()))
                                    }
                                    hosts.append(host)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Ligne JSON invalide ignorée: {line[:100]}... - {e}")
                        continue
            
            logger.info(f"Parsé {len(hosts)} hosts depuis {results_file}")
            return hosts
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing des résultats: {e}")
            return hosts

class MetasploitIntegration:
    """Classe pour l'intégration avec Metasploit"""
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.workspace_name = "masscan_import"
    
    @contextmanager
    def get_connection(self):
        """Gestionnaire de contexte pour les connexions MSF DB"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
        except Exception as e:
            logger.error(f"Erreur de connexion MSF: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def create_workspace(self) -> int:
        """
        Crée ou récupère un workspace Metasploit
        
        Returns:
            ID du workspace
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Vérifier si le workspace existe
                    cur.execute(
                        "SELECT id FROM workspaces WHERE name = %s",
                        (self.workspace_name,)
                    )
                    
                    result = cur.fetchone()
                    if result:
                        workspace_id = result[0]
                        logger.info(f"Workspace existant utilisé: {self.workspace_name} (ID: {workspace_id})")
                    else:
                        # Créer le workspace
                        cur.execute(
                            """INSERT INTO workspaces (name, description, created_at, updated_at) 
                               VALUES (%s, %s, NOW(), NOW()) RETURNING id""",
                            (self.workspace_name, "Workspace automatique pour imports Masscan")
                        )
                        workspace_id = cur.fetchone()[0]
                        conn.commit()
                        logger.info(f"Nouveau workspace créé: {self.workspace_name} (ID: {workspace_id})")
                    
                    return workspace_id
                    
        except Exception as e:
            logger.error(f"Erreur lors de la création du workspace: {e}")
            raise
    
    def add_host(self, workspace_id: int, ip: str) -> int:
        """
        Ajoute un host dans la base MSF
        
        Args:
            workspace_id: ID du workspace
            ip: Adresse IP
            
        Returns:
            ID de l'host
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Vérifier si l'host existe déjà
                    cur.execute(
                        "SELECT id FROM hosts WHERE workspace_id = %s AND address = %s",
                        (workspace_id, ip)
                    )
                    
                    result = cur.fetchone()
                    if result:
                        return result[0]
                    
                    # Ajouter l'host
                    cur.execute(
                        """INSERT INTO hosts (workspace_id, address, name, state, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, NOW(), NOW()) RETURNING id""",
                        (workspace_id, ip, ip, 'alive')
                    )
                    
                    host_id = cur.fetchone()[0]
                    conn.commit()
                    return host_id
                    
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de l'host {ip}: {e}")
            raise
    
    def add_service(self, host_id: int, port: int, protocol: str = 'tcp') -> int:
        """
        Ajoute un service dans la base MSF
        
        Args:
            host_id: ID de l'host
            port: Numéro de port
            protocol: Protocole (tcp/udp)
            
        Returns:
            ID du service
        """
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    # Vérifier si le service existe déjà
                    cur.execute(
                        "SELECT id FROM services WHERE host_id = %s AND port = %s AND proto = %s",
                        (host_id, port, protocol)
                    )
                    
                    result = cur.fetchone()
                    if result:
                        return result[0]
                    
                    # Déterminer le nom du service
                    service_name = self.get_service_name(port, protocol)
                    
                    # Ajouter le service
                    cur.execute(
                        """INSERT INTO services (host_id, port, proto, state, name, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s, NOW(), NOW()) RETURNING id""",
                        (host_id, port, protocol, 'open', service_name)
                    )
                    
                    service_id = cur.fetchone()[0]
                    conn.commit()
                    return service_id
                    
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du service {port}/{protocol}: {e}")
            raise
    
    def get_service_name(self, port: int, protocol: str) -> str:
        """
        Détermine le nom du service basé sur le port
        
        Args:
            port: Numéro de port
            protocol: Protocole
            
        Returns:
            Nom du service
        """
        common_ports = {
            22: 'ssh',
            23: 'telnet',
            25: 'smtp',
            53: 'dns',
            80: 'http',
            110: 'pop3',
            143: 'imap',
            443: 'https',
            993: 'imaps',
            995: 'pop3s',
            3389: 'rdp',
            5985: 'winrm',
            5986: 'winrm-ssl',
            8080: 'http-alt',
            8443: 'https-alt'
        }
        
        return common_ports.get(port, 'unknown')
    
    def import_hosts(self, hosts: List[Dict]) -> Dict:
        """
        Importe tous les hosts dans Metasploit
        
        Args:
            hosts: Liste des hosts trouvés par Masscan
            
        Returns:
            Statistiques d'import
        """
        if not hosts:
            logger.warning("Aucun host à importer")
            return {'hosts': 0, 'services': 0}
        
        stats = {'hosts': 0, 'services': 0, 'errors': 0}
        
        try:
            # Créer/récupérer le workspace
            workspace_id = self.create_workspace()
            
            # Grouper par IP
            hosts_by_ip = {}
            for host in hosts:
                ip = host['ip']
                if ip not in hosts_by_ip:
                    hosts_by_ip[ip] = []
                hosts_by_ip[ip].append(host)
            
            logger.info(f"Import de {len(hosts_by_ip)} hosts uniques avec {len(hosts)} services")
            
            # Importer chaque host
            for ip, host_services in hosts_by_ip.items():
                try:
                    # Ajouter l'host
                    host_id = self.add_host(workspace_id, ip)
                    stats['hosts'] += 1
                    
                    # Ajouter les services
                    for service in host_services:
                        try:
                            self.add_service(
                                host_id,
                                service['port'],
                                service.get('protocol', 'tcp')
                            )
                            stats['services'] += 1
                        except Exception as e:
                            logger.error(f"Erreur service {ip}:{service['port']} - {e}")
                            stats['errors'] += 1
                            
                except Exception as e:
                    logger.error(f"Erreur host {ip} - {e}")
                    stats['errors'] += 1
            
            logger.info(f"Import terminé: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Erreur lors de l'import global: {e}")
            raise
class MasscanMSFPipeline:
    """Pipeline principal IP2Location -> Masscan -> MSF"""
    
    def __init__(self):
        self.db_config = DatabaseConfig()
        self.ip2location = IP2LocationReader(self.db_config.ip2location_config)
        self.masscan = MasscanRunner()
        self.msf = MetasploitIntegration(self.db_config.msf_config)
    
    def test_connections(self) -> bool:
        """
        Teste les connexions aux bases de données
        
        Returns:
            True si toutes les connexions fonctionnent
        """
        logger.info("Test des connexions aux bases de données...")
        
        # Test IP2Location
        try:
            with self.ip2location.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM ip2location_db1 LIMIT 1")
                    count = cur.fetchone()[0]
                    logger.info(f"IP2Location DB: OK ({count} enregistrements)")
        except Exception as e:
            logger.error(f"Erreur connexion IP2Location: {e}")
            return False
        
        # Test MSF
        try:
            with self.msf.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM workspaces")
                    count = cur.fetchone()[0]
                    logger.info(f"MSF DB: OK ({count} workspaces)")
        except Exception as e:
            logger.error(f"Erreur connexion MSF: {e}")
            return False
        
        # Test Masscan
        try:
            result = subprocess.run(['masscan', '--help'], capture_output=True, timeout=10)
            if result.returncode < 2:
                logger.info("Masscan: OK")
            else:
                logger.error("Masscan non disponible")
                return False
        except Exception as e:
            logger.error(f"Erreur Masscan: {e}")
            return False
        
        return True
    
    def run_country_scan(self, 
                        country_code: str,
                        ports: str = "22,80,443,3389,5985",
                        rate: int = 1000,
                        max_cidrs: int = 10) -> Dict:
        """
        Lance un scan complet pour un pays
        
        Args:
            country_code: Code pays ISO
            ports: Ports à scanner
            rate: Taux de scan
            max_cidrs: Nombre maximum de CIDR à scanner
            
        Returns:
            Résultats du scan
        """
        logger.info(f"Démarrage du scan pour le pays: {country_code}")
        
        try:
            # 1. Récupérer les CIDR
            logger.info("Étape 1: Récupération des blocs CIDR...")
            cidrs = self.ip2location.get_cidr_by_country(country_code)
            
            if not cidrs:
                raise Exception(f"Aucun CIDR trouvé ")
            
            # Limiter le nombre de CIDR pour éviter des scans trop longs
            if len(cidrs) > max_cidrs:
                logger.warning(f"Limitation à {max_cidrs} CIDR (sur {len(cidrs)} trouvés)")
                cidrs = cidrs[:max_cidrs]
            self.ip2location.update_cidr("1",cidrs) 
            # 2. Lancer Masscan
            logger.info(f"Étape 2: Scan Masscan sur {len(cidrs)} CIDR...")
            results_file = self.masscan.run_masscan(cidrs, ports, rate)
            self.ip2location.update_cidr("2",cidrs) 
            
            # 3. Parser les résultats
            logger.info("Étape 3: Parsing des résultats...")
            hosts = self.masscan.parse_masscan_results(results_file)
            
            if not hosts:
                logger.warning("Aucun host trouvé")
                return {
                    'country': country_code,
                    'cidrs_scanned': len(cidrs),
                    'hosts_found': 0,
                    'import_stats': {'hosts': 0, 'services': 0}
                }
            
            # 4. Importer dans MSF
            logger.info(f"Étape 4: Import de {len(hosts)} résultats dans MSF...")
            import_stats = self.msf.import_hosts(hosts)
            
            result = {
                'country': country_code,
                'cidrs_scanned': len(cidrs),
                'hosts_found': len(hosts),
                'import_stats': import_stats,
                'results_file': results_file
            }
            
            logger.info(f"Scan terminé: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Erreur durant le scan {country_code}: {e}")
            raise
    

def main():
    """Fonction principale"""
    print("5665")
    logger.info("Démarrage du pipeline IP2Location -> Masscan -> MSF")
    
    # Configuration par défaut
    COUNTRY_CODE = os.getenv('TARGET_COUNTRY', 'RU')  # France par défaut
    ISP_NAME = os.getenv('TARGET_ISP', '')
    PORTS = os.getenv('SCAN_PORTS', '22,80,443,3389,5985,8080')
    RATE = int(os.getenv('SCAN_RATE', '10000'))
    MAX_CIDRS = int(os.getenv('MAX_CIDRS', '50'))
    
    try:
        # Initialiser le pipeline
        pipeline = MasscanMSFPipeline()
        
        # Tester les connexions
        if not pipeline.test_connections():
            logger.error("Échec des tests de connexion")
            sys.exit(100)
        
        logger.info(f"Mode pays: {COUNTRY_CODE}")
        while True:
            result = pipeline.run_country_scan(
                country_code=COUNTRY_CODE,
                ports=PORTS,
                rate=RATE,
                max_cidrs=MAX_CIDRS
            )
        
            # Afficher le résumé
            logger.info("="*50)
            logger.info("RÉSUMÉ DU SCAN")
            logger.info("="*50)
            for key, value in result.items():
                logger.info(f"{key}: {value}")
        
            logger.info("Pipeline terminé avec succès !!")
    except KeyboardInterrupt:
        print("\nBoucle interrompue par l'operateur")
        raise



if __name__ == "__main__":
    main()
