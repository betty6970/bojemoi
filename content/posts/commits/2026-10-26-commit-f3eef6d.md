---
title: "[myai] fix(cve-triage): advisory lock PG + timeout LLM 60s"
date: 2026-10-26T19:54:09+01:00
draft: false
tags: ["commit", "myai", "main"]
categories: ["Git Activity"]
summary: "Commit f3eef6d par Betty dans myai"
author: "Betty"
---

## Commit `f3eef6d`

| | |
|---|---|
| **Repository** | myai |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `f3eef6dca0ecd7bd982e8f69421f5d97f30ae67a` |


### Description

- pg_try_advisory_lock(424242) : un seul replica exécute le triage
  (avec 2 replicas, les deux appelaient phi4 en simultané → timeout 30s)
- Timeout LLM 30s → 60s (phi4 peut être occupé par attack pipeline)
- Import db._connect/_POSTGRES_DB en tête de fichier

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	app/cve_triage.py
```

### Diff Summary

```
 app/cve_triage.py | 32 +++++++++++++++++++++++++++++++-
 1 file changed, 31 insertions(+), 1 deletion(-)
```
