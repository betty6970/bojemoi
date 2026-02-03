# Faraday

Plateforme de gestion des vulnérabilités - centralise les résultats de tous les scanners.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│    Scanners     │────▶│     Faraday     │
│ (Nuclei, ZAP,   │     │   PostgreSQL    │
│  Masscan, etc.) │     │                 │
└─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────┐
                        │  Dashboard  │
                        │    Web UI   │
                        └─────────────┘
```

## Accès

- **URL**: https://faraday.bojemoi.lab (si configuré avec Traefik)
- **Port interne**: 5985
- **Credentials par défaut**: faraday / changeme

## Service Docker

```yaml
# Dans 40-service-borodino.yml
faraday:
  image: faradaysec/faraday:latest
  networks:
    - backend
  ports:
    - 5985:5985
```

## Commandes Claude Code

```bash
/faraday status      # Vérifier la connexion
/faraday workspaces  # Lister les workspaces
/faraday import      # Importer les résultats
/faraday list        # Lister les fichiers de résultats
```

## API Faraday

### Authentification
```bash
# Login
curl -X POST http://faraday:5985/_api/login \
  -H "Content-Type: application/json" \
  -d '{"email": "faraday", "password": "changeme"}'
```

### Workspaces
```bash
# Lister les workspaces
curl http://faraday:5985/_api/v3/ws \
  -H "Cookie: session=<token>"

# Créer un workspace
curl -X POST http://faraday:5985/_api/v3/ws \
  -H "Content-Type: application/json" \
  -d '{"name": "mon_workspace"}'
```

### Vulnérabilités
```bash
# Lister les vulnérabilités d'un workspace
curl http://faraday:5985/_api/v3/ws/mon_workspace/vulns

# Créer une vulnérabilité
curl -X POST http://faraday:5985/_api/v3/ws/mon_workspace/vulns \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SQL Injection",
    "desc": "Description de la vuln",
    "severity": "high",
    "type": "Vulnerability",
    "parent": 1,
    "parent_type": "Host"
  }'
```

## Import des Résultats

### Automatique (via orchestrator)
Les scans lancés via l'orchestrateur envoient automatiquement les résultats à Faraday.

### Manuel (script import_results.py)
```bash
cd /opt/bojemoi/samsonov/pentest_orchestrator

# Voir les fichiers en attente
python3 import_results.py --list

# Importer tous les résultats
python3 import_results.py

# Importer vers un workspace spécifique
python3 import_results.py -w production

# Prévisualiser sans importer
python3 import_results.py --dry-run
```

### Via Plugin Python
```python
from plugins.plugin_faraday import import_results, get_status

# Vérifier la connexion
status = get_status()
print(status)

# Importer des résultats
results = {
    'target': '192.168.1.1',
    'scans': [
        {
            'status': 'success',
            'result': {
                'tool': 'nuclei',
                'findings': [...]
            }
        }
    ]
}
import_results(workspace='default', results=results)
```

## Formats Supportés

L'orchestrateur convertit automatiquement les formats suivants:

| Outil | Format | Champs |
|-------|--------|--------|
| Nuclei | JSON | template-id, info, matched-at |
| ZAP | JSON | alert, risk, url, description |
| Masscan | JSON | ports, ip, proto |
| VulnX | JSON | vulnerability, cms, version |

## Configuration

### Variables d'environnement
```bash
FARADAY_URL=http://faraday:5985
FARADAY_USERNAME=faraday
FARADAY_PASSWORD=changeme
```

### config/config.json
```json
{
  "faraday": {
    "url": "http://faraday:5985",
    "username": "faraday",
    "password": "changeme"
  }
}
```

## Dépannage

### Connexion échouée
```bash
# Vérifier que le service tourne
docker service ls | grep faraday

# Vérifier les logs
docker service logs borodino_faraday --tail 50

# Tester la connectivité
curl -v http://faraday:5985/_api/v3/ws
```

### Import échoue
```bash
# Vérifier les logs d'import
cd /opt/bojemoi/samsonov/pentest_orchestrator
python3 import_results.py --dry-run

# Vérifier le format du fichier résultat
cat results/scan_*.json | jq '.scans[0].result'
```
