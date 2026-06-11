---
title: "[bojemoi] Push 8 commit(s) to main"
date: 2026-06-11T14:43:20+02:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 8 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 8 |
| **Pushed by** | Betty |

### Commits

- **03facaa** fix(grafana): panneaux réseau par interface sur node_network_* au lieu de cAdvisor (Betty)
- **751d152** fix(monitoring): node-exporter en host network pour métriques réseau correctes (Betty)
- **c879866** feat(monitoring): logs infra-daily-monitor → Loki + dashboard Grafana (Betty)
- **1e41573** feat(agents): infra-daily-monitor — check + restart ZAP proxy saturé (Betty)
- **fc1cd7a** feat(agents): infra-daily-monitor — actions correctives et proactives (Betty)
- **f3a2228** feat(agents): déléguer /monitor à l'agent infra-daily-monitor (Betty)
- **7193636** fix(razvedka): re-auth Telegram session + cleanup stack auth workflow (Betty)
- **a1f4ae6** feat(stack): mount SecLists in msf-teamserver + disable pentest-orchestrator (Betty)


### Diff Summary

```
 .claude/agents/infra-daily-monitor.md              | 331 +++++++++++++++++++++
 .claude/commands/monitor.md                        | 118 +-------
 borodino/thearm_uzi                                |   8 +
 stack/01-service-hl.yml                            |  16 +-
 stack/39-service-borodino-msf.yml                  |   5 +
 stack/40-service-borodino.yml                      |   1 +
 stack/46-service-razvedka.yml                      |  25 ++
 stack/60-service-telegram.yml                      |   2 +-
 volumes/alloy/config/config.alloy                  |   9 +
 .../general/docker-container-metrics.json          |  14 +-
 .../grafana/dashboards/general/infra-monitor.json  |  89 ++++++
 volumes/grafana/dashboards/security/hosts-geo.json | 305 -------------------
 12 files changed, 486 insertions(+), 437 deletions(-)
```
