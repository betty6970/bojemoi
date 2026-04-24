---
title: "[bojemoi] feat: merge DefectDojo into borodino stack, add alert-agent, discord, suricata-exporter"
date: 2026-04-24T22:36:02+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit fad9bc3 par Betty dans bojemoi"
author: "Betty"
---

## Commit `fad9bc3`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `fad9bc309a6829eab6c423395fcbdaf8e043a282` |


### Description

Stack consolidation:
- Move DefectDojo (nginx, uWSGI, Celery Beat/Worker, initializer, dojo-triage)
  from standalone 70-service-defectdojo.yml into 40-service-borodino.yml
- Move nym-proxy from 41-service-nym.yml into borodino stack
- Delete stack/70-service-defectdojo.yml and stack/41-service-nym.yml
- Add c2-monitor service to borodino stack

New components:
- alert-agent/ + stack/48-service-alert-agent.yml — alert routing agent
- suricata-exporter/ — Prometheus exporter for Suricata
- discord/ — Discord channel provisioning scripts (populate, post_architecture,
  post_blueteam, post_infra_channels, post_intel_channels, cleanup)
- scripts/gameover.sh — full teardown script
- scripts/startover.sh — full deploy with Alertmanager silence support

Service updates:
- razvedka: Dockerfile + config update
- vigie: Dockerfile + config update
- provisioning/orchestrator/app/services/database.py: refactored
- stack/01-suricata-host.yml, 02-service-maintenance.yml,
  45-service-ml-threat-intel.yml, 60-service-telegram.yml: minor fixes
- volumes/alertmanager/alertmanager.yml, dnsmask.conf, suricata.yaml: config updates

Docs:
- ARCHITECTURE.md: update node labels, stack table, DefectDojo section, c2-monitor flow

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	ARCHITECTURE.md
A	alert-agent/Dockerfile.alert-agent
A	alert-agent/alert_agent/__init__.py
A	alert-agent/alert_agent/__main__.py
A	alert-agent/alert_agent/actions.py
A	alert-agent/alert_agent/alerter.py
A	alert-agent/alert_agent/config.py
A	alert-agent/alert_agent/db.py
A	alert-agent/alert_agent/enricher.py
A	alert-agent/alert_agent/llm.py
A	alert-agent/alert_agent/metrics.py
A	alert-agent/alert_agent/webhook.py
A	alert-agent/requirements.txt
A	discord/ARCHITECTURE.md
A	discord/cleanup.py
A	discord/populate.py
A	discord/post_architecture.py
A	discord/post_blueteam.py
A	discord/post_infra_channels.py
A	discord/post_intel_channels.py
M	provisioning/orchestrator/app/services/database.py
M	razvedka/Dockerfile.razvedka
M	razvedka/auth_helper.py
M	razvedka/razvedka/config.py
A	scripts/gameover.sh
M	scripts/startover.sh
M	stack/01-suricata-host.yml
M	stack/02-service-maintenance.yml
M	stack/40-service-borodino.yml
D	stack/41-service-nym.yml
M	stack/45-service-ml-threat-intel.yml
M	stack/46-service-razvedka.yml
M	stack/47-service-vigie.yml
A	stack/48-service-alert-agent.yml
M	stack/60-service-telegram.yml
D	stack/70-service-defectdojo.yml
A	suricata-exporter/Dockerfile
M	vigie/Dockerfile.vigie
M	vigie/vigie/config.py
M	volumes/alertmanager/alertmanager.yml
M	volumes/dnsmask/dnsmask.conf
M	volumes/suricata/suricata.yaml
```

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
