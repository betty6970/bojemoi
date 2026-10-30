---
title: "[borodino] fix(dojo-triage): router qwen2.5:3b vers ollama-judge (T400)"
date: 2026-10-30T22:35:03+01:00
draft: false
tags: ["commit", "borodino", "main"]
categories: ["Git Activity"]
summary: "Commit a1b2aec par Claude Code dans borodino"
author: "Claude Code"
---

## Commit `a1b2aec`

| | |
|---|---|
| **Repository** | borodino |
| **Branch** | `main` |
| **Author** | Claude Code |
| **Hash** | `a1b2aec1bacfd693377f4f9be32ba32b5f1c1d10` |


### Description

dojo-triage pointait sur ollama_ollama (RTX 3060) avec qwen2.5:3b,
chargeant inutilement 1.5 GB sur la RTX 3060 déjà à 91%.
Redirigé vers ollama_ollama-judge (T400) dédié à ce modèle.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	stack/40-service-borodino.yml
```

### Diff Summary

```
 stack/40-service-borodino.yml | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```
