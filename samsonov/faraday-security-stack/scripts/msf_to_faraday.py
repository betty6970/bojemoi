#!/usr/bin/env python3
"""
Script d'intégration Metasploit -> Faraday
Exporte les résultats de Metasploit vers Faraday
"""

import requests
import json
import xml.etree.ElementTree as ET
import argparse
import sys

class MetasploitFaradayIntegration:
    def __init__(self, faraday_url, faraday_user, faraday_pass, 
                 msf_xml_file, workspace):
        self.faraday_url = faraday_url
        self.faraday_user = faraday_user
        self.faraday_pass = faraday_pass
        self.msf_xml_file = msf_xml_file
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
                "description": "Metasploit Scan Results"
            }
            response = self.session.post(create_url, json=data)
            if response.status_code == 201:
                print(f"[+] Workspace '{self.workspace}' créé")
                return True
        elif response.status_code == 200:
            print(f"[+] Workspace '{self.workspace}' existe déjà")
            return True
        
        return False
    
    def parse_msf_xml(self):
        """Parser le fichier XML Metasploit"""
        try:
            tree = ET.parse(self.msf_xml_file)
            root = tree.getroot()
            return root
        except Exception as e:
            print(f"[-] Erreur lors du parsing XML: {e}")
            return None
    
    def create_host(self, host_data):
        """Créer un host dans Faraday"""
        host_url = f"{self.faraday_url}/_api/v3/ws/{self.workspace}/hosts"
        
        ip = host_data.get('address', 'unknown')
        mac = host_data.get('mac', '')
        os_name = host_data.get('os_name', 'Unknown')
        
        data = {
            "ip": ip,
            "description": f"Host discovered by Metasploit",
            "os": os_name,
            "mac": mac,
            "hostnames": host_data.get('hostnames', [])
        }
        
        try:
            response = self.session.post(host_url, json=data)
            if response.status_code in [200, 201]:
                return response.json().get('id')
            elif response.status_code == 409:
                # Host existe déjà, récupérer son ID
                get_response = self.session.get(f"{host_url}?ip={ip}")
                if get_response.status_code == 200:
                    hosts = get_response.json()
                    if hosts:
                        return hosts[0].get('id')
            return None
        except Exception as e:
            print(f"[-] Erreur création host: {e}")
            return None
    
    def create_service(self, host_id, service_data):
        """Créer un service dans Faraday"""
        service_url = f"{self.faraday_url}/_api/v3/ws/{self.workspace}/services"
        
        data = {
            "name": service_data.get('name', 'unknown'),
            "protocol": service_data.get('protocol', 'tcp'),
            "port": service_data.get('port', 0),
            "status": "open",
            "version": service_data.get('version', ''),
            "description": service_data.get('info', ''),
            "parent": host_id,
            "parent_type": "Host"
        }
        
        try:
            response = self.session.post(service_url, json=data)
            if response.status_code in [200, 201]:
                print(f"[+] Service créé: {data['name']}:{data['port']}")
                return response.json().get('id')
            return None
        except Exception as e:
            print(f"[-] Erreur création service: {e}")
            return None
    
    def create_vulnerability(self, parent_id, parent_type, vuln_data):
        """Créer une vulnérabilité dans Faraday"""
        vuln_url = f"{self.faraday_url}/_api/v3/ws/{self.workspace}/vulns"
        
        severity_map = {
            'critical': 'critical',
            'high': 'high',
            'medium': 'medium',
            'low': 'low',
            'info': 'informational'
        }
        
        data = {
            "name": vuln_data.get('name', 'Unknown Vulnerability'),
            "description": vuln_data.get('description', ''),
            "severity": severity_map.get(vuln_data.get('severity', 'medium').lower(), 'medium'),
            "type": "vulnerability",
            "resolution": vuln_data.get('solution', ''),
            "refs": vuln_data.get('refs', []),
            "confirmed": False,
            "parent": parent_id,
            "parent_type": parent_type
        }
        
        try:
            response = self.session.post(vuln_url, json=data)
            if response.status_code in [200, 201]:
                print(f"[+] Vulnérabilité créée: {data['name']}")
                return True
            return False
        except Exception as e:
            print(f"[-] Erreur création vulnérabilité: {e}")
            return False
    
    def import_msf_results(self):
        """Importer les résultats Metasploit dans Faraday"""
        if not self.authenticate_faraday():
            return False
        
        if not self.create_workspace():
            return False
        
        root = self.parse_msf_xml()
        if root is None:
            return False
        
        # Parser les hosts
        for host_elem in root.findall('.//host'):
            host_data = {
                'address': host_elem.find('address').get('addr') if host_elem.find('address') is not None else 'unknown',
                'mac': host_elem.find('address[@addrtype="mac"]').get('addr', '') if host_elem.find('address[@addrtype="mac"]') is not None else '',
                'os_name': 'Unknown',
                'hostnames': []
            }
            
            # OS detection
            os_elem = host_elem.find('.//os/osmatch')
            if os_elem is not None:
                host_data['os_name'] = os_elem.get('name', 'Unknown')
            
            # Hostnames
            for hostname_elem in host_elem.findall('.//hostname'):
                host_data['hostnames'].append(hostname_elem.get('name', ''))
            
            host_id = self.create_host(host_data)
            
            if host_id:
                # Parser les services
                for port_elem in host_elem.findall('.//port'):
                    service_elem = port_elem.find('service')
                    if service_elem is not None:
                        service_data = {
                            'name': service_elem.get('name', 'unknown'),
                            'protocol': port_elem.get('protocol', 'tcp'),
                            'port': int(port_elem.get('portid', 0)),
                            'version': service_elem.get('version', ''),
                            'info': service_elem.get('product', '')
                        }
                        service_id = self.create_service(host_id, service_data)
                        
                        # Vérifier les vulnérabilités associées
                        for script_elem in port_elem.findall('.//script'):
                            if 'vuln' in script_elem.get('id', '').lower():
                                vuln_data = {
                                    'name': script_elem.get('id', 'Unknown'),
                                    'description': script_elem.get('output', ''),
                                    'severity': 'medium',
                                    'refs': []
                                }
                                if service_id:
                                    self.create_vulnerability(service_id, 'Service', vuln_data)
        
        print("[+] Import Metasploit terminé")
        return True

def main():
    parser = argparse.ArgumentParser(description='Intégration Metasploit -> Faraday')
    parser.add_argument('--faraday-url', default='http://faraday:5985',
                        help='URL Faraday (default: http://faraday:5985)')
    parser.add_argument('--faraday-user', default='faraday',
                        help='Utilisateur Faraday (default: faraday)')
    parser.add_argument('--faraday-pass', default='changeme',
                        help='Mot de passe Faraday')
    parser.add_argument('--msf-xml', required=True,
                        help='Fichier XML Metasploit')
    parser.add_argument('--workspace', default='metasploit-scan',
                        help='Workspace Faraday (default: metasploit-scan)')
    
    args = parser.parse_args()
    
    integration = MetasploitFaradayIntegration(
        faraday_url=args.faraday_url,
        faraday_user=args.faraday_user,
        faraday_pass=args.faraday_pass,
        msf_xml_file=args.msf_xml,
        workspace=args.workspace
    )
    
    integration.import_msf_results()

if __name__ == "__main__":
    main()
