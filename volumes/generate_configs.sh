#!/bin/bash
################################################################################
# Génération automatique des fichiers de configuration
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/configs"

log_info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }
log_success() { echo -e "\033[0;32m[SUCCESS]\033[0m $1"; }

mkdir -p "${CONFIG_DIR}"/{alloy,prometheus,alertmanager,grafana}

################################################################################
# Générer config Alloy
################################################################################
cat > "${CONFIG_DIR}/alloy/config.alloy" <<'ALLOY_EOF'
// ========================================
// PROMETHEUS SCRAPING
// ========================================

prometheus.scrape "node_exporter" {
  targets = [{"__address__" = "base_node-exporter:9100"}]
  forward_to = [prometheus.remote_write.default.receiver]
  scrape_interval = "15s"
}

prometheus.scrape "cadvisor" {
  targets = [{"__address__" = "base_cadvisor:8080"}]
  forward_to = [prometheus.remote_write.default.receiver]
  scrape_interval = "15s"
}

prometheus.scrape "traefik" {
  targets = [{"__address__" = "base_traefik:8080"}]
  forward_to = [prometheus.remote_write.default.receiver]
  scrape_interval = "15s"
}

prometheus.scrape "suricata_exporter" {
  targets = [{"__address__" = "base_suricata-exporter:9917"}]
  forward_to = [prometheus.remote_write.default.receiver]
  scrape_interval = "15s"
}

prometheus.scrape "postgres_exporter" {
  targets = [{"__address__" = "postgres-exporter:9187"}]
  forward_to = [prometheus.remote_write.default.receiver]
  scrape_interval = "30s"
}

prometheus.scrape "redis_exporter" {
  targets = [{"__address__" = "redis-exporter:9121"}]
  forward_to = [prometheus.remote_write.default.receiver]
  scrape_interval = "30s"
}

prometheus.scrape "prometheus" {
  targets = [{"__address__" = "base_prometheus:9090"}]
  forward_to = [prometheus.remote_write.default.receiver]
  scrape_interval = "30s"
}

prometheus.scrape "loki" {
  targets = [{"__address__" = "base_loki:3100"}]
  forward_to = [prometheus.remote_write.default.receiver]
  scrape_interval = "30s"
}

prometheus.scrape "grafana" {
  targets = [{"__address__" = "base_grafana:3000"}]
  forward_to = [prometheus.remote_write.default.receiver]
  scrape_interval = "30s"
}

prometheus.scrape "alertmanager" {
  targets = [{"__address__" = "base_alertmanager:9093"}]
  forward_to = [prometheus.remote_write.default.receiver]
  scrape_interval = "30s"
}

prometheus.remote_write "default" {
  endpoint {
    url = "http://base_prometheus:9090/api/v1/write"
    queue_config {
      capacity = 10000
      max_shards = 200
    }
  }
}

// ========================================
// LOKI LOG COLLECTION
// ========================================

discovery.docker "containers" {
  host = "unix:///var/run/docker.sock"
  filter {
    name = "name"
    values = ["base_.*", "faraday_.*", "owasp_.*"]
  }
}

loki.source.docker "docker_logs" {
  host = "unix:///var/run/docker.sock"
  targets = discovery.docker.containers.targets
  forward_to = [loki.process.parse_logs.receiver]
  labels = {job = "docker"}
}

loki.process "parse_logs" {
  stage.json {
    expressions = {
      event_type = "event_type",
      src_ip = "src_ip",
      dest_ip = "dest_ip",
      alert_signature = "alert.signature",
      alert_severity = "alert.severity",
      severity = "alert.severity",
      query = "dns.query",
      query_type = "dns.type",
    }
  }
  
  stage.labels {
    values = {
      event_type = "",
      severity = "",
    }
  }
  
  forward_to = [loki.write.local.receiver]
}

loki.source.file "suricata_eve" {
  targets = [{
    __path__ = "/var/log/suricata/eve.json",
    job = "suricata",
  }]
  forward_to = [loki.process.parse_logs.receiver]
}

loki.write "local" {
  endpoint {
    url = "http://base_loki:3100/loki/api/v1/push"
    batch_wait = "1s"
    batch_size = 1048576
  }
}
ALLOY_EOF

log_success "Generated: ${CONFIG_DIR}/alloy/config.alloy"

