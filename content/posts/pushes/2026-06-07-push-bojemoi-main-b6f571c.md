---
title: "[bojemoi] Push 2 commit(s) to main"
date: 2026-06-07T23:31:47+02:00
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

- **b6f571c** feat(borodino): wordlists par pays dans UZI + colonne country dans bm12 (Betty)
- **614c27f** feat(grafana): Node Graph topology panel — tous les services Swarm avec indicateurs rouge/vert (Betty)


### Diff Summary

```
 borodino/thearm_bm12                               |   8 +-
 borodino/thearm_uzi                                |  73 +++++++++++--
 stack/01-service-hl.yml                            |   1 +
 .../dashboards/topology/service-topology.json      |  79 ++++++++++++++
 .../grafana/provisioning/dashboards/dashboards.yml |  20 ++++
 volumes/monitoring/swarm-exporter.py               | 121 ++++++++++++++++++++-
 6 files changed, 286 insertions(+), 16 deletions(-)
```
