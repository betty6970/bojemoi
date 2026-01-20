#!/usr/bin/env python3
"""
Script d'intégration Masscan -> Faraday
Exporte les résultats de Masscan vers Faraday
"""

import requests
import json
import argparse
import sys

class MasscanFaradayIntegration:
    def __init__(self, faraday_url, faraday_user, faraday_pass, 
                 masscan_json, workspace):
        self.faraday_url = faraday_url
        self.faraday_user = faraday_user
        self.faraday_pass = faraday_pass
        self.masscan_json = masscan_json
        self.workspace = workspace
        self.session = requests.Session()
        
    def authenticate_faraday(self):
        """Authentification à Faraday"""
        login_url = f"{self.faraday_url}/_api/login"
        data = {
            "email": self.faraday_user,
            "password": self.faraday_pass
        }
        try:
            response = self.session.post(login_url, json=data)
            if response.status_code == 200:
                print("[+] Authentification Faraday réussie")
                return True
            else:
                print(f"[-] Erreur d'authentification: {response.status_code}")
                return False
        except Exception as e:
            print(f"[-] Erreur de connexion à Faraday: {e}")
            return False
    
    def create_workspace(self):
        """Créer un workspace si inexistant"""
        ws_url = f"{self.faraday_url}/_api/v3/ws/{self.workspace}"
        response = self.session.get(ws_url)
        
        if response.status_code == 404:
            create_url = f"{self.faraday_url}/_api/v3/ws"
            data = {
                "name": self.workspace,
                "description": "Masscan Results"
            }
            response = self.session.post(create_url, json=data)
            if response.status_code == 201:
                print(f"[+] Workspace '{self.workspace}' créé")
                return True
        elif response.status_code == 200:
            print(f"[+] Workspace '{self.workspace}' existe déjà")
            return True
        
        return False
    
    def parse_masscan_json(self):
        """Parser le fichier JSON Masscan"""
        try:
            with open(self.masscan_json, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"[-] Erreur lors du parsing JSON: {e}")
            return None
    
    def create_host(self, ip_address):
        """Créer un host dans Faraday"""
        host_url = f"{self.faraday_url}/_api/v3/ws/{self.workspace}/hosts"
        
        data = {
            "ip": ip_address,
            "description": "Host discovered by Masscan",
            "os": "unknown"
        }
        
        try:
            response = self.session.post(host_url, json=data)
            if response.status_code in [200, 201]:
                return response.json().get('id')
            elif response.status_code == 409:
                # Host existe déjà, récupérer son ID
                get_response = self.session.get(f"{host_url}?ip={ip_address}")
                if get_response.status_code == 200:
                    hosts = get_response.json()
                    if hosts:
                        return hosts[0].get('id')
            return None
        except Exception as e:
            print(f"[-] Erreur création host: {e}")
            return None
    
    def create_service(self, host_id, port, protocol, status):
        """Créer un service dans Faraday"""
        service_url = f"{self.faraday_url}/_api/v3/ws/{self.workspace}/services"
        
        data = {
            "name": f"port-{port}",
            "protocol": protocol,
            "port": port,
            "status": status,
            "version": "",
            "description": f"Port discovered by Masscan",
            "parent": host_id,
            "parent_type": "Host"
        }
        
        try:
            response = self.session.post(service_url, json=data)
            if response.status_code in [200, 201]:
                print(f"[+] Service créé: {protocol}/{port} sur host {host_id}")
                return response.json().get('id')
            return None
        except Exception as e:
            print(f"[-] Erreur création service: {e}")
            return None
    
    def import_masscan_results(self):
        """Importer les résultats Masscan dans Faraday"""
        if not self.authenticate_faraday():
            return False
        
        if not self.create_workspace():
            return False
        
        data = self.parse_masscan_json()
        if data is None:
            return False
        
        hosts_cache = {}
        
        # Parser les résultats Masscan
        for entry in data:
            if 'ip' in entry and 'ports' in entry:
                ip = entry['ip']
                
                # Créer le host s'il n'existe pas
                if ip not in hosts_cache:
                    host_id = self.create_host(ip)
                    hosts_cache[ip] = host_id
                else:
                    host_id = hosts_cache[ip]
                
                if host_id:
                    # Créer les services pour chaque port
                    for port_info in entry['ports']:
                        port = port_info.get('port', 0)
                        protocol = port_info.get('proto', 'tcp')
                        status = port_info.get('status', 'open')
                        
                        self.create_service(host_id, port, protocol, status)
        
        print(f"[+] Import Masscan terminé: {len(hosts_cache)} hosts traités")
        return True

def main():
    parser = argparse.ArgumentParser(description='Intégration Masscan -> Faraday')
    parser.add_argument('--faraday-url', default='http://faraday:5985',
                        help='URL Faraday (default: http://faraday:5985)')
    parser.add_argument('--faraday-user', default='faraday',
                        help='Utilisateur Faraday (default: faraday)')
    parser.add_argument('--faraday-pass', default='changeme',
                        help='Mot de passe Faraday')
    parser.add_argument('--masscan-json', required=True,
                        help='Fichier JSON Masscan')
    parser.add_argument('--workspace', default='masscan-scan',
                        help='Workspace Faraday (default: masscan-scan)')
    
    args = parser.parse_args()
    
    integration = MasscanFaradayIntegration(
        faraday_url=args.faraday_url,
        faraday_user=args.faraday_user,
        faraday_pass=args.faraday_pass,
        masscan_json=args.masscan_json,
        workspace=args.workspace
    )
    
    integration.import_masscan_results()

if __name__ == "__main__":
    main()
