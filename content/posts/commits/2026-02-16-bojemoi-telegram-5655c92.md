---
title: "[bojemoi-telegram] Fix telegram bot: add mitre-attack library and make Redis non-fatal"
date: 2026-02-16T15:03:06+01:00
draft: false
tags: ["commit", "bojemoi-telegram", "fix"]
categories: ["Git Activity"]
summary: "Commit 5655c92 par Betty — 42 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `5655c92`

| | |
|---|---|
| **Repository** | bojemoi-telegram |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `5655c9272c174c47fb8942da9c450973c9f27f03` |
| **Date** | 2026-02-16 |

### Description

- Rename telegram/ to telegram-bot/ for clarity
- Add bojemoi-mitre-attack to Dockerfile via named build context
- Make Redis subscriber connection non-fatal so bot starts without Redis
- Update deploy.sh with --build-context flag

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>

### Fichiers modifiés

```
A	telegram-bot/.env.example
A	telegram-bot/Dockerfile.telegram-bot
A	telegram-bot/blockchain.py
A	telegram-bot/bot.py
A	telegram-bot/config.py
A	telegram-bot/database/__init__.py
A	telegram-bot/database/connection.py
A	telegram-bot/database/crud.py
A	telegram-bot/database/models.py
A	telegram-bot/deploy.sh
A	telegram-bot/docker-compose.yml
A	telegram-bot/init_db.py
A	telegram-bot/integrations/__init__.py
A	telegram-bot/integrations/cortex.py
A	telegram-bot/integrations/maltego.py
A	telegram-bot/integrations/misp.py
A	telegram-bot/integrations/mitre_attack.py
A	telegram-bot/integrations/thehive.py
A	telegram-bot/osint.py
A	telegram-bot/redis_client.py
A	telegram-bot/requirements.txt
D	telegram/.env.example
D	telegram/Dockerfile.telegram
D	telegram/blockchain.py
D	telegram/bot.py
D	telegram/config.py
D	telegram/database/__init__.py
D	telegram/database/connection.py
D	telegram/database/crud.py
D	telegram/database/models.py
D	telegram/deploy.sh
D	telegram/docker-compose.yml
D	telegram/init_db.py
D	telegram/integrations/__init__.py
D	telegram/integrations/cortex.py
D	telegram/integrations/maltego.py
D	telegram/integrations/misp.py
D	telegram/integrations/mitre_attack.py
D	telegram/integrations/thehive.py
D	telegram/osint.py
D	telegram/redis_client.py
D	telegram/requirements.txt
```

### Statistiques

```
 42 files changed, 6372 insertions(+), 6363 deletions(-)
```
