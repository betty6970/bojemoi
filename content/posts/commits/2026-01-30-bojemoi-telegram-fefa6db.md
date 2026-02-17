---
title: "[bojemoi-telegram] Add IP2LOCATION verification to restrict registration to Russian IPs"
date: 2026-01-30T22:41:47+01:00
draft: false
tags: ["commit", "bojemoi-telegram", "feature"]
categories: ["Git Activity"]
summary: "Commit fefa6db par Betty — 4 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `fefa6db`

| | |
|---|---|
| **Repository** | bojemoi-telegram |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `fefa6db6488aacb66c816c2d42df4ad927f1a777` |
| **Date** | 2026-01-30 |

### Description

Query the ip2location database (ip2location_db1 table) during registration
to verify IP addresses. Only allow registration for IPs from Russia (RU),
reject all others or unverifiable IPs.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

### Fichiers modifiés

```
M	telegram/bot.py
M	telegram/config.py
M	telegram/database/connection.py
M	telegram/database/crud.py
```

### Statistiques

```
 4 files changed, 49 insertions(+), 21 deletions(-)
```
