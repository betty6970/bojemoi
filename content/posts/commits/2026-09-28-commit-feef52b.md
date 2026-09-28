---
title: "[borodino] fix(rag): corriger les noms de colonnes de la table attacks"
date: 2026-09-28T18:38:36+02:00
draft: false
tags: ["commit", "borodino", "main"]
categories: ["Git Activity"]
summary: "Commit feef52b par Claude Code dans borodino"
author: "Claude Code"
---

## Commit `feef52b`

| | |
|---|---|
| **Repository** | borodino |
| **Branch** | `main` |
| **Author** | Claude Code |
| **Hash** | `feef52b14faf05acf96caf3dbc8088752f9fa533` |


### Description

La table myai.attacks a objective/osint_profile/findings (pas hints).
Correction du parsing loop, de _text_for_attack et du query_rec
dans find_similar pour utiliser les bons noms de colonnes.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	rag_context.py
```

### Diff Summary

```
 rag_context.py | 55 ++++++++++++++++++++++++++++++++++++++-----------------
 1 file changed, 38 insertions(+), 17 deletions(-)
```
