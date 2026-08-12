---
title: "[myai] fix(suricata): désactiver fast.log et stats.log — redondants avec eve.json"
date: 2026-08-13T00:41:09+02:00
draft: false
tags: ["commit", "myai", "main"]
categories: ["Git Activity"]
summary: "Commit eabdfd8 par grafana-watcher dans myai"
author: "grafana-watcher"
---

## Commit `eabdfd8`

| | |
|---|---|
| **Repository** | myai |
| **Branch** | `main` |
| **Author** | grafana-watcher |
| **Hash** | `eabdfd8b24986e24aa12a5871e60d220f786b71b` |


### Description

stats.log grossissait à 7.8 GB sans limite (pas de rotation native pour ce type
de log dans Suricata). fast.log et stats.log sont couverts par eve.json qui capture
déjà alerts et stats. eve-cleaner gère eve.json (seuil 5 GB).

Déployé Suricata sur meta-68 (manquant jusqu'ici).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	.claude/agent-memory/infra-daily-monitor/MEMORY.md
M	.claude/agent-memory/pipeline/MEMORY.md
M	volumes/suricata/suricata.yaml
```

### Diff Summary

```
 .claude/agent-memory/infra-daily-monitor/MEMORY.md | 117 +++++++++++++++------
 .claude/agent-memory/pipeline/MEMORY.md            |  48 +++++----
 volumes/suricata/suricata.yaml                     |   4 +-
 3 files changed, 112 insertions(+), 57 deletions(-)
```
