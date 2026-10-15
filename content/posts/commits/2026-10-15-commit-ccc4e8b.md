---
title: "[myai] refactor(planner): simplify parse — full=prompt+raw suffit pour les deux backends"
date: 2026-10-15T19:44:47+02:00
draft: false
tags: ["commit", "myai", "main"]
categories: ["Git Activity"]
summary: "Commit ccc4e8b par Betty dans myai"
author: "Betty"
---

## Commit `ccc4e8b`

| | |
|---|---|
| **Repository** | myai |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `ccc4e8b91e064d8cd02f5b1f02473156ae3060a7` |


### Description

raw ⊆ full (raw est un suffixe de full), donc chercher dans raw d'abord
était redondant. reversed() sur les blobs garantit que le JSON généré
(en fin de full) est trouvé en premier.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	app/attack_planner.py
```

### Diff Summary

```
 app/attack_planner.py | 37 +++++++++++++++----------------------
 1 file changed, 15 insertions(+), 22 deletions(-)
```
