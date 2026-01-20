#!/usr/bin/env python3
import requests
import sys
import time
from typing import Dict, List

SERVICES = {
    'traefik': 'https://traefik.bojemoi.lab.local/ping',
    'prometheus': 'https://prometheus.bojemoi.lab.local/-/healthy',
    'grafana': 'https://grafana.bojemoi.lab.local/api/health',
    'alertmanager': 'https://alertmanager.bojemoi.lab.local/-/healthy',
    'faraday': 'https://faraday.bojemoi.lab.local/_api/v3/info',
}

def check_service(name: str, url: str) -> bool:
    """Vérifie la santé d'un service"""
    try:
        response = requests.get(url, timeout=10, verify=False)
        if response.status_code == 200:
            print(f"✓ {name}: OK")
            return True
        else:
            print(f"✗ {name}: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ {name}: {str(e)}")
        return False

def main():
    print("=== Health Check Started ===\n")
    
    results = {}
    for name, url in SERVICES.items():
        results[name] = check_service(name, url)
        time.sleep(1)
    
    print("\n=== Summary ===")
    healthy = sum(results.values())
    total = len(results)
    print(f"Healthy services: {healthy}/{total}")
    
    if healthy == total:
        print("✓ All services are healthy")
        sys.exit(0)
    else:
        print("✗ Some services are unhealthy")
        sys.exit(1)

if __name__ == '__main__':
    main()
```

## 5. Configuration GitLab CI/CD Variables

Dans **GitLab → Settings → CI/CD → Variables** :
```
SSH_PRIVATE_KEY = <votre_clé_SSH_privée_pour_accéder_au_manager>
SWARM_MANAGER = manager.bojemoi.lab.local
DOCKER_HOST = ssh://manager@manager.bojemoi.lab.local

