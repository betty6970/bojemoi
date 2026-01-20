#!/usr/bin/env python3
"""
Script Alpine Linux - OpenVPN + IP2Location + Masscan + Metasploit Integration
Pipeline complet avec connexion VPN sécurisée pour les scans
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
import threading
import signal
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Callable
from pathlib import Path
from contextlib import contextmanager
import xml.etree.ElementTree as ET

# Imports pour les bases de données
import psycopg2
import psycopg2.extras

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/vpn_masscan_msf.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def get_host_ip(host):
    """Récupérer l'adresse IP du serveur"""
    try:
        return socket.gethostbyname(host)
    except socket.gaierror as e:
        logger.error(f"Impossible de résoudre {host}: {e}")
        return None

class OpenVPNManager:
    """Gestionnaire OpenVPN intégré pour Alpine Linux"""
    
    def __init__(self, config_file: str, log_level: str = "INFO"):
        self.config_file = Path(config_file)
        self.process: Optional[subprocess.Popen] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 10
        
        self.logger = logging.getLogger(f"{__name__}.OpenVPN")
        
        # Callbacks
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        self._check_requirements()
    
    def _check_requirements(self):
        """Vérifie les prérequis OpenVPN"""
        try:
            subprocess.run(['which', 'openvpn'], check=True, capture_output=True)
            self.logger.info("OpenVPN disponible")
        except subprocess.CalledProcessError:
            raise RuntimeError("OpenVPN non installé. Installez avec: apk add openvpn")
        
        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration VPN non trouvée: {self.config_file}")
    
    def connect(self, daemon: bool = True, auth_file: Optional[str] = None):
        """Démarre la connexion OpenVPN"""
        if self.is_running:
            self.logger.warning("OpenVPN déjà actif")
            return
        
        try:
            cmd = ['openvpn', '--config', str(self.config_file)]
            
            if daemon:
                cmd.extend(['--daemon', '--log', '/tmp/openvpn.log'])
            
            if auth_file:
                cmd.extend(['--auth-user-pass', auth_file])
            
            cmd.extend([
                '--script-security', '2',
                '--up', '/etc/openvpn/update-resolv-conf',
                '--down', '/etc/openvpn/update-resolv-conf'
            ])
            
            self.logger.info(f"Démarrage OpenVPN: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.is_running = True
            self.reconnect_attempts = 0
            
            if daemon:
                self._start_monitoring()
            
            # Attendre et vérifier le démarrage
            time.sleep(3)
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                raise RuntimeError(f"OpenVPN échec: {stderr}")
            
            self.logger.info("OpenVPN connecté avec succès")
            
            if self.on_connected:
                self.on_connected()
                
        except Exception as e:
            self.logger.error(f"Erreur connexion VPN: {e}")
            self.is_running = False
            if self.on_error:
                self.on_error(e)
            raise
    
    def disconnect(self):
        """Arrête la connexion OpenVPN"""
        if not self.is_running:
            return
        
        try:
            self.is_running = False
            
            if self.process:
                self.logger.info("Arrêt OpenVPN...")
                self.process.terminate()
                
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.logger.warning("Forçage arrêt OpenVPN...")
                    self.process.kill()
                    self.process.wait()
                
                self.process = None
            
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5)
            
            self.logger.info("OpenVPN déconnecté")
            
            if self.on_disconnected:
                self.on_disconnected()
                
        except Exception as e:
            self.logger.error(f"Erreur déconnexion: {e}")
            if self.on_error:
                self.on_error(e)
    
    def _start_monitoring(self):
        """Démarre la surveillance de connexion"""
        self.monitor_thread = threading.Thread(target=self._monitor_connection, daemon=True)
        self.monitor_thread.start()
    
    def _monitor_connection(self):
        """Surveille et reconnecte si nécessaire"""
        while self.is_running:
            try:
                if self.process and self.process.poll() is not None:
                    stdout, stderr = self.process.communicate()
                    self.logger.warning(f"OpenVPN arrêté: {stderr}")
                    
                    if self.is_running and self.reconnect_attempts < self.max_reconnect_attempts:
                        self.logger.info(f"Reconnexion {self.reconnect_attempts + 1}/{self.max_reconnect_attempts}")
                        self.reconnect_attempts += 1
                        time.sleep(self.reconnect_delay)
                        self._reconnect()
                    else:
                        self.logger.error("Maximum de reconnexions atteint")
                        self.is_running = False
                        if self.on_error:
                            self.on_error(RuntimeError("Connexion VPN perdue"))
                
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Erreur monitoring: {e}")
                time.sleep(10)
    
    def _reconnect(self):
        """Tente une reconnexion"""
        try:
            if self.process:
                self.process.terminate()
                self.process.wait()
            
            self.connect(daemon=True)
            
        except Exception as e:
            self.logger.error(f"Erreur reconnexion: {e}")
    
    def get_status(self) -> Dict:
        """Retourne le statut VPN"""
        return {
            'is_running': self.is_running,
            'reconnect_attempts': self.reconnect_attempts,
            'process_id': self.process.pid if self.process else None,
            'public_ip': self._get_public_ip()
        }
    
    def _get_public_ip(self) -> Optional[str]:
        """Récupère l'IP publique actuelle"""
        try:
            result = subprocess.run(['wget', '-qO-', 'https://ipinfo.io/ip'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

class DatabaseConfig:
    """Configuration des bases de données"""
    
    def __init__(self):
        # Configuration PostgreSQL IP2Location
        self.ip2location_config = {
            'host': get_host_ip(os.getenv('IP2LOCATION_DB_HOST', 'postgres')),
            'port': int(os.getenv('IP2LOCATION_DB_PORT', 5432)),
            'database': os.getenv('IP2LOCATION_DB_NAME', 'ip2location_db1'),
            'user': os.getenv('IP2LOCATION_DB_USER', 'postgres'),
            'password': os.getenv('IP2LOCATION_DB_PASSWORD', 'bojemoi')
        }
        
        # Configuration PostgreSQL Metasploit
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
        self.logger = logging.getLogger(f"{__name__}.IP2Location")
    
    @contextmanager
    def get_connection(self):
        """Gestionnaire de contexte pour les connexions DB"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
        except Exception as e:
            self.logger.error(f"Erreur connexion IP2Location: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def get_cidr_by_country(self, country_code: str, limit: int = 1000) -> List[str]:
        """Récupère les blocs CIDR pour un pays"""
        query = """
        SELECT cidr_z 
        FROM ip2location_db1
        WHERE country_code LIKE %s 
        AND ip_from IS NOT NULL 
        AND ip_to IS NOT NULL
        AND nmap = '0'
        LIMIT %s;
        """
        
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                    cur.execute(query, (country_code.upper(), limit))
                    results = cur.fetchall()
                    
                    cidrs = []
                    for row in results:
                        try:
                            network = ipaddress.ip_network(row['cidr_z'], strict=False)
                            cidrs.append(str(network))
                        except ValueError as e:
                            self.logger.warning(f"CIDR invalide: {row['cidr_z']} - {e}")
                            continue
                    
                    self.logger.info(f"Trouvé {len(cidrs)} blocs CIDR pour {country_code}")
                    return cidrs
                    
        except Exception as e:
            self.logger.error(f"Erreur lecture IP2Location: {e}")
            return []
    
    def update_cidr(self, code: str, cidr_list: List[str]) -> int:
        """Met à jour le statut des CIDR scannés"""
        if not cidr_list:
            return 0
        
        self.logger.info(f"Mise à jour de {len(cidr_list)} CIDR avec code {code}")
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    updated_count = 0
                    for cidr in cidr_list:
                        cur.execute("""
                        UPDATE ip2location_db1 
                        SET nmap = %s, date_nmap = NOW() 
                        WHERE cidr_z = %s::cidr
                        """, (code, cidr))
                        updated_count += cur.rowcount
                    
                    conn.commit()
                    self.logger.info(f"Mise à jour réussie: {updated_count} CIDR")
                    return updated_count
                    
        except Exception as e:
            self.logger.error(f"Erreur mise à jour: {e}")
            return 0

class MasscanRunner:
    """Classe pour exécuter Masscan avec VPN"""
    
    def __init__(self):
        self.results_dir = "/tmp/masscan_results"
        os.makedirs(self.results_dir, exist_ok=True)
        self.logger = logging.getLogger(f"{__name__}.Masscan")
    
    def run_masscan(self, 
                   cidrs: List[str],
                   ports: str = "22,80,443,8080,8443,3389,5985,5986",
                   rate: int = 1000,
                   output_format: str = "json") -> str:
        """Exécute Masscan sur les blocs CIDR via VPN"""
        if not cidrs:
            raise ValueError("Aucun CIDR à scanner")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.results_dir, f"masscan_{timestamp}.{output_format}")
        
        # Créer fichier temporaire avec les cibles
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            targets_file = f.name
            for cidr in cidrs:
                f.write(f"{cidr}\n")
        
        try:
            # Commande Masscan optimisée pour VPN
            cmd = [
                "masscan",
                "-iL", targets_file,
                "-p", ports,
                "--rate", str(rate),
                "--output-format", output_format,
                "--output-filename", output_file,
                "--wait", "10",
                "--retries", "3",
                "--randomize-hosts",  # Randomiser pour éviter la détection
                "--source-port", "61000-65535"  # Ports source aléatoires
            ]
            
            self.logger.info(f"Démarrage scan Masscan sur {len(cidrs)} CIDR via VPN")
            self.logger.info(f"Commande: {' '.join(cmd)}")
            
            # Exécuter Masscan
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=7200  # 2 heures max
            )
            
            if result.returncode == 0:
                self.logger.info(f"Scan terminé: {output_file}")
                return output_file
            else:
                self.logger.error(f"Erreur Masscan: {result.stderr}")
                raise Exception(f"Masscan échec: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout scan Masscan")
            raise Exception("Timeout Masscan")
        finally:
            if os.path.exists(targets_file):
                os.unlink(targets_file)
    
    def parse_masscan_results(self, results_file: str) -> List[Dict]:
        """Parse les résultats Masscan"""
        hosts = []
        
        try:
            if not os.path.exists(results_file):
                self.logger.warning(f"Fichier résultats non trouvé: {results_file}")
                return hosts
            
            with open(results_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or not line.startswith('{'):
                        continue
                    
                    try:
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
                        self.logger.warning(f"Ligne JSON invalide: {line[:50]}... - {e}")
                        continue
            
            self.logger.info(f"Parsé {len(hosts)} hosts depuis {results_file}")
            return hosts
            
        except Exception as e:
            self.logger.error(f"Erreur parsing résultats: {e}")
            return hosts

class MetasploitIntegration:
    """Classe pour l'intégration avec Metasploit"""
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.workspace_name = "vpn_masscan_import"
        self.logger = logging.getLogger(f"{__name__}.MSF")
    
    @contextmanager
    def get_connection(self):
        """Gestionnaire de contexte pour MSF DB"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
        except Exception as e:
            self.logger.error(f"Erreur connexion MSF: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()
    
    def create_workspace(self) -> int:
        """Crée ou récupère un workspace Metasploit"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM workspaces WHERE name = %s",
                        (self.workspace_name,)
                    )
                    
                    result = cur.fetchone()
                    if result:
                        workspace_id = result[0]
                        self.logger.info(f"Workspace existant: {self.workspace_name} (ID: {workspace_id})")
                    else:
                        cur.execute(
                            """INSERT INTO workspaces (name, description, created_at, updated_at) 
                               VALUES (%s, %s, NOW(), NOW()) RETURNING id""",
                            (self.workspace_name, "Workspace VPN Masscan auto-import")
                        )
                        workspace_id = cur.fetchone()[0]
                        conn.commit()
                        self.logger.info(f"Nouveau workspace: {self.workspace_name} (ID: {workspace_id})")
                    
                    return workspace_id
                    
        except Exception as e:
            self.logger.error(f"Erreur création workspace: {e}")
            raise
    
    def add_host(self, workspace_id: int, ip: str) -> int:
        """Ajoute un host dans MSF"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM hosts WHERE workspace_id = %s AND address = %s",
                        (workspace_id, ip)
                    )
                    
                    result = cur.fetchone()
                    if result:
                        return result[0]
                    
                    cur.execute(
                        """INSERT INTO hosts (workspace_id, address, name, state, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, NOW(), NOW()) RETURNING id""",
                        (workspace_id, ip, ip, 'alive')
                    )
                    
                    host_id = cur.fetchone()[0]
                    conn.commit()
                    return host_id
                    
        except Exception as e:
            self.logger.error(f"Erreur ajout host {ip}: {e}")
            raise
    
    def add_service(self, host_id: int, port: int, protocol: str = 'tcp') -> int:
        """Ajoute un service dans MSF"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM services WHERE host_id = %s AND port = %s AND proto = %s",
                        (host_id, port, protocol)
                    )
                    
                    result = cur.fetchone()
                    if result:
                        return result[0]
                    
                    service_name = self.get_service_name(port, protocol)
                    
                    cur.execute(
                        """INSERT INTO services (host_id, port, proto, state, name, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s, NOW(), NOW()) RETURNING id""",
                        (host_id, port, protocol, 'open', service_name)
                    )
                    
                    service_id = cur.fetchone()[0]
                    conn.commit()
                    return service_id
                    
        except Exception as e:
            self.logger.error(f"Erreur ajout service {port}/{protocol}: {e}")
            raise
    
    def get_service_name(self, port: int, protocol: str) -> str:
        """Détermine le nom du service"""
        common_ports = {
            22: 'ssh', 23: 'telnet', 25: 'smtp', 53: 'dns',
            80: 'http', 110: 'pop3', 143: 'imap', 443: 'https',
            993: 'imaps', 995: 'pop3s', 3389: 'rdp',
            5985: 'winrm', 5986: 'winrm-ssl',
            8080: 'http-alt', 8443: 'https-alt'
        }
        return common_ports.get(port, 'unknown')
    
    def import_hosts(self, hosts: List[Dict], vpn_info: Dict = None) -> Dict:
        """Importe tous les hosts dans Metasploit avec info VPN"""
        if not hosts:
            self.logger.warning("Aucun host à importer")
            return {'hosts': 0, 'services': 0}
        
        stats = {'hosts': 0, 'services': 0, 'errors': 0}
        
        try:
            workspace_id = self.create_workspace()
            
            # Grouper par IP
            hosts_by_ip = {}
            for host in hosts:
                ip = host['ip']
                if ip not in hosts_by_ip:
                    hosts_by_ip[ip] = []
                hosts_by_ip[ip].append(host)
            
            self.logger.info(f"Import {len(hosts_by_ip)} hosts via VPN ({vpn_info.get('public_ip', 'N/A')})")
            
            # Importer chaque host
            for ip, host_services in hosts_by_ip.items():
                try:
                    host_id = self.add_host(workspace_id, ip)
                    stats['hosts'] += 1
                    
                    for service in host_services:
                        try:
                            self.add_service(
                                host_id,
                                service['port'],
                                service.get('protocol', 'tcp')
                            )
                            stats['services'] += 1
                        except Exception as e:
                            self.logger.error(f"Erreur service {ip}:{service['port']} - {e}")
                            stats['errors'] += 1
                            
                except Exception as e:
                    self.logger.error(f"Erreur host {ip} - {e}")
                    stats['errors'] += 1
            
            self.logger.info(f"Import terminé: {stats}")
            return stats
            
        except Exception as e:
            self.logger.error(f"Erreur import global: {e}")
            raise

