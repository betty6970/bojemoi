---
title: "[myai] fix(api): charger les trophées dans GET /attack/{id}"
date: 2026-09-26T21:59:14+02:00
draft: false
tags: ["commit", "myai", "main"]
categories: ["Git Activity"]
summary: "Commit d15baed par Betty dans myai"
author: "Betty"
---

## Commit `d15baed`

| | |
|---|---|
| **Repository** | myai |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `d15baed11c29a9cacc4e15649707c92ca95aaf39` |


### Description

_attack_row_to_response ne peuplait pas le champ trophies.
Fetch list_trophies(attack_id) dans attack_get() et injection
via _trophy_row_to_model.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	app/main.py
```

### Diff Summary

```
 app/main.py | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)
```
