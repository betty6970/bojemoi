---
title: "[bojemoi] Push 3 commit(s) to main"
date: 2026-03-18T13:52:16+01:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 3 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 3 |
| **Pushed by** | Betty |

### Commits

- **fced696** chore: add Discord bot scaffold + breachforum discovery scripts (Betty)
- **1041a8b** blog: add alertmanager Docker secrets post (FR) (Betty)
- **b93e503** feat(borodino/uzi): auto-detect LHOST, split LPORT_BIND, improve exploit targeting (Betty)


### Diff Summary

```
 blog/alertmanager-docker-secrets-fr.md | 174 +++++++++++
 borodino/thearm_uzi                    |  53 +++-
 discord/.env.example                   |  17 ++
 discord/create_structure.sh            |  68 +++++
 discord/structure.yml                  |  38 +++
 scripts/Dockerfile.discovery           |  34 +++
 scripts/INTEGRATION_GUIDE.sh           | 205 +++++++++++++
 scripts/README.md                      | 540 +++++++++++++++++++++++++++++++++
 scripts/breachforum_discovery_api.py   | 259 ++++++++++++++++
 scripts/breachforum_onion_discovery.py | 421 +++++++++++++++++++++++++
 scripts/docker-compose.discovery.yml   |  99 ++++++
 scripts/examples_usage.py              | 301 ++++++++++++++++++
 stack/40-service-borodino.yml          |   5 +-
 13 files changed, 2202 insertions(+), 12 deletions(-)
```
