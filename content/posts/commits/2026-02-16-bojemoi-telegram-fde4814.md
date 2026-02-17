---
title: "[bojemoi-telegram] Add geocoding validation for location field during registration"
date: 2026-02-16T18:29:35+01:00
draft: false
tags: ["commit", "bojemoi-telegram", "feature"]
categories: ["Git Activity"]
summary: "Commit fde4814 par Betty — 1 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `fde4814`

| | |
|---|---|
| **Repository** | bojemoi-telegram |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `fde4814818ef66d1655f720eb9c85826ba1e9330` |
| **Date** | 2026-02-16 |

### Description

Use Nominatim API to verify that the user-entered location is in France,
preventing false location entries. Unrecognized or non-FR locations are
rejected and the user is prompted to re-enter.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Fichiers modifiés

```
M	telegram-bot/bot.py
```

### Statistiques

```
 1 file changed, 39 insertions(+), 3 deletions(-)
```
