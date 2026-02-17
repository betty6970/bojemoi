---
title: "[bojemoi-telegram] Refactor /register to generate all OSINT documents conditionally"
date: 2026-02-02T21:04:01+01:00
draft: false
tags: ["commit", "bojemoi-telegram", "refactor"]
categories: ["Git Activity"]
summary: "Commit c04a904 par Betty — 2 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `c04a904`

| | |
|---|---|
| **Repository** | bojemoi-telegram |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `c04a90416f49fa353d8662efa2cdf7beee1a726a` |
| **Date** | 2026-02-02 |

### Description

- Add PENTEST_THREAT_THRESHOLD config (default 50) to control scan launch
- /register now generates full OSINT report, Maltego export, and MITRE ATT&CK mapping
- Pentest scans only launch when threat_score >= threshold
- Remove scan storage in database for /osint and /domainlookup commands
- Remove obsolete commands: /osinthistory, /osintstats, /osintget, /osintsearch, /sendtomisp, /attackmap

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

### Fichiers modifiés

```
M	telegram/bot.py
M	telegram/config.py
```

### Statistiques

```
 2 files changed, 304 insertions(+), 19 deletions(-)
```
