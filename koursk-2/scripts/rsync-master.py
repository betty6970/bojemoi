#!/usr/bin/env python3
"""
Script de monitoring rsync optimisé - Version unique avec scheduling intégré
"""
import time
import json
import subprocess
import os
import re
import schedule
import bojemoi
from datetime import datetime, timezone
from prometheus_client import start_http_server, Gauge, Counter, Histogram

# Métriques Prometheus
rsync_duration = Histogram('rsync_duration_seconds', 'Durée des synchronisations rsync', ['source', 'destination', 'job_name'])
rsync_files_transferred = Gauge('rsync_files_transferred_total', 'Nombre de fichiers transférés', ['source', 'destination', 'job_name'])
rsync_bytes_transferred = Gauge('rsync_bytes_transferred_bytes', 'Octets transférés', ['source', 'destination', 'job_name'])
rsync_success = Gauge('rsync_last_success_timestamp', 'Timestamp du dernier succès', ['source', 'destination', 'job_name'])
rsync_errors = Counter('rsync_errors_total', 'Nombre d\'erreurs rsync', ['source', 'destination', 'job_name', 'error_type'])
rsync_speed = Gauge('rsync_transfer_speed_bps', 'Vitesse de transfert en bytes/sec', ['source', 'destination', 'job_name'])
rsync_job_status = Gauge('rsync_job_running', 'Statut d\'exécution du job (1=en cours, 0=arrêté)', ['job_name'])

