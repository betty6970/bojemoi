---
title: "[myai] fix(myai): msf_rpc_password secret + validation module LLM avant exécution"
date: 2026-10-15T20:52:54+02:00
draft: false
tags: ["commit", "myai", "main"]
categories: ["Git Activity"]
summary: "Commit ff73bae par Betty dans myai"
author: "Betty"
---

## Commit `ff73bae`

| | |
|---|---|
| **Repository** | myai |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `ff73baec036f7f154f8423ea6d8836b7217c6737` |


### Description

- Ajoute secret msf_rpc_password dans myai.yml (HTTP 401 MSF RPC)
- _validate_msf_module() existait mais n'était pas appelée dans decide_exploit
  → modules hallucinations Qwen3 (ex: auxiliary/scanner/webapp/craftcms_rce)
  causaient HTTP 500. Validation via msf_search() avant d'utiliser le module.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	app/attack_planner.py
M	stack/myai.yml
```

### Diff Summary

```
 app/attack_planner.py | 5 +++++
 stack/myai.yml        | 5 +++--
 2 files changed, 8 insertions(+), 2 deletions(-)
```
