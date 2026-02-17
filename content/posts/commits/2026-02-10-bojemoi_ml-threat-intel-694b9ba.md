---
title: "[bojemoi_ml-threat-intel] Add AI-powered threat correlation and report generation via Claude API"
date: 2026-02-10T14:55:33+01:00
draft: false
tags: ["commit", "bojemoi_ml-threat-intel", "feature"]
categories: ["Git Activity"]
summary: "Commit 694b9ba par Betty — 6 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `694b9ba`

| | |
|---|---|
| **Repository** | bojemoi_ml-threat-intel |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `694b9baa8fbf9818903cf7fe93920d7df8542abc` |
| **Date** | 2026-02-10 |

### Description

Replace Phase 4 rule-based scoring with LLM correlation (Claude API via aiohttp),
with automatic fallback to rule-based if AI unavailable. Add markdown report
generation for investigations.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Fichiers modifiés

```
M	.env.example
A	ai_agents.py
M	api.py
M	config/config.yaml
M	database.py
M	investigator.py
```

### Statistiques

```
 6 files changed, 326 insertions(+), 6 deletions(-)
```