class VPNScannerPipeline:
    """Pipeline principal avec VPN: IP2Location -> Masscan -> MSF"""
    
    def __init__(self, vpn_config_file: str):
        self.db_config = DatabaseConfig()
        self.vpn = OpenVPNManager(vpn_config_file)
        self.ip2location = IP2LocationReader(self.db_config.ip2location_config)
        self.masscan = MasscanRunner()
        self.msf = MetasploitIntegration(self.db_config.msf_config)
        self.logger = logging.getLogger(f"{__name__}.Pipeline")
        
        # Callbacks VPN
        self.vpn.on_connected = self._on_vpn_connected
        self.vpn.on_disconnected = self._on_vpn_disconnected
        self.vpn.on_error = self._on_vpn_error
    
    def _on_vpn_connected(self):
        """Callback connexion VPN"""
        status = self.vpn.get_status()
        self.logger.info(f"🔐 VPN connecté - IP publique: {status.get('public_ip', 'N/A')}")
    
    def _on_vpn_disconnected(self):
        """Callback déconnexion VPN"""
        self.logger.warning("🔓 VPN déconnecté")
    
    def _on_vpn_error(self, error):
        """Callback erreur VPN"""
        self.logger.error(f"🚨 Erreur VPN: {error}")
    
    def test_connections(self) -> bool:
        """Teste toutes les connexions"""
        self.logger.info("Test des connexions...")
        
        # Test IP2Location
        try:
            with self.ip2location.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM ip2location_db1 LIMIT 1")
                    count = cur.fetchone()[0]
                    self.logger.info(f"✅ IP2Location DB: OK ({count} enregistrements)")
        except Exception as e:
            self.logger.error(f"❌ IP2Location: {e}")
            return False
        
        # Test MSF
        try:
            with self.msf.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM workspaces")
                    count = cur.fetchone()[0]
                    self.logger.info(f"✅ MSF DB: OK ({count} workspaces)")
        except Exception as e:
            self.logger.error(f"❌ MSF: {e}")
            return False
        
        # Test Masscan
        try:
            result = subprocess.run(['masscan', '--help'], capture_output=True, timeout=10)
            if result.returncode < 2:
                self.logger.info("✅ Masscan: OK")
            else:
                self.logger.error("❌ Masscan non disponible")
                return False
        except Exception as e:
            self.logger.error(f"❌ Masscan: {e}")
            return False
        
        return True
    
    def run_vpn_scan(self, 
                    country_code: str,
                    ports: str = "22,80,443,3389,5985",
                    rate: int = 1000,
                    max_cidrs: int = 10,
                    use_vpn: bool = True) -> Dict:
        """Lance un scan complet avec VPN"""
        self.logger.info(f"🚀 Démarrage scan VPN pour: {country_code}")
        
        vpn_context = None
        try:
            # 1. Connexion VPN si demandée
            if use_vpn:
                self.logger.info("🔐 Connexion VPN...")
                self.vpn.connect(daemon=True)
                time.sleep(5)  # Attendre stabilisation VPN
                vpn_context = self.vpn.get_status()
                
                if not vpn_context['is_running']:
                    raise Exception("Échec connexion VPN")
            
            # 2. Récupération CIDR
            self.logger.info("📊 Récupération blocs CIDR...")
            cidrs = self.ip2location.get_cidr_by_country(country_code)
            
            if not cidrs:
                raise Exception(f"Aucun CIDR trouvé pour {country_code}")
            
            if len(cidrs) > max_cidrs:
                self.logger.warning(f"Limitation à {max_cidrs} CIDR (sur {len(cidrs)} trouvés)")
                cidrs = cidrs[:max_cidrs]
            
            # Marquer comme en cours de scan
            self.ip2location.update_cidr("1", cidrs)
            
            # 3. Scan Masscan via VPN
            self.logger.info(f"🔍 Scan Masscan sur {len(cidrs)} CIDR via VPN...")
            results_file = self.masscan.run_masscan(cidrs, ports, rate)
            
            # Marquer comme scanné
            self.ip2location.update_cidr("2", cidrs)
            
            # 4. Parse résultats
            self.logger.info("📋 Parsing résultats...")
            hosts = self.masscan.parse_masscan_results(results_file)
            
            if not hosts:
                self.logger.warning("Aucun host trouvé")
                return {
                    'country': country_code,
                    'vpn_used': use_vpn,
                    'vpn_ip': vpn_context.get('public_ip') if vpn_context else None,
                    'cidrs_scanned': len(cidrs),
                    'hosts_found': 0,
                    'import_stats': {'hosts': 0, 'services': 0}
                }
            
            # 5. Import dans MSF
            self.logger.info(f"💾 Import {len(hosts)} résultats dans MSF...")
            import_stats = self.msf.import_hosts(hosts, vpn_context)
            
            result = {
                'country': country_code,
                'vpn_used': use_vpn,
                'vpn_ip': vpn_context.get('public_ip') if vpn_context else None,
                'cidrs_scanned': len(cidrs),
                'hosts_found': len(hosts),
                'import_stats': import_stats,
                'results_file': results_file,
                'scan_duration': time.time()
            }
            
            self.logger.info(f"✅ Scan terminé: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Erreur scan {country_code}: {e}")
            raise
        finally:
            # Déconnexion VPN si utilisé
            if use_vpn and self.vpn.is_running:
                self.logger.info("🔓 Déconnexion VPN...")
                self.vpn.disconnect()
    
    def run_continuous_scan(self, 
                          countries: List[str],
                          ports: str = "22,80,443,3389,5985",
                          rate: int = 1000,
                          max_cidrs: int = 10,
                          scan_interval: int = 3600,
                          use_vpn: bool = True):
        """Lance des scans continus avec rotation de pays"""
        self.logger.info(f"🔄 Mode scan continu: {countries}")
        
        country_index = 0
        scan_count = 0
        
        try:
            while True:
                country = countries[country_index % len(countries)]
                scan_count += 1
                
                self.logger.info(f"🎯 Scan #{scan_count} - Pays: {country}")
                
                try:
                    result = self.run_vpn_scan(
                        country_code=country,
                        ports=ports,
                        rate=rate,
                        max_cidrs=max_cidrs,
                        use_vpn=use_vpn
                    )
                    
                    # Afficher résumé
                    self.logger.info("="*60)
                    self.logger.info(f"RÉSUMÉ SCAN #{scan_count}")
                    self.logger.info("="*60)
                    for key, value in result.items():
                        if key != 'results_file':
                            self.logger.info(f"{key.upper()}: {value}")
                    self.logger.info("="*60)
                    
                    # Rotation pays
                    country_index += 1
                    
                    # Attente avant prochain scan
                    if scan_interval > 0:
                        self.logger.info(f"⏳ Attente {scan_interval}s avant prochain scan...")
                        time.sleep(scan_interval)
                
                except Exception as e:
                    self.logger.error(f"❌ Erreur scan {country}: {e}")
                    # Passer au pays suivant en cas d'erreur
                    country_index += 1
                    time.sleep(60)  # Attente courte en cas d'erreur
                    continue
                    
        except KeyboardInterrupt:
            self.logger.info("🛑 Arrêt demandé par l'utilisateur")
        finally:
            if self.vpn.is_running:
                self.vpn.disconnect()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.vpn.is_running:
            self.vpn.disconnect()


