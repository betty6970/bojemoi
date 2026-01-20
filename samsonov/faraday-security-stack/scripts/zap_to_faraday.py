#!/usr/bin/env python3
"""
Script d'intégration ZAP -> Faraday
Exporte les résultats de ZAP vers Faraday
"""

import requests
import json
import sys
import time
from zapv2 import ZAPv2
import argparse

class ZapFaradayIntegration:
    def __init__(self, faraday_url, faraday_user, faraday_pass, 
                 zap_url, zap_api_key, workspace):
        self.faraday_url = faraday_url
        self.faraday_user = faraday_user
        self.faraday_pass = faraday_pass
        self.zap_url = zap_url
        self.zap_api_key = zap_api_key
        self.workspace = workspace
        self.session = requests.Session()
        self.zap = ZAPv2(apikey=zap_api_key, proxies={'http': zap_url, 'https': zap_url})
        
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
                "description": "ZAP Security Scan Results"
            }
            response = self.session.post(create_url, json=data)
            if response.status_code == 201:
                print(f"[+] Workspace '{self.workspace}' créé")
                return True
        elif response.status_code == 200:
            print(f"[+] Workspace '{self.workspace}' existe déjà")
            return True
        
        return False
    
    def get_zap_alerts(self, target_url=None):
        """Récupérer les alertes ZAP"""
        try:
            if target_url:
                alerts = self.zap.core.alerts(baseurl=target_url)
            else:
                alerts = self.zap.core.alerts()
            print(f"[+] {len(alerts)} alertes récupérées de ZAP")
            return alerts
        except Exception as e:
            print(f"[-] Erreur lors de la récupération des alertes ZAP: {e}")
            return []
    
    def map_zap_severity(self, risk):
        """Mapper la sévérité ZAP vers Faraday"""
        mapping = {
            '3': 'critical',  # High
            '2': 'high',      # Medium
            '1': 'medium',    # Low
            '0': 'informational'  # Informational
        }
        return mapping.get(str(risk), 'unclassified')
    
    def create_faraday_host(self, ip_address):
        """Créer un host dans Faraday"""
        host_url = f"{self.faraday_url}/_api/v3/ws/{self.workspace}/hosts"
        data = {
            "ip": ip_address,
            "description": "Host discovered by ZAP scan",
            "os": "unknown"
        }
        try:
            response = self.session.post(host_url, json=data)
            if response.status_code in [200, 201, 409]:
                host_id = response.json().get('id') if response.status_code in [200, 201] else None
                return host_id
            return None
        except Exception as e:
            print(f"[-] Erreur création host: {e}")
            return None
    
    def create_faraday_vulnerability(self, alert, host_id):
        """Créer une vulnérabilité dans Faraday"""
        vuln_url = f"{self.faraday_url}/_api/v3/ws/{self.workspace}/vulns"
        
        severity = self.map_zap_severity(alert.get('risk', '0'))
        
        data = {
            "name": alert.get('name', 'Unknown Vulnerability'),
            "description": alert.get('description', ''),
            "severity": severity,
            "type": "vulnerability_web",
            "resolution": alert.get('solution', ''),
            "data": alert.get('other', ''),
            "refs": [alert.get('reference', '')],
            "target": alert.get('url', ''),
            "method": alert.get('method', 'GET'),
            "params": alert.get('param', ''),
            "request": alert.get('attack', ''),
            "response": alert.get('evidence', ''),
            "website": alert.get('url', ''),
            "path": alert.get('url', ''),
            "status_code": 0,
            "confirmed": False,
            "parent": host_id,
            "parent_type": "Host"
        }
        
        try:
            response = self.session.post(vuln_url, json=data)
            if response.status_code in [200, 201]:
                print(f"[+] Vulnérabilité créée: {data['name']}")
                return True
            else:
                print(f"[-] Erreur création vuln: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[-] Erreur lors de la création de la vulnérabilité: {e}")
            return False
    
    def import_zap_results(self, target_url=None):
        """Importer les résultats ZAP dans Faraday"""
        if not self.authenticate_faraday():
            return False
        
        if not self.create_workspace():
            return False
        
        alerts = self.get_zap_alerts(target_url)
        
        hosts = {}
        for alert in alerts:
            url = alert.get('url', '')
            # Extraire l'hôte de l'URL
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                host = parsed.hostname or 'unknown'
                
                if host not in hosts:
                    host_id = self.create_faraday_host(host)
                    hosts[host] = host_id
                else:
                    host_id = hosts[host]
                
                if host_id:
                    self.create_faraday_vulnerability(alert, host_id)
            except Exception as e:
                print(f"[-] Erreur traitement alerte: {e}")
                continue
        
        print(f"[+] Import terminé: {len(alerts)} alertes traitées")
        return True

def main():
    parser = argparse.ArgumentParser(description='Intégration ZAP -> Faraday')
    parser.add_argument('--faraday-url', default='http://faraday:5985',
                        help='URL Faraday (default: http://faraday:5985)')
    parser.add_argument('--faraday-user', default='faraday',
                        help='Utilisateur Faraday (default: faraday)')
    parser.add_argument('--faraday-pass', default='changeme',
                        help='Mot de passe Faraday')
    parser.add_argument('--zap-url', default='http://zap:8080',
                        help='URL ZAP (default: http://zap:8080)')
    parser.add_argument('--zap-api-key', default='',
                        help='Clé API ZAP')
    parser.add_argument('--workspace', default='zap-scan',
                        help='Workspace Faraday (default: zap-scan)')
    parser.add_argument('--target-url', default=None,
                        help='URL cible spécifique (optionnel)')
    
    args = parser.parse_args()
    
    integration = ZapFaradayIntegration(
        faraday_url=args.faraday_url,
        faraday_user=args.faraday_user,
        faraday_pass=args.faraday_pass,
        zap_url=args.zap_url,
        zap_api_key=args.zap_api_key,
        workspace=args.workspace
    )
    
    integration.import_zap_results(args.target_url)

if __name__ == "__main__":
    main()
