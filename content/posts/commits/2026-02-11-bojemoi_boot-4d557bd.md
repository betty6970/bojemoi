---
title: "[bojemoi_boot] Fix Traefik prometheus.port label: 8082 -> 8085"
date: 2026-02-11T19:04:21+01:00
draft: false
tags: ["commit", "bojemoi_boot", "fix", "stack"]
categories: ["Git Activity"]
summary: "Commit 4d557bd par Betty — 1 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `4d557bd`

| | |
|---|---|
| **Repository** | bojemoi_boot |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `4d557bda8f1c78530c5cd3da327423ce53ccc5de` |
| **Date** | 2026-02-11 |

### Description

Traefik exposes metrics on entryPoint 'metrics' at port 8085,
not 8082. This caused 4 PrometheusTargetDown alerts.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Fichiers modifiés

```
M	stack/01-boot-service.yml
```

### Statistiques

```
 1 file changed, 1 insertion(+), 1 deletion(-)
```
