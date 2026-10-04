---
title: "[bojemoi] Push 2 commit(s) to main"
date: 2026-10-04T22:10:58+02:00
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

- **3b43802** fix(nuclei-api): sources reconstruites (refs borodino build) (grafana-watcher)
- **afbed36** feat(grafana): campaign-dispatcher dashboard — remplace pentest-orchestrator (grafana-watcher)


### Diff Summary

```
 Dockerfile.nuclei-api                              |  30 ++
 samsonov/nuclei_api/entrypoint.sh                  |  28 ++
 samsonov/nuclei_api/main.py                        | 410 +++++++++++++++++++++
 samsonov/nuclei_api/requirements.txt               |   4 +
 .../dashboards/red-team/campaign-dispatcher.json   |  31 ++
 .../dashboards/red-team/pentest-orchestrator.json  | 202 ----------
 6 files changed, 503 insertions(+), 202 deletions(-)
```