################################################################################
# Générer Prometheus rules (version compacte)
################################################################################
cat > "${CONFIG_DIR}/prometheus/alerts.yml" <<'PROM_EOF'
groups:
  - name: infrastructure
    interval: 30s
    rules:
      - alert: ServiceDown
        expr: up{job=~"base_.*|faraday_.*|owasp_.*"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Service {{$labels.job}} DOWN"
          
      - alert: HighCPU
        expr: 100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CPU élevé: {{$value}}%"
          
      - alert: HighMemory
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Mémoire saturée: {{$value}}%"
          
      - alert: DiskFull
        expr: 100 - ((node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100) > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disque plein: {{$value}}%"

  - name: security
    interval: 1m
    rules:
      - alert: SuricataHighAlertRate
        expr: rate({job="suricata"} | json | event_type="alert" [5m]) > 10
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Taux d'alertes IDS élevé"
          
      - alert: SuricataCritical
        expr: count_over_time({job="suricata"} | json | event_type="alert" | severity="1" [5m]) > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "ALERTE CRITIQUE SURICATA"
          
      - alert: WebAttack
        expr: count_over_time({job="traefik"} |~ "(?i)(sql|xss|exec)" [10m]) > 5
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Tentatives d'attaque web détectées"

  - name: performance
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: (sum(rate(traefik_service_requests_total{code=~"5.."}[5m])) / sum(rate(traefik_service_requests_total[5m]))) * 100 > 5
        for: 3m
        labels:
          severity: critical
        annotations:
          summary: "Taux d'erreurs 5xx: {{$value}}%"
          
      - alert: HighLatency
        expr: histogram_quantile(0.95, sum(rate(traefik_service_request_duration_seconds_bucket[5m])) by (le)) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Latence P95 élevée: {{$value}}s"
PROM_EOF

log_success "Generated: ${CONFIG_DIR}/prometheus/alerts.yml"

################################################################################
# Générer Alertmanager config
################################################################################
cat > "${CONFIG_DIR}/alertmanager/alertmanager.yml" <<'AM_EOF'
global:
  resolve_timeout: 5m
  smtp_from: 'alertmanager@bojemoi.lab.local'
  smtp_smarthost: 'base_postfix:25'
  smtp_require_tls: false

route:
  receiver: 'default'
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  
  routes:
    - match:
        severity: critical
      receiver: 'critical'
      group_wait: 10s
      repeat_interval: 30m

receivers:
  - name: 'default'
    email_configs:
      - to: 'admin@bojemoi.lab.local'
        headers:
          Subject: '[MONITORING] {{ .GroupLabels.alertname }}'
  
  - name: 'critical'
    email_configs:
      - to: 'security@bojemoi.lab.local'
        headers:
          Subject: '� [CRITIQUE] {{ .GroupLabels.alertname }}'

inhibit_rules:
  - source_match:
      severity: critical
    target_match:
      severity: warning
    equal: ['alertname']
AM_EOF

log_success "Generated: ${CONFIG_DIR}/alertmanager/alertmanager.yml"

################################################################################
# Dashboard minimal (Security)
################################################################################
cat > "${CONFIG_DIR}/grafana/dashboard-security-minimal.json" <<'DASH_EOF'
{
  "title": "� Security Monitoring",
  "tags": ["security"],
  "timezone": "browser",
  "refresh": "30s",
  "panels": [
    {
      "title": "Total Alertes",
      "type": "stat",
      "datasource": "Loki",
      "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
      "targets": [{
        "expr": "sum(count_over_time({job=\"suricata\"} | json | event_type=\"alert\" [1h]))"
      }]
    },
    {
      "title": "Top Signatures",
      "type": "table",
      "datasource": "Loki",
      "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4},
      "targets": [{
        "expr": "topk(10, sum by (alert_signature) (count_over_time({job=\"suricata\"} | json | event_type=\"alert\" [1h])))"
      }]
    },
    {
      "title": "Timeline Alertes",
      "type": "timeseries",
      "datasource": "Loki",
      "gridPos": {"h": 8, "w": 24, "x": 0, "y": 12},
      "targets": [{
        "expr": "sum(rate({job=\"suricata\"} | json | event_type=\"alert\" [5m]))"
      }]
    }
  ]
}
DASH_EOF

log_success "Generated: ${CONFIG_DIR}/grafana/dashboard-security-minimal.json"

echo ""
log_success "✓ All configuration files generated in: ${CONFIG_DIR}"
echo ""
echo "Structure:"
tree -L 2 "$CONFIG_DIR" 2>/dev/null || find "$CONFIG_DIR" -type f

