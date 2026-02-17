---
title: "Fix slow queries and connection leaks in bm12 scanner"
date: 2026-02-07T21:55:45+01:00
draft: false
tags: ["commit", "bojemoi", "fix", "borodino"]
categories: ["Git Activity"]
summary: "Commit ecbf8c9 par Betty — 1 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `ecbf8c9`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `ecbf8c989b95587f9fd3ea691a263ab6ea972388` |
| **Date** | 2026-02-07 |

### Description

Replace ORDER BY RANDOM() with TABLESAMPLE SYSTEM() for host selection
and explicitly close DB connections to prevent idle-in-transaction buildup.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Fichiers modifiés

```
M	borodino/thearm_bm12
```

### Statistiques

```
 1 file changed, 20 insertions(+), 8 deletions(-)
```
