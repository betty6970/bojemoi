---
title: "[bojemoi-telegram] Fix /register geo-restriction: allow French IPs instead of Russian"
date: 2026-02-15T22:36:44+01:00
draft: false
tags: ["commit", "bojemoi-telegram", "fix"]
categories: ["Git Activity"]
summary: "Commit 9950de2 par Betty — 1 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `9950de2`

| | |
|---|---|
| **Repository** | bojemoi-telegram |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `9950de2dcff5b5a39f067de1ff54ee6f1de128ef` |
| **Date** | 2026-02-15 |

### Description

The IP2LOCATION check was incorrectly restricting registration to
Russian IPs (RU) instead of French IPs (FR).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Fichiers modifiés

```
M	telegram/bot.py
```

### Statistiques

```
 1 file changed, 3 insertions(+), 3 deletions(-)
```
