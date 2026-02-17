---
title: "[bojemoi-telegram] Refactor MITRE ATT&CK to shared library and remove stack config"
date: 2026-02-15T22:37:23+01:00
draft: false
tags: ["commit", "bojemoi-telegram", "refactor", "stack"]
categories: ["Git Activity"]
summary: "Commit b723c96 par Betty — 2 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `b723c96`

| | |
|---|---|
| **Repository** | bojemoi-telegram |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `b723c968559901a05a9cdcbe8fab353669797cd9` |
| **Date** | 2026-02-15 |

### Description

Replace inline MITRE ATT&CK implementation with re-exports from the
bojemoi-mitre-attack shared library. Remove 60-service-telegram.yml
stack config (managed elsewhere).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Fichiers modifiés

```
M	telegram/integrations/mitre_attack.py
D	telegram/stack/60-service-telegram.yml
```

### Statistiques

```
 2 files changed, 6 insertions(+), 694 deletions(-)
```
