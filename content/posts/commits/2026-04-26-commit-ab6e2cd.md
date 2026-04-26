---
title: "[bojemoi] refactor(borodino): remplace MODE_RUN/SCAN_MODE/READ_MODE par MODE_DEBUG"
date: 2026-04-26T18:46:34+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit ab6e2cd par Betty dans bojemoi"
author: "Betty"
---

## Commit `ab6e2cd`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `ab6e2cd426781691cdc0d403b810c45684a23f75` |


### Description

Un seul env var MODE_DEBUG (bool, défaut false) remplace les trois variables :
- MODE_DEBUG=true  → lit host_debug, lecture séquentielle avec curseur+reset
- MODE_DEBUG=false → lit hosts, lecture aléatoire TABLESAMPLE SYSTEM(0.5)

Supprime le check MODE_RUN==1 redondant (exploits toujours actifs si payloads dispo).
Initialise MODE_DEBUG=false dans stack/40-service-borodino.yml.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	borodino/thearm_uzi
M	stack/40-service-borodino.yml
```

### Diff Summary

```
 borodino/thearm_uzi           | 96 ++++++++++++++++---------------------------
 stack/40-service-borodino.yml |  2 +-
 2 files changed, 36 insertions(+), 62 deletions(-)
```
