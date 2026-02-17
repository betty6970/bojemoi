---
title: "[bojemoi_ml-threat-intel] Increase OSINT fetch timeout to 30s and improve error logging"
date: 2026-02-10T15:28:20+01:00
draft: false
tags: ["commit", "bojemoi_ml-threat-intel"]
categories: ["Git Activity"]
summary: "Commit 21c975d par Betty — 1 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `21c975d`

| | |
|---|---|
| **Repository** | bojemoi_ml-threat-intel |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `21c975d17442ca3198f8eafccad780a51e217436` |
| **Date** | 2026-02-10 |

### Description

10s timeout caused all OSINT sources to fail from overlay network.
Added exc_info traceback to VirusTotal error logging for debugging.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Fichiers modifiés

```
M	feature_extractor.py
```

### Statistiques

```
 1 file changed, 5 insertions(+), 5 deletions(-)
```