def create_auth_file(username: str, password: str, filepath: str = "/tmp/vpn_auth.txt") -> str:
    """Crée un fichier d'authentification VPN"""
    try:
        with open(filepath, 'w') as f:
            f.write(f"{username}\n{password}\n")
        
        os.chmod(filepath, 0o600)
        return filepath
    except Exception as e:
        logger.error(f"Erreur création fichier auth: {e}")
        raise


def setup_signal_handlers(pipeline):
    """Configure les gestionnaires de signaux"""
    def signal_handler(signum, frame):
        logger.info(f"Signal {signum} reçu - Arrêt en cours...")
        if pipeline.vpn.is_running:
            pipeline.vpn.disconnect()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def validate_environment():
    """Valide l'environnement Alpine Linux"""
    logger.info("🔍 Validation environnement Alpine Linux...")
    
    # Vérifier les outils requis
    required_tools = ['openvpn', 'masscan', 'wget', 'ip']
    missing_tools = []
    
    for tool in required_tools:
        try:
            subprocess.run(['which', tool], check=True, capture_output=True)
            logger.info(f"✅ {tool}: OK")
        except subprocess.CalledProcessError:
            missing_tools.append(tool)
            logger.error(f"❌ {tool}: MANQUANT")
    
    if missing_tools:
        logger.error(f"Outils manquants: {missing_tools}")
        logger.info("Installation: apk add " + " ".join(missing_tools))
        return False
    
    # Vérifier les permissions
    if os.geteuid() != 0:
        logger.warning("⚠️  Privilèges root recommandés pour OpenVPN")
    
    # Vérifier le device TUN
    if not os.path.exists('/dev/net/tun'):
        logger.error("❌ Device /dev/net/tun manquant")
        logger.info("Dans Docker: --device /dev/net/tun --privileged")
        return False
    else:
        logger.info("✅ Device TUN: OK")
    
    logger.info("✅ Environnement validé")
    return True


