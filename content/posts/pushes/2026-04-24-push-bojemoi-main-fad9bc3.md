---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-04-24T22:36:02+02:00
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

- **fad9bc3** feat: merge DefectDojo into borodino stack, add alert-agent, discord, suricata-exporter (Betty)


### Diff Summary

```
 ARCHITECTURE.md                                    |  65 +++-
 alert-agent/Dockerfile.alert-agent                 |  17 +
 alert-agent/alert_agent/__init__.py                |   0
 alert-agent/alert_agent/__main__.py                |  45 +++
 alert-agent/alert_agent/actions.py                 | 146 +++++++
 alert-agent/alert_agent/alerter.py                 |  58 +++
 alert-agent/alert_agent/config.py                  |  58 +++
 alert-agent/alert_agent/db.py                      | 107 ++++++
 alert-agent/alert_agent/enricher.py                | 105 ++++++
 alert-agent/alert_agent/llm.py                     |  99 +++++
 alert-agent/alert_agent/metrics.py                 |  25 ++
 alert-agent/alert_agent/webhook.py                 | 125 ++++++
 alert-agent/requirements.txt                       |   6 +
 discord/ARCHITECTURE.md                            |   0
 discord/cleanup.py                                 |  47 +++
 discord/populate.py                                | 420 +++++++++++++++++++++
 discord/post_architecture.py                       |  88 +++++
 discord/post_blueteam.py                           | 175 +++++++++
 discord/post_infra_channels.py                     | 321 ++++++++++++++++
 discord/post_intel_channels.py                     | 242 ++++++++++++
 provisioning/orchestrator/app/services/database.py | 231 +++---------
 razvedka/Dockerfile.razvedka                       |   3 +
 razvedka/auth_helper.py                            |  10 +-
 razvedka/razvedka/config.py                        |   4 +
 scripts/gameover.sh                                | 142 +++++++
 scripts/startover.sh                               |  40 +-
 stack/01-suricata-host.yml                         |  98 +++--
 stack/02-service-maintenance.yml                   |   2 +-
 stack/40-service-borodino.yml                      | 371 +++++++++++++++++-
 stack/41-service-nym.yml                           |  67 ----
 stack/45-service-ml-threat-intel.yml               |   5 +-
 stack/46-service-razvedka.yml                      |  21 +-
 stack/47-service-vigie.yml                         |  21 +-
 stack/48-service-alert-agent.yml                   |  73 ++++
 stack/60-service-telegram.yml                      |   9 +-
 stack/70-service-defectdojo.yml                    | 292 --------------
 suricata-exporter/Dockerfile                       |  10 +
 vigie/Dockerfile.vigie                             |   3 +
 vigie/vigie/config.py                              |   4 +
 volumes/alertmanager/alertmanager.yml              |   8 +
 volumes/dnsmask/dnsmask.conf                       |   2 +
 volumes/suricata/suricata.yaml                     |   1 +
 42 files changed, 2951 insertions(+), 615 deletions(-)
```
