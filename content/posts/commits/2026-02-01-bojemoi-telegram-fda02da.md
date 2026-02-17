---
title: "[bojemoi-telegram] Add comprehensive OSINT module with Maltego and TheHive integrations"
date: 2026-02-01T23:06:43+01:00
draft: false
tags: ["commit", "bojemoi-telegram", "feature"]
categories: ["Git Activity"]
summary: "Commit fda02da par Betty — 6 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `fda02da`

| | |
|---|---|
| **Repository** | bojemoi-telegram |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `fda02da9136b3c0eddf75792ac15f5743f357bf2` |
| **Date** | 2026-02-01 |

### Description

Features:
- Multi-source OSINT gathering (IP-API, IPInfo, ipwhois, ThreatCrowd, AlienVault)
- Optional Shodan, VirusTotal, AbuseIPDB support (API keys)
- Automatic threat scoring (0-100) with risk levels
- Proxy/VPN/Tor/hosting detection
- Maltego export (MTGX, CSV, JSON formats)
- TheHive integration (alerts, cases, observables)
- New commands: /osint <ip>, /maltego [format]

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

### Fichiers modifiés

```
M	telegram/bot.py
M	telegram/config.py
A	telegram/integrations/__init__.py
A	telegram/integrations/maltego.py
A	telegram/integrations/thehive.py
A	telegram/osint.py
```

### Statistiques

```
 6 files changed, 1996 insertions(+), 9 deletions(-)
```
