#!/usr/bin/env python3
# metrics_exporter.py

import time
import os
import json
import psycopg2
from prometheus_client import start_http_server, Gauge, Counter, Histogram
from datetime import datetime, timedelta
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Métriques Prometheus
rsync_transfer_bytes = Gauge('rsync_transfer_bytes_total', 'Total bytes transferred by rsync', ['job_name', 'source', 'destination'])
rsync_transfer_files = Gauge('rsync_transfer_files_total', 'Total files transferred by rsync', ['job_name', 'source', 'destination'])
rsync_duration_seconds = Histogram('rsync_duration_seconds', 'Duration of rsync operations in seconds', ['job_name', 'source', 'destination'])
rsync_success_total = Counter('rsync_success_total', 'Total successful rsync operations', ['job_name'])
rsync_error_total = Counter('rsync_error_total', 'Total failed rsync operations', ['job_name', 'error_type'])
rsync_last_success = Gauge('rsync_last_success_timestamp', 'Timestamp of last successful rsync', ['job_name'])

class RsyncMetricsExporter:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'postgresql'),
            'database': os.getenv('POSTGRES_DB', 'rsync_monitoring'),
            'user': os.getenv('POSTGRES_USER', 'rsync_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'rsync_password')
        }
        
    def get_db_connection(self):
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"Erreur de connexion à la base de données: {e}")
            return None
    
    def update_metrics_from_db(self):
        """Met à jour les métriques Prometheus depuis la base de données"""
        conn = self.get_db_connection()
        if not conn:
            return
            
        try:
            cursor = conn.cursor()
            
            # Métriques des dernières 24h
            query = """
            SELECT 
                job_name,
                source_path,
                destination_path,
                bytes_transferred,
                files_transferred,
                duration_seconds,
                status,
                error_message,
                created_at
            FROM rsync_jobs 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            for row in results:
                job_name, source, dest, bytes_tx, files_tx, duration, status, error_msg, created_at = row
                
                if status == 'success':
                    rsync_transfer_bytes.labels(job_name=job_name, source=source, destination=dest).set(bytes_tx or 0)
                    rsync_transfer_files.labels(job_name=job_name, source=source, destination=dest).set(files_tx or 0)
                    rsync_duration_seconds.labels(job_name=job_name, source=source, destination=dest).observe(duration or 0)
                    rsync_success_total.labels(job_name=job_name).inc()
                    rsync_last_success.labels(job_name=job_name).set(created_at.timestamp())
                else:
                    error_type = 'unknown'
                    if error_msg:
                        if 'permission' in error_msg.lower():
                            error_type = 'permission'
                        elif 'network' in error_msg.lower() or 'connection' in error_msg.lower():
                            error_type = 'network'
                        elif 'space' in error_msg.lower():
                            error_type = 'disk_space'
                    
                    rsync_error_total.labels(job_name=job_name, error_type=error_type).inc()
            
            cursor.close()
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métriques: {e}")
        finally:
            conn.close()
    
    def read_log_metrics(self):
        """Lit les métriques depuis les fichiers de log"""
        log_dir = "/rsync/logs"
        if not os.path.exists(log_dir):
            return
            
        for log_file in os.listdir(log_dir):
            if log_file.endswith('.json'):
                try:
                    with open(os.path.join(log_dir, log_file), 'r') as f:
                        data = json.load(f)
                        
                    job_name = data.get('job_name', 'unknown')
                    if data.get('status') == 'success':
                        rsync_transfer_bytes.labels(
                            job_name=job_name,
                            source=data.get('source', ''),
                            destination=data.get('destination', '')
                        ).set(data.get('bytes_transferred', 0))
                        
                        rsync_transfer_files.labels(
                            job_name=job_name,
                            source=data.get('source', ''),
                            destination=data.get('destination', '')
                        ).set(data.get('files_transferred', 0))
                        
                except Exception as e:
                    logger.warning(f"Erreur lors de la lecture du fichier {log_file}: {e}")
    
    def run(self):
        """Démarre l'exporteur de métriques"""
        logger.info("Démarrage de l'exporteur de métriques rsync sur le port 8080")
        start_http_server(8080)
        
        while True:
            try:
                self.update_metrics_from_db()
                self.read_log_metrics()
                time.sleep(30)  # Mise à jour toutes les 30 secondes
            except KeyboardInterrupt:
                logger.info("Arrêt de l'exporteur de métriques")
                break
            except Exception as e:
                logger.error(f"Erreur dans la boucle principale: {e}")
                time.sleep(10)

if __name__ == '__main__':
    exporter = RsyncMetricsExporter()
    exporter.run()	
