---
title: "[bojemoi_ml-threat-intel] Fix deployment: Dockerfile reference, healthcheck, and DB connection"
date: 2026-02-09T20:16:11+01:00
draft: false
tags: ["commit", "bojemoi_ml-threat-intel", "fix"]
categories: ["Git Activity"]
summary: "Commit 1c2ac07 par Betty — 5 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `1c2ac07`

| | |
|---|---|
| **Repository** | bojemoi_ml-threat-intel |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `1c2ac077885865aa3d7afe31bc34835ec4ab1c10` |
| **Date** | 2026-02-09 |

### Description

- deploy.sh: use -f flag to reference Dockerfile.ml-threat
- Dockerfile: fix healthcheck to use GET instead of HEAD (--spider)
- Dockerfile: include pre-trained ML models in image
- api.py: inject DB_USER and DB_NAME from env vars in load_config()

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Fichiers modifiés

```
M	Dockerfile.ml-threat
M	api.py
M	deploy.sh
A	models/ioc_classifier.pkl
A	models/reputation_scorer.pkl
```

### Statistiques

```
 5 files changed, 7 insertions(+), 4 deletions(-)
```
