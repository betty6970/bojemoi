---
title: "[bojemoi] feat(grafana): campaign-dispatcher dashboard — remplace pentest-orchestrator"
date: 2026-10-04T21:00:26+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit afbed36 par grafana-watcher dans bojemoi"
author: "grafana-watcher"
---

## Commit `afbed36`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | grafana-watcher |
| **Hash** | `afbed368b96cced7f4ef867b77a881e2e128ba93` |


### Description

Services (Prometheus), stats campagnes + activité (pg-myai), logs (Loki).
Supprime l'ancien dashboard AK47/BM12/UZI devenu obsolète.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
A	volumes/grafana/dashboards/red-team/campaign-dispatcher.json
D	volumes/grafana/dashboards/red-team/pentest-orchestrator.json
```

### Diff Summary

```
 .../dashboards/red-team/campaign-dispatcher.json   |  31 ++++
 .../dashboards/red-team/pentest-orchestrator.json  | 202 ---------------------
 2 files changed, 31 insertions(+), 202 deletions(-)
```
