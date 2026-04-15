---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-04-15T23:00:02+02:00
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

- **4fa26f4** feat(vuln-mgmt): migrate Faraday CE → DefectDojo (Betty)


### Diff Summary

```
 faraday-triage/Dockerfile                          |  10 +
 faraday-triage/requirements.txt                    |   3 +
 faraday-triage/triage.py                           | 354 ++++++++++++++
 mcp-server/server.py                               |  49 +-
 mcp-server/tools/defectdojo.py                     | 190 ++++++++
 mcp-server/tools/faraday.py                        | 126 -----
 medved/honeypot/config.py                          |  16 +-
 medved/honeypot/db.py                              |  29 +-
 medved/honeypot/defectdojo_reporter.py             | 234 +++++++++
 medved/honeypot/faraday_reporter.py                | 200 --------
 medved/honeypot/main.py                            |   6 +-
 medved/honeypot/metrics.py                         |   6 +-
 oblast-1/zap_scanner.py                            | 212 ++++++---
 samsonov/nuclei_api/main.py                        | 212 +++++----
 .../pentest_orchestrator/plugins/plugin_faraday.py | 522 ---------------------
 stack/40-service-borodino.yml                      |  99 +---
 stack/49-service-mcp.yml                           |   7 +-
 stack/65-service-medved.yml                        |  14 +-
 stack/70-service-defectdojo.yml                    | 295 ++++++++++++
 volumes/nginx/conf.d/default.conf                  |   6 +-
 volumes/nginx/conf.d/sites/defectdojo.conf         |  31 ++
 volumes/nginx/conf.d/sites/faraday.conf            |  65 ---
 volumes/nginx/conf.d/upstreams/upstreams.conf      |   6 +-
 volumes/prometheus/rules/alert_rules.yml           |   8 +-
 volumes/prometheus/rules/alerts.yml                |  52 +-
 25 files changed, 1502 insertions(+), 1250 deletions(-)
```
