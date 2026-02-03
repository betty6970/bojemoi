# Monitoring

Stack de monitoring basé sur Prometheus, Grafana, Loki et Alertmanager.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Prometheus  │────▶│ Alertmanager │────▶│   Email      │
│    :9090     │     │    :9093     │     │ (ProtonMail) │
└──────────────┘     └──────────────┘     └──────────────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│   Grafana    │◀────│     Loki     │
│    :3000     │     │    :3100     │
└──────────────┘     └──────────────┘
```

## Composants

### Prometheus
- **Port**: 9090
- **URL**: https://prometheus.bojemoi.lab
- **Config**: `/opt/bojemoi/volumes/prometheus/prometheus.yml`
- **Règles**: `/opt/bojemoi/volumes/prometheus/rules/`

### Grafana
- **Port**: 3000
- **URL**: https://grafana.bojemoi.lab
- **Login**: admin / admin_password
- **Config**: `/opt/bojemoi/volumes/grafana/`

### Alertmanager
- **Port**: 9093
- **URL**: https://alertmanager.bojemoi.lab
- **Config**: `/opt/bojemoi/volumes/alertmanager/alertmanager.yml`

### Loki
- **Port**: 3100
- **Config**: `/opt/bojemoi/volumes/loki/loki-config.yml`

## Exporters

| Exporter | Port | Description |
|----------|------|-------------|
| node-exporter | 9100 | Métriques système (CPU, mémoire, disque) |
| cAdvisor | 8088 | Métriques conteneurs Docker |
| postgres-exporter | 9187 | Métriques PostgreSQL |
| postfix-exporter | 9154 | Métriques Postfix |
| suricata-exporter | 9917 | Métriques Suricata IDS |

## Commandes Utiles

### Vérifier le statut
```bash
# Via Claude Code
/monitor

# Manuellement
docker service ls | grep -E "prometheus|grafana|alertmanager|loki"
```

### Recharger la configuration Prometheus
```bash
docker exec $(docker ps -q -f name=prometheus) wget -qO- --post-data='' 'http://localhost:9090/-/reload'
```

### Voir les targets Prometheus
```bash
curl -s http://prometheus.bojemoi.lab:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
```

## Métriques Clés

### CPU
```promql
# Usage CPU par node
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Usage CPU par conteneur
rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100
```

### Mémoire
```promql
# Usage mémoire par node
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Usage mémoire par conteneur
container_memory_usage_bytes{name!=""} / container_spec_memory_limit_bytes{name!=""} * 100
```

### Disque
```promql
# Espace disque utilisé
(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100
```
