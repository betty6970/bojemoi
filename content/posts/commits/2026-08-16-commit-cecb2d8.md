---
title: "[myai] refactor(codegen): put prompt as leading comment before context code"
date: 2026-08-16T14:53:11+02:00
draft: false
tags: ["commit", "myai", "main"]
categories: ["Git Activity"]
summary: "Commit cecb2d8 par Betty dans myai"
author: "Betty"
---

## Commit `cecb2d8`

| | |
|---|---|
| **Repository** | myai |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `cecb2d8a9c8954b035b28fac5fa61385b372ccf1` |


### Description

Prompt is now: # {user prompt}\n{imports + open call}
so the model sees the intent first, then code to continue.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	app/codegen.py
```

### Diff Summary

```
 app/codegen.py | 13 +++++++++----
 1 file changed, 9 insertions(+), 4 deletions(-)
```
