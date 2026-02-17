---
title: "[bojemoi-telegram] Add OSINT scan persistence, Cortex/MISP/MITRE integrations, and new stack config"
date: 2026-02-06T14:12:16+01:00
draft: false
tags: ["commit", "bojemoi-telegram", "feature", "stack"]
categories: ["Git Activity"]
summary: "Commit ea5561c par Betty — 12 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `ea5561c`

| | |
|---|---|
| **Repository** | bojemoi-telegram |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `ea5561c448e3efcee08658a1ab29ffc33d343dc8` |
| **Date** | 2026-02-06 |

### Description

Add OSINTScan model and CRUD operations for persisting scan results. Integrate
Cortex, MISP, and MITRE ATT&CK clients for enriched threat intelligence.
Expand osint module with comprehensive analysis capabilities. Replace old
docker-stack with new 60-service-telegram stack definition.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Fichiers modifiés

```
A	telegram/.env.example
M	telegram/database/__init__.py
M	telegram/database/crud.py
M	telegram/database/models.py
M	telegram/integrations/__init__.py
A	telegram/integrations/cortex.py
A	telegram/integrations/misp.py
A	telegram/integrations/mitre_attack.py
M	telegram/osint.py
M	telegram/requirements.txt
A	telegram/stack/60-service-telegram.yml
D	telegram/stack/docker-stack.yml
```

### Statistiques

```
 12 files changed, 2810 insertions(+), 53 deletions(-)
```
