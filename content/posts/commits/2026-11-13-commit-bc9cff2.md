---
title: "[myai] refactor(judge): suppression complète du juge LLM qwen2.5:3b"
date: 2026-11-13T20:56:27+01:00
draft: false
tags: ["commit", "myai", "main"]
categories: ["Git Activity"]
summary: "Commit bc9cff2 par Betty dans myai"
author: "Betty"
---

## Commit `bc9cff2`

| | |
|---|---|
| **Repository** | myai |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `bc9cff29e84db898f32f0621a5eac2cc47412f58` |


### Description

qwen2.5:3b refusait systématiquement les outputs offensifs (EXPLOIT, modules MSF).
Tous les contextes (_generate_constrained + _validate_exploit_semantics) passent
désormais en validation syntaxique locale uniquement.

llm_judge.py supprimé. T400 exclusivement pour dojo-triage + alert-agent.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	app/attack_planner.py
M	app/campaign_executor.py
D	app/llm_judge.py
```

### Diff Summary

```
 app/attack_planner.py    |  54 ++++++++++--------------
 app/campaign_executor.py |  46 +++------------------
 app/llm_judge.py         | 105 -----------------------------------------------
 3 files changed, 27 insertions(+), 178 deletions(-)
```
