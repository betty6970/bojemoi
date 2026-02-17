---
title: "[bojemoi_boot] Create overlay networks instead of external, externalize rsync secret"
date: 2026-02-06T14:12:19+01:00
draft: false
tags: ["commit", "bojemoi_boot", "stack"]
categories: ["Git Activity"]
summary: "Commit c9fcf47 par Betty — 2 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `c9fcf47`

| | |
|---|---|
| **Repository** | bojemoi_boot |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `c9fcf477628e1e21348407fbdea4812464e7c33f` |
| **Date** | 2026-02-06 |

### Description

Switch monitoring/backend/proxy networks from external to overlay with
attachable flag so boot stack can initialize them. Externalize rsync_config
secret with create-secrets.sh script.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Fichiers modifiés

```
A	scripts/create-secrets.sh
M	stack/01-boot-service.yml
```

### Statistiques

```
 2 files changed, 184 insertions(+), 5 deletions(-)
```
