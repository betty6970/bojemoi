---
title: "[bojemoi] Push 2 commit(s) to main"
date: 2026-06-30T15:50:15+02:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 2 commit(s) par grafana-watcher dans bojemoi/main"
author: "grafana-watcher"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 2 |
| **Pushed by** | grafana-watcher |

### Commits

- **9d0d3ba** chore: consolidate sub-repos into /opt/bojemoi (grafana-watcher)
- **4b9d525** feat(grafana-watcher): add grafana labels on all 20 base stack services (grafana-watcher)


### Diff Summary

```
 grafana-screenshot/Dockerfile                      |   11 +
 grafana-screenshot/docker-compose.yml              |   22 +
 grafana-screenshot/screenshot.py                   |   56 +
 .../screenshots/batch/alertmanager.png             |  Bin 0 -> 148322 bytes
 .../screenshots/batch/c2-sessions.png              |  Bin 0 -> 151193 bytes
 .../screenshots/batch/docker-container-metrics.png |  Bin 0 -> 105040 bytes
 .../screenshots/batch/docker-registry.png          |  Bin 0 -> 231492 bytes
 .../screenshots/batch/docker-swarm-overview.png    |  Bin 0 -> 111607 bytes
 .../screenshots/batch/loki-stack.png               |  Bin 0 -> 256376 bytes
 .../screenshots/batch/nvidia-dcgm.png              |  Bin 0 -> 150873 bytes
 .../screenshots/batch/nvidia-gpu.png               |  Bin 0 -> 242125 bytes
 .../screenshots/batch/nym-operator.png             |  Bin 0 -> 89265 bytes
 .../screenshots/batch/pentest-overview.png         |  Bin 0 -> 241165 bytes
 .../screenshots/batch/pentest-vuln.png             |  Bin 0 -> 371237 bytes
 .../screenshots/batch/pipeline-borodino.png        |  Bin 0 -> 525119 bytes
 .../screenshots/batch/postgresql-exporter.png      |  Bin 0 -> 262208 bytes
 .../batch/postgresql-infrastructure.png            |  Bin 0 -> 102784 bytes
 .../screenshots/batch/scan-results.png             |  Bin 0 -> 203535 bytes
 .../screenshots/batch/security-monitoring.png      |  Bin 0 -> 53706 bytes
 .../screenshots/batch/sentinel-iot.png             |  Bin 0 -> 174178 bytes
 grafana-screenshot/screenshots/batch/traefik.png   |  Bin 0 -> 177730 bytes
 grafana-screenshot/screenshots/batch/trivy.png     |  Bin 0 -> 58564 bytes
 grafana-screenshot/screenshots/batch/valkey.png    |  Bin 0 -> 292406 bytes
 .../screenshots/batch/vigie-certfr.png             |  Bin 0 -> 117011 bytes
 grafana-screenshot/screenshots/grafana.png         |  Bin 0 -> 134302 bytes
 .../screenshots/grafana_viewport.png               |  Bin 0 -> 199132 bytes
 ml-threat/Dockerfile.ml-threat                     |   42 +
 ml-threat/ai_agents.py                             |  240 +++
 ml-threat/api.py                                   |  496 ++++++
 .../bojemoi_mitre_attack.egg-info/PKG-INFO         |    7 +
 .../bojemoi_mitre_attack.egg-info/SOURCES.txt      |   13 +
 .../dependency_links.txt                           |    1 +
 .../bojemoi_mitre_attack.egg-info/top_level.txt    |    1 +
 .../bojemoi_mitre_attack/__init__.py               |   23 +
 .../bojemoi_mitre_attack/formatters.py             |  136 ++
 .../bojemoi_mitre_attack/mapper.py                 |  324 ++++
 .../bojemoi_mitre_attack/mappings/__init__.py      |   11 +
 .../bojemoi_mitre_attack/mappings/osint.py         |   54 +
 .../bojemoi_mitre_attack/mappings/suricata.py      |   99 ++
 .../bojemoi_mitre_attack/mappings/vulnerability.py |   73 +
 .../bojemoi_mitre_attack/models.py                 |   36 +
 ml-threat/bojemoi-mitre-attack/setup.py            |   10 +
 ml-threat/config/config.yaml                       |   95 ++
 ml-threat/database.py                              |  543 +++++++
 ml-threat/feature_extractor.py                     |  330 ++++
 ml-threat/integration_example.py                   |  391 +++++
 ml-threat/investigator.py                          |  598 +++++++
 ml-threat/ml_models.py                             |  353 ++++
 ml-threat/requirements.txt                         |   31 +
 ml-threat/telegram_bot.py                          |  329 ++++
 ml-threat/test.py                                  |  205 +++
 ml-threat/train.py                                 |  206 +++
 scripts/create-networks.sh                         |   53 +
 scripts/push-images.sh                             |  262 +++
 stack/00-service-boot.yml                          |  453 ++++++
 stack/01-service-hl.yml                            |  101 ++
 telegram-bot/Dockerfile.telegram-bot               |   29 +
 telegram-bot/blockchain.py                         |  152 ++
 telegram-bot/bot.py                                | 1330 ++++++++++++++++
 telegram-bot/config.py                             |   89 ++
 telegram-bot/database/__init__.py                  |   16 +
 telegram-bot/database/connection.py                |   48 +
 telegram-bot/database/crud.py                      |  759 +++++++++
 telegram-bot/database/models.py                    |  184 +++
 telegram-bot/deploy.sh                             |   53 +
 telegram-bot/init_db.py                            |   15 +
 telegram-bot/integrations/__init__.py              |   48 +
 telegram-bot/integrations/cortex.py                |  423 +++++
 telegram-bot/integrations/maltego.py               |  412 +++++
 telegram-bot/integrations/misp.py                  |  436 +++++
 telegram-bot/integrations/mitre_attack.py          |  644 ++++++++
 telegram-bot/integrations/thehive.py               |  590 +++++++
 telegram-bot/osint.py                              | 1682 ++++++++++++++++++++
 telegram-bot/redis_client.py                       |  280 ++++
 telegram-bot/requirements.txt                      |   11 +
 volumes/grafana/dashboards/red-team/.gitkeep       |    1 +
 76 files changed, 12807 insertions(+)
```
