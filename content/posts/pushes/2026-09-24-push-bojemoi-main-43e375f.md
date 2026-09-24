---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-09-24T19:38:17+02:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 1 commit(s) par grafana-watcher dans bojemoi/main"
author: "grafana-watcher"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 1 |
| **Pushed by** | grafana-watcher |

### Commits

- **43e375f** feat(provisioning): reconstruire sources Python + corriger bugs XenServer critiques (grafana-watcher)


### Diff Summary

```
 provisioning/Dockerfile.provisioning               |  22 +
 provisioning/cloud-init/alpine/database.yaml       |  62 ++
 provisioning/cloud-init/alpine/minimal.yaml        |  41 +
 provisioning/cloud-init/alpine/webserver.yaml      |  65 ++
 provisioning/cloud-init/common/hardening.sh        |  92 +++
 provisioning/cloud-init/common/setup_docker.sh     |  64 ++
 provisioning/cloud-init/common/setup_monitoring.sh |  50 ++
 provisioning/cloud-init/debian/default.yaml        |  54 ++
 provisioning/cloud-init/debian/webserver.yaml      |  72 ++
 provisioning/cloud-init/ubuntu/database.yaml       |  73 ++
 provisioning/cloud-init/ubuntu/default.yaml        |  54 ++
 provisioning/cloud-init/ubuntu/webserver.yaml      |  72 ++
 provisioning/orchestrator/app/__init__.py          |   3 +
 provisioning/orchestrator/app/config.py            | 127 +++
 provisioning/orchestrator/app/main.py              | 867 +++++++++++++++++++++
 provisioning/orchestrator/app/metrics.py           | 100 +++
 .../orchestrator/app/middleware/__init__.py        |   1 +
 .../orchestrator/app/middleware/ip_validation.py   |  90 +++
 provisioning/orchestrator/app/models/__init__.py   |  15 +
 provisioning/orchestrator/app/models/schemas.py    | 257 ++++++
 provisioning/orchestrator/app/services/__init__.py |   1 +
 .../orchestrator/app/services/blockchain.py        | 215 +++++
 .../orchestrator/app/services/cloudinit_gen.py     |  35 +
 provisioning/orchestrator/app/services/database.py | 112 +++
 .../orchestrator/app/services/docker_client.py     |  93 +++
 .../orchestrator/app/services/gitea_client.py      |  75 ++
 .../app/services/ip2location_client.py             |  51 ++
 .../app/services/local_template_client.py          |  56 ++
 .../orchestrator/app/services/rapid7_manager.py    |  64 ++
 .../orchestrator/app/services/vulnhub_manager.py   | 126 +++
 .../orchestrator/app/services/xenserver_client.py  |  86 ++
 .../app/services/xenserver_client_real.py          | 839 ++++++++++++++++++++
 provisioning/requirements.txt                      |  10 +
 33 files changed, 3944 insertions(+)
```