def main():
    """Fonction principale avec gestion VPN intégrée"""
    logger.info("🚀 Démarrage Pipeline VPN + Masscan + MSF")
    
    # Configuration par défaut
    VPN_CONFIG = os.getenv('VPN_CONFIG_FILE', '/app/config/client.ovpn')
    VPN_AUTH_USER = os.getenv('VPN_USERNAME', '')
    VPN_AUTH_PASS = os.getenv('VPN_PASSWORD', '')
    
    COUNTRY_CODE = os.getenv('TARGET_COUNTRY', 'RU')
    COUNTRIES_LIST = os.getenv('TARGET_COUNTRIES', 'RU,CN,KP,IR').split(',')
    PORTS = os.getenv('SCAN_PORTS', '22,80,443,3389,5985,8080')
    RATE = int(os.getenv('SCAN_RATE', '1000'))
    MAX_CIDRS = int(os.getenv('MAX_CIDRS', '10'))
    SCAN_INTERVAL = int(os.getenv('SCAN_INTERVAL', '3600'))
    USE_VPN = os.getenv('USE_VPN', 'true').lower() == 'true'
    CONTINUOUS_MODE = os.getenv('CONTINUOUS_MODE', 'false').lower() == 'true'
    
    try:
        # Validation environnement
        if not validate_environment():
            logger.error("❌ Environnement non valide")
            sys.exit(1)
        
        # Créer fichier auth VPN si nécessaire
        auth_file = None
        if VPN_AUTH_USER and VPN_AUTH_PASS:
            auth_file = create_auth_file(VPN_AUTH_USER, VPN_AUTH_PASS)
            logger.info("🔐 Fichier authentification VPN créé")
        
        # Initialiser le pipeline
        with VPNScannerPipeline(VPN_CONFIG) as pipeline:
            
            # Configuration gestionnaire de signaux
            setup_signal_handlers(pipeline)
            
            # Test connexions
            if not pipeline.test_connections():
                logger.error("❌ Échec tests de connexion")
                sys.exit(1)
            
            logger.info("✅ Tous les tests passés")
            
            # Mode de fonctionnement
            if CONTINUOUS_MODE:
                logger.info(f"🔄 Mode continu activé - Pays: {COUNTRIES_LIST}")
                pipeline.run_continuous_scan(
                    countries=COUNTRIES_LIST,
                    ports=PORTS,
                    rate=RATE,
                    max_cidrs=MAX_CIDRS,
                    scan_interval=SCAN_INTERVAL,
                    use_vpn=USE_VPN
                )
            else:
                logger.info(f"🎯 Mode single scan - Pays: {COUNTRY_CODE}")
                result = pipeline.run_vpn_scan(
                    country_code=COUNTRY_CODE,
                    ports=PORTS,
                    rate=RATE,
                    max_cidrs=MAX_CIDRS,
                    use_vpn=USE_VPN
                )
                
                # Afficher résumé final
                logger.info("="*60)
                logger.info("RÉSUMÉ FINAL")
                logger.info("="*60)
                for key, value in result.items():
                    if key != 'results_file':
                        logger.info(f"{key.upper()}: {value}")
                logger.info("="*60)
            
            logger.info("✅ Pipeline terminé avec succès!")
            
    except KeyboardInterrupt:
        logger.info("🛑 Interruption utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        sys.exit(1)
    finally:
        # Nettoyage fichier auth
        if auth_file and os.path.exists(auth_file):
            os.unlink(auth_file)
            logger.info("🧹 Fichier auth nettoyé")


if __name__ == "__main__":
    main()

