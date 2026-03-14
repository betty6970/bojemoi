---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-03-14T21:52:42+01:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 1 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 1 |
| **Pushed by** | Betty |

### Commits

- **487dbeb** feat: sentinel IoT detector, trivy CI split, MCP server, provisioning hardening (Betty)


### Diff Summary

```
 .mcp.json                                         |   8 +
 archi.md                                          | 165 +++++++++++++
 blog/architecture-bojemoi-lab-linkedin.md         |  26 ++
 blog/architecture-bojemoi-lab-telegram.md         |  23 ++
 blog/bojemoi-lab-sur-dockerhub.md                 | 160 ++++++++++++
 blog/choisir alpine linux.md                      |  37 +++
 blog/mcp-server-bojemoi-lab.md                    | 125 ++++++++++
 blog/trivy-gitea-actions-en.md                    | 104 ++++++++
 blog/trivy-gitea-actions-fr.md                    | 104 ++++++++
 blog/tryvi implement.md                           |  95 +++++++
 blog/turn into MCP.md                             | 223 +++++++++++++++++
 claude/Dockerfile                                 |   3 +
 claude/claude.sh                                  |   9 +
 mcp-server/Dockerfile                             |  22 ++
 mcp-server/requirements.txt                       |   6 +
 mcp-server/server.py                              | 288 ++++++++++++++++++++++
 mcp-server/tools/__init__.py                      |   0
 mcp-server/tools/nmap.py                          |  95 +++++++
 mcp-server/tools/osint.py                         | 140 +++++++++++
 provisioning/Dockerfile.provisioning              |  55 +++--
 scripts/startover.sh                              |   2 +
 sentinel/collector/collector.py                   |  15 +-
 sentinel/sql/02-tables.sql                        |   2 +-
 stack/.gitlab-ci.yml                              | 107 +++++++-
 stack/01-service-hl.yml                           |   1 +
 stack/40-service-borodino.yml                     |   2 +-
 stack/50-service-trivy.yml                        |  23 ++
 stack/55-service-sentinel.yml                     |   4 +-
 trivy-scanner/Dockerfile                          |  14 ++
 trivy-scanner/scan-images.sh                      |  78 ++++++
 volumes/alertmanager/alertmanager.yml             |  29 +++
 volumes/grafana/dashboards/sentinel.json          | 235 ++++++++++++++++++
 volumes/grafana/datasources/sentinel-postgres.yml |  16 ++
 volumes/prometheus/prometheus.yml                 |   7 +
 volumes/prometheus/rules/sentinel_alerts.yml      |  52 ++++
 35 files changed, 2244 insertions(+), 31 deletions(-)
```
