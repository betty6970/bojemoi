#!/usr/bin/env python3
"""
Service Daemon pour la Blockchain PostgreSQL
---
Ce script exécute le serveur blockchain en arrière-plan comme un service.
Il gère le redémarrage automatique en cas d'erreur.
"""

import os
import sys
import time
import signal
import logging
import argparse
import subprocess
import json
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='blockchain_service.log'
)
logger = logging.getLogger('blockchain_service')

class BlockchainService:
    def __init__(self, config_file=None, debug=False):
        """
        Initialise le service blockchain.
        
        Args:
            config_file (str, optional): Chemin vers le fichier de configuration
            debug (bool): Mode de débogage
        """
        self.process = None
        self.running = False
        self.debug = debug
        
        # Chargement de la configuration
        self.config = self._load_config(config_file)
        
        # Configuration des gestionnaires de signaux
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _load_config(self, config_file):
        """
        Charge la configuration depuis un fichier JSON.
    
        Args:
            config_file (str): Chemin vers le fichier de configuration
        
        Returns:
            dict: Configuration chargée
        """
        default_config = {
           "host": "0.0.0.0",
           "port": 5000,
           "msf_db_config": {
                "host": "localhost",
                "port": 5432,
                "database": "msf",
                "user": "bojemoi",
                "password": "xxxxx"
            },
            "karacho_db_config": {
                "host": "localhost",
                "port": 5432,
                "database": "karacho",
                "user": "bojemoi",
                "password": "xxxxx"
            },
            "log_level": "INFO",
            "restart_delay": 5
        }
        if not config_file:
            logger.info("Aucun fichier de configuration spécifié, utilisation des valeurs par défaut")
            return default_config
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                logger.info(f"Configuration chargée depuis {config_file}")
                
                # Fusion avec la configuration par défaut
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                    elif isinstance(value, dict) and key in config:
                        for subkey, subvalue in value.items():
                            if subkey not in config[key]:
                                config[key][subkey] = subvalue
                
                return config
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}")
            logger.info("Utilisation des valeurs par défaut")
            return default_config

    def start(self):
        """Démarre le service blockchain"""
        logger.info("Démarrage du service blockchain...")
        self.running = True
    
        while self.running:
            try:
                # Construction de la commande avec les paramètres pour les deux bases de données
                cmd = [
                   sys.executable,
                   "blockchain_postgres_api.py",
                   "--host", self.config["host"],
                   "--port", str(self.config["port"]),
                   "--msf-host", self.config["msf_db_config"]["host"],
                   "--msf-port", str(self.config["msf_db_config"]["port"]),
                   "--msf-dbname", self.config["msf_db_config"]["database"],
                   "--msf-user", self.config["msf_db_config"]["user"],
                   "--msf-password", self.config["msf_db_config"]["password"],
                   "--karacho-host", self.config["karacho_db_config"]["host"],
                   "--karacho-port", str(self.config["karacho_db_config"]["port"]),
                   "--karacho-dbname", self.config["karacho_db_config"]["database"],
                   "--karacho-user", self.config["karacho_db_config"]["user"],
                   "--karacho-password", self.config["karacho_db_config"]["password"],
                   "--log-level", self.config["log_level"]
               ]
                
                if self.debug:
                    cmd.append("--debug")
                
                # Démarrage du processus
                logger.info(f"Exécution de la commande: {' '.join(cmd)}")
                
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE if not self.debug else None,
                    stderr=subprocess.PIPE if not self.debug else None,
                    universal_newlines=True
                )
                
                logger.info(f"Service blockchain démarré avec PID {self.process.pid}")
                
                # Attente de la fin du processus
                self.process.wait()
                
                # Vérification si l'arrêt était volontaire
                if not self.running:
                    logger.info("Arrêt volontaire du service")
                    break
                
                # Redémarrage en cas d'erreur
                exit_code = self.process.returncode
                logger.error(f"Le service s'est arrêté avec le code de sortie {exit_code}")
                
                if self.process.stderr:
                    error_output = self.process.stderr.read()
                    logger.error(f"Erreur: {error_output}")
                
                logger.info(f"Redémarrage dans {self.config['restart_delay']} secondes...")
                time.sleep(self.config['restart_delay'])
                
            except Exception as e:
                logger.error(f"Erreur lors de l'exécution du service: {e}")
                logger.info(f"Redémarrage dans {self.config['restart_delay']} secondes...")
                time.sleep(self.config['restart_delay'])

            
    def _handle_signal(self, signum, frame):
        """Gestionnaire de signaux pour l'arrêt propre du service"""
        logger.info(f"Signal reçu: {signum}")
        self.stop()
    
    
    def stop(self):
        """Arrête le service blockchain"""
        logger.info("Arrêt du service blockchain...")
        self.running = False
        
        if self.process and self.process.poll() is None:
            logger.info(f"Arrêt du processus {self.process.pid}")
            self.process.terminate()
            
            # Attente de la fin du processus (timeout de 5 secondes)
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Le processus ne répond pas, forçage de l'arrêt")
                self.process.kill()
        
        logger.info("Service blockchain arrêté")

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Service Daemon pour la Blockchain PostgreSQL")
    
    parser.add_argument("--config", help="Chemin vers le fichier de configuration")
    parser.add_argument("--debug", action="store_true", help="Mode de débogage")
    
    # Actions (start, stop, restart, status)
    parser.add_argument("action", choices=["start", "stop", "restart", "status"], help="Action à effectuer")
    
    args = parser.parse_args()
    
    # Vérification du PID file
    pid_file = "blockchain_service.pid"
    
    if args.action == "start":
        # Vérification si le service est déjà en cours d'exécution
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            try:
                # Vérification si le processus existe
                os.kill(pid, 0)
                logger.error(f"Le service est déjà en cours d'exécution (PID {pid})")
                print(f"Le service est déjà en cours d'exécution (PID {pid})")
                sys.exit(1)
            except OSError:
                # Le processus n'existe pas, on peut supprimer le fichier PID
                logger.warning(f"Fichier PID obsolète trouvé (PID {pid})")
                os.remove(pid_file)
        
        # Démarrage du service
        service = BlockchainService(args.config, args.debug)
        
        # Écriture du PID dans le fichier
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
        print(f"Service blockchain démarré (PID {os.getpid()})")
        service.start()
        
        # Suppression du fichier PID à la fin
        if os.path.exists(pid_file):
            os.remove(pid_file)
    
    elif args.action == "stop":
        # Vérification si le service est en cours d'exécution
        if not os.path.exists(pid_file):
            logger.error("Le service n'est pas en cours d'exécution")
            print("Le service n'est pas en cours d'exécution")
            sys.exit(1)
        
        # Lecture du PID
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        try:
            # Envoi du signal SIGTERM au processus
            os.kill(pid, signal.SIGTERM)
            print(f"Signal d'arrêt envoyé au service (PID {pid})")
            
            # Attente que le processus se termine
            max_wait = 10
            while max_wait > 0:
                try:
                    os.kill(pid, 0)
                    time.sleep(1)
                    max_wait -= 1
                except OSError:
                    break
            
            if max_wait == 0:
                logger.warning(f"Le service ne répond pas, forçage de l'arrêt (PID {pid})")
                print(f"Le service ne répond pas, forçage de l'arrêt (PID {pid})")
                os.kill(pid, signal.SIGKILL)
            
            # Suppression du fichier PID
            if os.path.exists(pid_file):
                os.remove(pid_file)
            
            print("Service blockchain arrêté")
            
        except OSError:
            logger.error(f"Impossible d'arrêter le service (PID {pid})")
            print(f"Impossible d'arrêter le service (PID {pid})")
            
            # Suppression du fichier PID obsolète
            if os.path.exists(pid_file):
                os.remove(pid_file)
    
    elif args.action == "restart":
        # Arrêt du service
        os.system(f"{sys.executable} {sys.argv[0]} stop")
        time.sleep(2)
        
        # Démarrage du service
        os.system(f"{sys.executable} {sys.argv[0]} start" + (" --debug" if args.debug else "") + (f" --config {args.config}" if args.config else ""))
    
    elif args.action == "status":
        # Vérification si le service est en cours d'exécution
        if not os.path.exists(pid_file):
            print("Le service n'est pas en cours d'exécution")
            sys.exit(1)
        
        # Lecture du PID
        with open(pid_file, 'r') as f:
            pid = int(f.read().strip())
        
        try:
            # Vérification si le processus existe
            os.kill(pid, 0)
            print(f"Le service est en cours d'exécution (PID {pid})")
        except OSError:
            print("Le service n'est pas en cours d'exécution (PID file obsolète)")
            
            # Suppression du fichier PID obsolète
            if os.path.exists(pid_file):
                os.remove(pid_file)

if __name__ == "__main__":
    main()
