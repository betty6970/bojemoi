# Alertes

Configuration et gestion des alertes Prometheus/Alertmanager.

## Fichiers de Configuration

| Fichier | Description |
|---------|-------------|
| `/opt/bojemoi/volumes/prometheus/rules/alerts.yml` | Alertes infrastructure |
| `/opt/bojemoi/volumes/prometheus/rules/alert_rules.yml` | Alertes cluster/services |
| `/opt/bojemoi/volumes/alertmanager/alertmanager.yml` | Routage et notifications |

## Alertes CPU

| Alerte | Seuil | Durée | Sévérité |
|--------|-------|-------|----------|
| HostHighCPU | > 85% | 10 min | warning |
| HostCriticalCPU | > 95% | 5 min | critical |
| NodeHighCPU | > 85% | 5 min | warning |
| NodeCriticalCPU | > 95% | 3 min | critical |
| ContainerHighCPU | > 80% | 10 min | warning |
| ContainerCriticalCPU | > 95% | 5 min | critical |

## Alertes Mémoire

| Alerte | Seuil | Durée | Sévérité |
|--------|-------|-------|----------|
| HostHighMemory | > 85% | 10 min | warning |
| HostCriticalMemory | > 95% | 5 min | critical |
| ContainerHighMemory | > 85% | 10 min | warning |

## Alertes Disque

| Alerte | Seuil | Durée | Sévérité |
|--------|-------|-------|----------|
| HostDiskSpaceWarning | < 15% libre | 5 min | warning |
| HostDiskSpaceCritical | < 5% libre | 2 min | critical |

## Alertes Services

| Alerte | Description | Sévérité |
|--------|-------------|----------|
| PrometheusDown | Prometheus ne répond plus | critical |
| AlertmanagerDown | Alertmanager ne répond plus | critical |
| GrafanaDown | Grafana ne répond plus | warning |
| TraefikDown | Reverse proxy down | critical |
| PostgresDown | Base de données down | critical |
| FaradayDown | Faraday ne répond plus | warning |

## Configuration Email

```yaml
# /opt/bojemoi/volumes/alertmanager/alertmanager.yml
global:
  smtp_from: 'betty.bombers@bojemoi.lab'
  smtp_smarthost: 'protonmail-bridge:1025'
  smtp_auth_username: 'betty.bombers@proton.me'
  smtp_require_tls: true

receivers:
  - name: 'default'
    email_configs:
      - to: 'betty.bombers@proton.me'
        send_resolved: true
```

## Commandes

### Voir les alertes actives
```bash
# Via Claude Code
/alerts list

# Manuellement
curl -s http://alertmanager.bojemoi.lab:9093/api/v2/alerts | jq '.[].labels.alertname'
```

### Voir les règles chargées
```bash
/alerts rules
```

### Vérifier le CPU
```bash
/alerts cpu
```

## Ajouter une Nouvelle Alerte

1. Éditer `/opt/bojemoi/volumes/prometheus/rules/alerts.yml`

2. Ajouter la règle:
```yaml
- alert: MonNouvelleAlerte
  expr: ma_metrique > seuil
  for: 5m
  labels:
    severity: warning
    component: mon_composant
  annotations:
    summary: "Description courte"
    description: "Description détaillée avec {{ $value }}"
```

3. Recharger Prometheus:
```bash
docker exec $(docker ps -q -f name=prometheus) wget -qO- --post-data='' 'http://localhost:9090/-/reload'
```

## Silencer une Alerte

Via l'interface Alertmanager:
1. Aller sur https://alertmanager.bojemoi.lab
2. Cliquer sur "Silences" > "New Silence"
3. Configurer les matchers (alertname, severity, etc.)
4. Définir la durée
