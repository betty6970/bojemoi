---
title: "[bojemoi] Push 11 commit(s) to main"
date: 2026-04-24T22:34:13+02:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 11 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 11 |
| **Pushed by** | Betty |

### Commits

- **4aba669** feat(orchestrator): local cloud-init templates — remove Gitea runtime dependency (Betty)
- **eb9a1ee** feat(packaging): package-dist.sh + Makefile + install/env fixes (Betty)
- **1c2ee83** feat(postgres): init SQL — create all databases on first start (Betty)
- **047a7a8** docs: update ARCHITECTURE + README, add runbook (Betty)
- **4adce3e** feat: new components — c2-monitor, ptaas-init, postgres-ssl, RIPE import (Betty)
- **cf02179** chore(claude): update monitor command (Betty)
- **9e5b612** feat(grafana): update pentest + security dashboards (Betty)
- **081acdb** feat(monitoring): prometheus targets + alert rules + alloy config (Betty)
- **b9abb6d** feat(stacks): update base, borodino, nym, dozor, ollama (Betty)
- **13e2bf9** fix: borodino/nym/zap/nuclei — pending fixes (Betty)
- **4e1f103** chore: exclude postgres SSL certs + remove obsolete scripts (Betty)


### Diff Summary

```
 .claude/commands/monitor.md                        |  48 +-
 .env.example                                       |  18 +-
 .gitignore                                         |   1 +
 ARCHITECTURE.md                                    | 323 +++++++
 Makefile                                           | 108 +++
 README.md                                          |  13 +-
 borodino/Dockerfile.postgres-ssl                   |   6 +
 borodino/start_msf_server.sh                       |  25 +-
 borodino/thearm_uzi                                |   7 +-
 c2-monitor/Dockerfile                              |  10 +
 c2-monitor/monitor.py                              | 205 +++++
 c2-monitor/requirements.txt                        |   4 +
 docs/runbook/README.md                             |  12 +
 docs/runbook/borodino-rebuild.md                   |  44 +
 docs/runbook/docker-secrets.md                     |  54 ++
 docs/runbook/node-access.md                        |  49 ++
 docs/runbook/postgres-ssl.md                       |  52 ++
 docs/runbook/protonmail-bridge.md                  |  69 ++
 docs/runbook/stack-deploy.md                       |  72 ++
 install.sh                                         |  19 +-
 nym-proxy/Dockerfile                               |   2 +-
 oblast-1/Dockerfile.oblast-1                       |   2 -
 oblast-1/zap_scanner.py                            |   8 +-
 provisioning/cloud-init/alpine/database.yaml       |  62 ++
 provisioning/cloud-init/alpine/minimal.yaml        |  41 +
 provisioning/cloud-init/alpine/webserver.yaml      |  65 ++
 provisioning/cloud-init/common/hardening.sh        |  92 ++
 provisioning/cloud-init/common/setup_docker.sh     |  64 ++
 provisioning/cloud-init/common/setup_monitoring.sh |  50 ++
 provisioning/cloud-init/debian/default.yaml        |  54 ++
 provisioning/cloud-init/debian/webserver.yaml      |  72 ++
 provisioning/cloud-init/ubuntu/database.yaml       |  73 ++
 provisioning/cloud-init/ubuntu/default.yaml        |  54 ++
 provisioning/cloud-init/ubuntu/webserver.yaml      |  72 ++
 provisioning/orchestrator/app/config.py            |  54 +-
 provisioning/orchestrator/app/main.py              | 191 +---
 .../orchestrator/app/services/cloudinit_gen.py     |   8 +-
 .../app/services/local_template_client.py          | 159 ++++
 ptaas-init/Dockerfile                              |  12 +
 ptaas-init/init.py                                 | 241 +++++
 ptaas-init/requirements.txt                        |   3 +
 samsonov/nuclei_api/main.py                        |   7 +-
 scripts/cccp-v2.sh                                 | 195 -----
 scripts/cccp.sh.1                                  | 138 ---
 scripts/check_image_v1.py                          | 451 ----------
 scripts/import_2_faraday.py                        | 118 ---
 scripts/import_ripe_cidrs.py                       | 113 +++
 scripts/mockba-v1.sh                               | 114 ---
 scripts/orchestrator-zap-nuclei-faraday.sh         | 154 ----
 scripts/package-dist.sh                            | 305 +++++++
 scripts/stack_armement.export                      | 113 ---
 scripts/stack_base.export                          | 431 ---------
 scripts/stack_faraday.export                       |  51 --
 scripts/stack_masscan.export                       |  42 -
 scripts/stack_owasp.export                         |  66 --
 scripts/test_deploiement.sh                        |  10 -
 scripts/test_reso.sh                               |   6 -
 scripts/test_wget.sh                               |  48 -
 stack/01-service-hl.yml                            | 156 +++-
 stack/02-init-ptaas.yml                            |  64 ++
 stack/40-service-borodino.yml                      |  66 ++
 stack/41-service-nym.yml                           |   6 +-
 stack/48-service-dozor.yml                         |   3 +
 stack/51-service-ollama.yml                        |   3 +
 volumes/alloy/config/config.alloy                  |   4 +-
 .../grafana/dashboards/pentest/c2-sessions.json    | 198 +++++
 .../dashboards/pentest/pentest-overview.json       | 256 +++++-
 .../grafana/dashboards/pentest/scan-results.json   | 966 +++++----------------
 .../security/dashboard-security-minimal.json       |   2 +-
 volumes/grafana/dashboards/security/sentinel.json  |  14 +-
 volumes/grafana/dashboards/security/vigie.json     |  12 +-
 volumes/postgres/conf/pg_hba.conf                  |  22 +
 volumes/postgres/init/01-create-databases.sql      |  76 ++
 volumes/postgres/postgres-entrypoint.sh            |  14 +
 volumes/prometheus/prometheus.yml                  |   5 +
 volumes/prometheus/rules/alerts.yml                |  21 +
 76 files changed, 3813 insertions(+), 2955 deletions(-)
```
