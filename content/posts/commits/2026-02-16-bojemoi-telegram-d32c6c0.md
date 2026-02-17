---
title: "[bojemoi-telegram] Restore inline MITRE ATT&CK code and fix Dockerfile build"
date: 2026-02-16T18:43:39+01:00
draft: false
tags: ["commit", "bojemoi-telegram"]
categories: ["Git Activity"]
summary: "Commit d32c6c0 par Betty — 2 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `d32c6c0`

| | |
|---|---|
| **Repository** | bojemoi-telegram |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `d32c6c0fbe6d1d930a3f26a4c47b87c60bc08271` |
| **Date** | 2026-02-16 |

### Description

Remove broken COPY --from=mitre-attack dependency from Dockerfile and
restore the original inline MITRE ATT&CK implementation instead of
re-exports from the unavailable bojemoi-mitre-attack shared library.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Fichiers modifiés

```
M	telegram-bot/Dockerfile.telegram-bot
M	telegram-bot/integrations/mitre_attack.py
```

### Statistiques

```
 2 files changed, 640 insertions(+), 10 deletions(-)
```
