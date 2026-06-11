---
title: "[bojemoi] feat(agents): infra-daily-monitor — actions correctives et proactives"
date: 2026-06-11T14:06:40+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit fc1cd7a par Betty dans bojemoi"
author: "Betty"
---

## Commit `fc1cd7a`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `fc1cd7aab0df09e88f9468b4bf3bd982330e4688` |


### Description

Phase 1 : checks complets (nodes, services, alertes, disque, MSF, VPN, Ollama)
Phase 2 : corrections automatiques (services down, labels manquants, Ollama tag, disk cleanup)
Phase 3 : mesures proactives (seuils disque, RAM, prometheus targets)
Actions manuelles signalées sans exécution (lab-tunnel, truncate eve.json, re-auth)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	.claude/agents/infra-daily-monitor.md
```

### Diff Summary

```
 .claude/agents/infra-daily-monitor.md | 331 ++++++++++++++++++++++------------
 1 file changed, 217 insertions(+), 114 deletions(-)
```