class RsyncScheduler:
    def __init__(self):
        self.metrics_file = '/data/rsync_metrics.json'
        self.log_file = '/var/log/rsync/rsync-master.log'
        self.running_jobs = {}  # Tracking des jobs en cours
        self.setup_logging()
        
    def setup_logging(self):
        """Configuration du logging"""
        os.makedirs('/var/log/rsync', exist_ok=True)
        
    def log(self, message, job_name="SYSTEM"):
        """Logging avec timestamp et job"""
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = f"[{timestamp}] [{job_name}] {message}\n"
        print(log_entry.strip())
        
        with open(self.log_file, 'a') as f:
            f.write(log_entry)
    
    def parse_rsync_stats(self, output, source, destination, job_name):
        """Parse la sortie de rsync --stats"""
        try:
            stats = {}
            
            patterns = {
                'files_transferred': r'Number of files transferred: (\d+)',
                'total_size': r'Total file size: ([\d,]+)',
                'bytes_sent': r'Total bytes sent: ([\d,]+)',
                'bytes_received': r'Total bytes received: ([\d,]+)',
                'transfer_speed': r'sent [\d,]+ bytes  received [\d,]+ bytes  ([\d,.]+) bytes/sec'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, output)
                if match:
                    value = match.group(1).replace(',', '')
                    stats[key] = float(value)
            
            # Mise à jour des métriques Prometheus avec job_name
            if 'files_transferred' in stats:
                rsync_files_transferred.labels(source=source, destination=destination, job_name=job_name).set(stats['files_transferred'])
            
            if 'bytes_sent' in stats:
                rsync_bytes_transferred.labels(source=source, destination=destination, job_name=job_name).set(stats['bytes_sent'])
            
            if 'transfer_speed' in stats:
                rsync_speed.labels(source=source, destination=destination, job_name=job_name).set(stats['transfer_speed'])
            
            return stats
            
        except Exception as e:
            self.log(f"Erreur lors du parsing des stats rsync: {e}", job_name)
            rsync_errors.labels(source=source, destination=destination, job_name=job_name, error_type='parsing_error').inc()
            return {}
    
    def execute_rsync_job(self, job,node):
        """Exécute un job rsync spécifique"""
        job_name = job['name']
        source = job['source']
        destination = job['destination']
        options = job.get('options', '-av')
        
        # Vérification si le job est déjà en cours
        if job_name in self.running_jobs:
            self.log(f"Job {job_name} déjà en cours d'exécution, ignoré", job_name)
            return False
        
        # Marquage du job comme en cours
        self.running_jobs[job_name] = True
        rsync_job_status.labels(job_name=job_name).set(1)
        
        try:
            start_time = time.time()
            cmd = f"rsync {options}  --log-file /var/log/rsync.log /opt/bojemoi/ rsync://docker@{node}/{job_name}/"
            
            self.log(f"Début d'exécution: {cmd}", job_name)
            
            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True,
                timeout=job.get('timeout', 3600)  # Timeout configurable par job
            )
            
            duration = time.time() - start_time
            rsync_duration.labels(source=source, destination=destination, job_name=job_name).observe(duration)
            
            if result.returncode == 0:
                # Succès
                rsync_success.labels(source=source, destination=destination, job_name=job_name).set(time.time())
                self.log(f"Job réussi en {duration:.2f}s", job_name)
                
                # Parse des statistiques
                stats = self.parse_rsync_stats(result.stdout, source, destination, job_name)
                self.save_metrics(job_name, source, destination, duration, stats, True)
                return True
                
            else:
                # Erreur
                self.log(f"Erreur (code {result.returncode}): {result.stderr}", job_name)
                rsync_errors.labels(source=source, destination=destination, job_name=job_name, error_type=f'exit_code_{result.returncode}').inc()
                self.save_metrics(job_name, source, destination, duration, {}, False, result.stderr)
                return False
            
        except subprocess.TimeoutExpired:
            self.log(f"Timeout après {time.time() - start_time:.2f}s", job_name)
            rsync_errors.labels(source=source, destination=destination, job_name=job_name, error_type='timeout').inc()
            return False
            
        except Exception as e:
            self.log(f"Exception lors de l'exécution: {e}", job_name)
            rsync_errors.labels(source=source, destination=destination, job_name=job_name, error_type='execution_error').inc()
            return False
            
        finally:
            # Nettoyage du tracking
            if job_name in self.running_jobs:
                del self.running_jobs[job_name]
            rsync_job_status.labels(job_name=job_name).set(0)
    
    def save_metrics(self, job_name, source, destination, duration, stats, success, error_msg=""):
        """Sauvegarde les métriques dans un fichier JSON"""
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r') as f:
                    all_metrics = json.load(f)
            else:
                all_metrics = []
            
            metric_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'job_name': job_name,
                'source': source,
                'destination': destination,
                'duration': duration,
                'success': success,
                'stats': stats,
                'error': error_msg
            }
            
            all_metrics.append(metric_entry)
            
            # Garde seulement les 1000 dernières entrées
            if len(all_metrics) > 1000:
                all_metrics = all_metrics[-1000:]
            
            with open(self.metrics_file, 'w') as f:
                json.dump(all_metrics, f, indent=2)
                
        except Exception as e:
            self.log(f"Erreur sauvegarde métriques: {e}", job_name)
    
    def load_jobs_config(self):
        """Charge la configuration des jobs"""
        config_file = '/config/rsync_jobs.json'
        
        if not os.path.exists(config_file):
            # Configuration par défaut
            default_config = [
                {
                    "name": "Sync_bojemoi",
                    "source": "/opt/bojemoi/",
                    "destination": "/opt/bojemoi/",
                    "options": "-av --delete --stats",
                    "schedule": "every_10_minutes",
                    "time": "02:00",
                    "timeout": 3600,
                    "enabled": True,
                    "description": "Synchronisation des données"
                }
            ]
            
            os.makedirs('/config', exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            
            return default_config
        
        with open(config_file, 'r') as f:
            return json.load(f)
    
    def setup_schedules(self, node):
        """Configure les planifications avec le module schedule"""
        jobs = self.load_jobs_config()
        
        # Nettoyage des anciennes planifications
        schedule.clear()
        
        for job in jobs:
            if not job.get('enabled', True):
                self.log(f"Job {job['name']} désactivé, ignoré")
                continue
                
            job_schedule = job.get('schedule', 'daily')
            job_time = job.get('time', '02:00')
            
            try:
                if job_schedule == 'daily':
                    schedule.every().day.at(job_time).do(self.execute_rsync_job, job, node)
                elif job_schedule == 'hourly':
                    schedule.every().hour.do(self.execute_rsync_job, job, node)
                elif job_schedule == 'weekly':
                    day = job.get('day', 'monday')
                    getattr(schedule.every(), day.lower()).at(job_time).do(self.execute_rsync_job, job, node)
                elif job_schedule.startswith('every_'):
                    # Format: every_30_minutes, every_2_hours
                    parts = job_schedule.split('_')
                    if len(parts) == 3:
                        interval = int(parts[1])
                        unit = parts[2]
                        if unit == 'minutes':
                            schedule.every(interval).minutes.do(self.execute_rsync_job, job,node)
                        elif unit == 'hours':
                            schedule.every(interval).hours.do(self.execute_rsync_job, job,node)
                
                self.log(f"Planification configurée pour {job['name']}:  {node}à {job_time}")
                
            except Exception as e:
                self.log(f"Erreur configuration planification pour {job['name']}: {e}")

    def get_rsync_slave_list(self):
        """Découvre les slaves via le label rsync.slave=true sur les nodes"""
        import docker
        client = docker.DockerClient(base_url='unix:///var/run/docker.sock')

        slave_ips = []
        slave_node_ids = []

        try:
            # Trouver les nodes avec label rsync.slave=true
            for node in client.nodes.list():
                labels = node.attrs.get('Spec', {}).get('Labels', {})
                if labels.get('rsync.slave') == 'true':
                    hostname = node.attrs.get('Description', {}).get('Hostname', '')
                    self.log(f"Node rsync slave: {hostname}")
                    slave_node_ids.append(node.id)

            if not slave_node_ids:
                self.log("Aucun node avec label rsync.slave=true")
                return []

            # Trouver les tasks sur ces nodes dans rsync_network
            for task in bojemoi.get_all_swarm_tasks():
                if task.get('NodeID') in slave_node_ids and task.get('Status', {}).get('State') == 'running':
                    for net in task.get('NetworksAttachments', []):
                        if net.get('Network', {}).get('Spec', {}).get('Name') == 'rsync_network':
                            for addr in net.get('Addresses', []):
                                ip = addr.split('/')[0]
                                if ip not in slave_ips:
                                    slave_ips.append(ip)
                                    self.log(f"Slave IP: {ip}")

            return slave_ips

        except Exception as e:
            self.log(f"Erreur découverte slaves: {e}")
            return []


    def _extract_ip_addresses(self, task):
        """Extrait toutes les adresses IP d'une task"""
        ip_addresses = []
        
        for network_attachment in task.get('NetworksAttachments', []):
            addresses = network_attachment.get('Addresses', [])
            for address in addresses:
                # Enlever le CIDR (/24) pour garder seulement l'IP
                ip = address.split('/')[0]
                ip_addresses.append(ip)
    
        return ip_addresses


    
    def run_manual_job(self, job_name):
        """Exécute manuellement un job par son nom"""
        jobs = self.load_jobs_config()
        
        for job in jobs:
            if job['name'] == job_name:
                self.log(f"Exécution manuelle du job: {job_name}")
                return self.execute_rsync_job(job)
        
        self.log(f"Job {job_name} non trouvé")
        return False
    
    def get_status(self):
        """Retourne le statut de tous les jobs"""
        jobs = self.load_jobs_config()
        status = {
            'running_jobs': list(self.running_jobs.keys()),
            'scheduled_jobs': [],
            'next_runs': []
        }
        
        for job in jobs:
            status['scheduled_jobs'].append({
                'name': job['name'],
                'enabled': job.get('enabled', True),
                'schedule': job.get('schedule', 'daily'),
                'time': job.get('time', '02:00')
            })
        
        # Prochaines exécutions planifiées
        for job in schedule.jobs:
            status['next_runs'].append({
                'job': str(job.job),
                'next_run': job.next_run.isoformat() if job.next_run else None
            })
        
        return status

def main():
    scheduler = RsyncScheduler()
    # Démarrage du serveur de métriques Prometheus
    start_http_server(8080)
    scheduler.log("Serveur de métriques Prometheus démarré sur le port 8080")
    
    # Configuration des planifications
    nodes = scheduler.get_rsync_slave_list()
    for node in nodes:
         scheduler.setup_schedules(node)
    scheduler.log("Planifications configurées")
    
    # Boucle principale
    scheduler.log("Démarrage du scheduler rsync")
    
    while True:
        try:
            # Exécution des tâches planifiées
            schedule.run_pending()
            
            # Rechargement de la configuration toutes les 10 minutes
            if int(time.time()) % 600 < 31:
                scheduler.log("Rechargement de la configuration")
                nodes = scheduler.get_rsync_slave_list()
                for node in nodes:
                    scheduler.setup_schedules(node)
                scheduler.log("Rechargement des nodes rsync-slave")
            time.sleep(30) 
        except KeyboardInterrupt:
            scheduler.log("Arrêt du scheduler")
            break
        except Exception as e:
            scheduler.log(f"Erreur dans la boucle principale: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()

