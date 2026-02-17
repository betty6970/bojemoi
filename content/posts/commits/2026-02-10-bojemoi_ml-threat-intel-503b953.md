---
title: "[bojemoi_ml-threat-intel] Add IP investigation pipeline with 4-phase analysis"
date: 2026-02-10T13:12:44+01:00
draft: false
tags: ["commit", "bojemoi_ml-threat-intel", "feature"]
categories: ["Git Activity"]
summary: "Commit 503b953 par Betty — 3 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `503b953`

| | |
|---|---|
| **Repository** | bojemoi_ml-threat-intel |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `503b953ad660fb98659014bd50c92b97b23542be` |
| **Date** | 2026-02-10 |

### Description

New POST /investigate/{ip} endpoint that runs a background pipeline:
validate (OSINT reputation check) -> surface mapping (Shodan + MSF DB
cross-ref) -> OSINT collection (VT/OTX deep extraction) -> correlation
(composite scoring with threat level and recommendation).

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Fichiers modifiés

```
M	api.py
M	database.py
A	investigator.py
```

### Statistiques

```
 3 files changed, 655 insertions(+), 2 deletions(-)
```
