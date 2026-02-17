---
title: "[bojemoi-telegram] Fix registration confirmation to accept multiple responses"
date: 2026-01-28T14:55:09+01:00
draft: false
tags: ["commit", "bojemoi-telegram", "fix"]
categories: ["Git Activity"]
summary: "Commit e7333ad par Betty — 1 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `e7333ad`

| | |
|---|---|
| **Repository** | bojemoi-telegram |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `e7333adcda0e51684a14ed5362bb3aea90a445b9` |
| **Date** | 2026-01-28 |

### Description

Accept yes/y/ok/oui/o/да/si for confirm and no/n/non/restart/recommencer
for starting over, instead of requiring exact button text.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

### Fichiers modifiés

```
M	bot.py
```

### Statistiques

```
 1 file changed, 6 insertions(+), 3 deletions(-)
```
