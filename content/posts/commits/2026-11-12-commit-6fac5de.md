---
title: "[bojemoi] fix(kali/judge): correction LLM sur rejet judge au lieu de discard"
date: 2026-11-12T18:38:02+01:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit 6fac5de par grafana-watcher dans bojemoi"
author: "grafana-watcher"
---

## Commit `6fac5de`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | grafana-watcher |
| **Hash** | `6fac5dedbaaef929e80721152d7b4dd33a97fde8` |


### Description

Flow : judge(cmd) → NO → llm_fix(cmd) → judge(fixed) → YES → exécuter fixed
                                                        → NO → discard

- _judge_one() : valide + tente correction si rejeté
- _llm_fix_command() : prompt LLM pour corriger syntaxe/outils invalides
  (<<< → printf | tool, sshpass → ssh -o BatchMode, < file → inline)
- Fail-open si judge indisponible

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	volumes/myai-plugins/kali_exec.py
```

### Diff Summary

```
 volumes/myai-plugins/kali_exec.py | 102 ++++++++++++++++++++++++++++----------
 1 file changed, 77 insertions(+), 25 deletions(-)
```
