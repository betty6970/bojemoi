#!/usr/bin/env python3
import os
import json
import requests
from pathlib import Path

FARADAY_URL = os.getenv('FARADAY_URL')
FARADAY_TOKEN = os.getenv('FARADAY_TOKEN')  # À configurer dans GitLab CI/CD variables
WORKSPACE = os.getenv('FARADAY_WORKSPACE', 'production')

class FaradayImporter:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {FARADAY_TOKEN}',
            'Content-Type': 'application/json'
        })
        self.base_url = f'{FARADAY_URL}/_api/v3'
    
    def import_zap_report(self, report_path):
        """Import ZAP JSON report"""
        with open(report_path, 'r') as f:
            zap_data = json.load(f)
        
        vulnerabilities = []
        for site in zap_data.get('site', []):
            for alert in site.get('alerts', []):
                vuln = {
                    'name': alert.get('name'),
                    'description': alert.get('desc'),
                    'severity': self._map_severity(alert.get('riskcode')),
                    'type': 'vulnerability',
                    'target': site.get('@host'),
                    'refs': alert.get('reference', '').split('\n'),
                    'resolution': alert.get('solution'),
                    'data': alert.get('instances', [])
                }
                vulnerabilities.append(vuln)
        
        return self._bulk_create_vulns(vulnerabilities)
    
    def import_masscan_report(self, report_path):
        """Import Masscan JSON report"""
        with open(report_path, 'r') as f:
            masscan_data = json.load(f)
        
        services = []
        for result in masscan_data:
            service = {
                'name': f"Port {result['ports'][0]['port']}",
                'description': f"Open port detected: {result['ports'][0]['port']}/{result['ports'][0]['proto']}",
                'protocol': result['ports'][0]['proto'],
                'port': result['ports'][0]['port'],
                'status': 'open',
                'type': 'service'
            }
            services.append(service)
        
        return self._bulk_create_services(services)
    
    def _map_severity(self, zap_risk):
        """Map ZAP risk levels to Faraday severity"""
        mapping = {
            '0': 'informational',
            '1': 'low',
            '2': 'medium',
            '3': 'high',
            '4': 'critical'
        }
        return mapping.get(str(zap_risk), 'unclassified')
    
    def _bulk_create_vulns(self, vulnerabilities):
        """Bulk create vulnerabilities in Faraday"""
        url = f'{self.base_url}/ws/{WORKSPACE}/vulns'
        created = 0
        
        for vuln in vulnerabilities:
            try:
                response = self.session.post(url, json=vuln)
                if response.status_code in [201, 200]:
                    created += 1
                else:
                    print(f"Failed to create vuln: {response.text}")
            except Exception as e:
                print(f"Error creating vulnerability: {e}")
        
        print(f"Created {created}/{len(vulnerabilities)} vulnerabilities")
        return created
    
    def _bulk_create_services(self, services):
        """Bulk create services in Faraday"""
        url = f'{self.base_url}/ws/{WORKSPACE}/services'
        created = 0
        
        for service in services:
            try:
                response = self.session.post(url, json=service)
                if response.status_code in [201, 200]:
                    created += 1
            except Exception as e:
                print(f"Error creating service: {e}")
        
        print(f"Created {created}/{len(services)} services")
        return created

if __name__ == '__main__':
    importer = FaradayImporter()
    
    # Import ZAP results
    if Path('zap-report.json').exists():
        print("Importing ZAP results...")
        importer.import_zap_report('zap-report.json')
    
    # Import Masscan results
    if Path('masscan-report.json').exists():
        print("Importing Masscan results...")
        importer.import_masscan_report('masscan-report.json')

