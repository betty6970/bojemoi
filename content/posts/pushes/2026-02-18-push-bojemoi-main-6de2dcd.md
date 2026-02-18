---
title: "[bojemoi] Push 4 commit(s) to main"
date: 2026-02-18T14:34:16+01:00
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

- **6de2dcd** volumes: add Tempo datasource to Grafana, update rsync config (Betty)
- **c4c408c** stacks: various updates - suricata enricher, network fixes, placement cleanup (Betty)
- **b76f9a8** samsonov: integrate bojemoi-mitre-attack library for vuln enrichment (Betty)
- **c33a4a5** borodino: bm12 v2 - targeted NSE scripts and server classification (Betty)


### Diff Summary

```
 borodino/thearm_bm12                               | 389 ++++++++++++++++++---
 samsonov/Dockerfile.samsonov                       |   6 +-
 .../pentest_orchestrator/plugins/plugin_faraday.py |  71 +++-
 stack/01-service-hl.yml                            |   9 +-
 stack/01-suricata-host.yml                         |  16 +
 stack/45-service-ml-threat-intel.yml               |   3 -
 stack/46-service-razvedka.yml                      |   2 +-
 stack/47-service-vigie.yml                         |   2 +-
 stack/48-service-dozor.yml                         |   2 +-
 stack/60-service-samsonov.yml                      | 164 ---------
 .../provisioning/datasources/datasources.yml       |  18 +
 volumes/rsync/configs/rsyncd.conf                  |  29 +-
 12 files changed, 460 insertions(+), 251 deletions(-)
```
