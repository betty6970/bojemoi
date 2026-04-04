---
title: "[bojemoi] Push 2 commit(s) to main"
date: 2026-04-05T00:48:14+02:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 2 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 2 |
| **Pushed by** | Betty |

### Commits

- **24c1a17** feat(grafana): dashboards bind mount + scan-results dashboard + config swap fix (Betty)
- **454674c** feat(redirector): Loki log drain via VPN (Betty)


### Diff Summary

```
 borodino/redirector/Dockerfile                     |   2 +
 borodino/redirector/entrypoint.sh                  |  13 +-
 borodino/redirector/loki-shipper.py                |  73 ++
 stack/01-service-hl.yml                            |  26 +-
 .../grafana/dashboards/pentest/scan-results.json   | 202 +++++
 .../grafana/provisioning/dashboards/dashboards.yml | 838 +--------------------
 .../provisioning/datasources/datasources.yml       |  18 +
 7 files changed, 339 insertions(+), 833 deletions(-)
```
