---
title: "[bojemoi] feat(grafana): refactorer dashboards pipeline + AK47/BM12"
date: 2026-09-27T13:30:17+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit aee0b2e par grafana-watcher dans bojemoi"
author: "grafana-watcher"
---

## Commit `aee0b2e`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | grafana-watcher |
| **Hash** | `aee0b2e3ebd252dc1256a52c4db16811d4749cfa` |


### Description

pipeline-overview:
- Supprimer toutes les références UZI (service retiré)
- Ajouter section Sliver (sliver_session_log) + Impacket (attacks.findings)
- Remplacer UZI dans entonnoir par Sliver sessions + Impacket findings

ak47-service: réécrire dashboard (total hosts, queue BM12, timeseries, OS distrib, now-7d)
bm12-service: réécrire dashboard (hosts traités, queue restante, services, bargauge, now-7d)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	volumes/grafana/dashboards/pentest/pipeline-overview.json
M	volumes/grafana/dashboards/red-team/ak47-service.json
M	volumes/grafana/dashboards/red-team/bm12-service.json
```

### Diff Summary

```
 .../dashboards/pentest/pipeline-overview.json      | 628 ++++++++++++++++-----
 .../grafana/dashboards/red-team/ak47-service.json  | 203 +++----
 .../grafana/dashboards/red-team/bm12-service.json  | 207 +++----
 3 files changed, 632 insertions(+), 406 deletions(-)
```
