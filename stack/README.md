# Bojemoi Lab - Docker Swarm Stacks

Infrastructure as Code pour le laboratoire Bojemoi.

## Architecture

- **Reverse Proxy**: Traefik avec Let's Encrypt
- **Monitoring**: Prometheus, Grafana, Loki, Alertmanager
- **Security**: CrowdSec, Suricata, Faraday
- **Services**: 20+ services en production

## Structure
```
/opt/bojemoi/stacks/
├── *.yml                    # Stacks Docker Swarm
├── scripts/                 # Scripts de déploiement
├── configs/                 # Configurations des services
└── .gitlab-ci.yml          # Pipeline CI/CD
```

## Déploiement

### Via GitLab CI/CD (recommandé)
1. Modifier le stack YAML
2. Commit et push vers GitLab
3. Pipeline valide automatiquement
4. Cliquer "Play" pour déployer

### Manuel
```bash
docker stack deploy -c nom-stack.yml nom-stack --prune
```

## Stacks disponibles

- `01-traefik.yml` - Reverse proxy et certificats SSL
- `10-monitoring.yml` - Prometheus, Grafana, Loki
- `20-security.yml` - CrowdSec, Suricata
- `30-faraday.yml` - Gestion des vulnérabilités
- `70-service-zarovnik.yml` - Service Zarovnik
- ... (liste complète avec `ls *.yml`)

## Maintenance

### Voir les services actifs
```bash
docker service ls
docker stack ls
```

### Logs d'un service
```bash
docker service logs -f nom_service
```

### Mettre à jour un stack
```bash
git pull
docker stack deploy -c stack.yml nom-stack --prune --resolve-image always
```
