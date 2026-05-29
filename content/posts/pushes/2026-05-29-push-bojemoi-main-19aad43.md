---
title: "[bojemoi] Push 4 commit(s) to main"
date: 2026-05-29T20:29:02+02:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 4 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 4 |
| **Pushed by** | Betty |

### Commits

- **19aad43** fix: corrections zap, ollama, alloy/prometheus et alerte swarm (Betty)
- **cee9b15** feat(monitoring): swarm-exporter service + métriques Prometheus sur le registry (Betty)
- **b95d4df** feat(grafana): renommer le dossier Pentest en Red Team + PostgreSQL-MSF par défaut (Betty)
- **5b26e52** fix(grafana): corriger les panels PostgreSQL pour Grafana 12 (Betty)


### Diff Summary

```
 oblast-1/zap_scanner.py                            |    2 +-
 stack/01-service-hl.yml                            |    2 +-
 stack/02-service-maintenance.yml                   |   34 +
 stack/51-service-ollama.yml                        |    8 +-
 volumes/alloy/config/config.alloy                  |   19 +-
 .../grafana/dashboards/pentest/c2-sessions.json    |  299 +-
 .../dashboards/pentest/pentest-overview.json       |  384 ++-
 .../dashboards/pentest/pipeline-overview.json      | 3028 ++++++++++----------
 .../grafana/dashboards/pentest/scan-results.json   |   59 +-
 .../dashboards/pentest/vuln-management.json        |  111 +-
 volumes/grafana/dashboards/security/sentinel.json  |  943 ++++--
 volumes/grafana/dashboards/security/vigie.json     |  252 +-
 .../grafana/provisioning/dashboards/dashboards.yml |    4 +-
 .../provisioning/datasources/datasources.yml       |   27 +-
 volumes/monitoring/swarm-exporter.py               |  144 +
 volumes/prometheus/prometheus.yml                  |    7 -
 volumes/prometheus/rules/alerts.yml                |    4 +-
 volumes/registry/config.yml                        |    5 +
 18 files changed, 3436 insertions(+), 1896 deletions(-)
```
