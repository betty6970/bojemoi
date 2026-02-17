---
title: "[bojemoi-telegram] Add blockchain recording and Redis integration for pentest daemon"
date: 2026-01-31T20:19:28+01:00
draft: false
tags: ["commit", "bojemoi-telegram", "feature", "stack"]
categories: ["Git Activity"]
summary: "Commit 1987dfc par Betty — 10 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `1987dfc`

| | |
|---|---|
| **Repository** | bojemoi-telegram |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `1987dfc79c9841996a739596b04bc4e0eba2dadd` |
| **Date** | 2026-01-31 |

### Description

- Add blockchain module to record all Telegram updates as blocks
- Add Redis client for publishing scan commands and receiving results
- Add /chain and /verify commands for blockchain inspection
- Add Block model to database with hash verification
- Configure Redis connection for pentest-orchestrator communication
- Mount Docker socket for service status checks

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

### Fichiers modifiés

```
A	telegram/blockchain.py
M	telegram/bot.py
M	telegram/config.py
M	telegram/database/__init__.py
M	telegram/database/crud.py
M	telegram/database/models.py
M	telegram/docker-compose.yml
A	telegram/redis_client.py
M	telegram/requirements.txt
M	telegram/stack/docker-stack.yml
```

### Statistiques

```
 10 files changed, 791 insertions(+), 4 deletions(-)
```
