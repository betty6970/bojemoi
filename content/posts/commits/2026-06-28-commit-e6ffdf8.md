---
title: "[bojemoi] fix(dojo): add found_by=[1] to all finding POSTs"
date: 2026-06-28T22:28:25+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit e6ffdf8 par Betty dans bojemoi"
author: "Betty"
---

## Commit `e6ffdf8`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `e6ffdf8a7590ef8c9e95b9154a8437235b289242` |


### Description

DefectDojo API requires the found_by field (list of test type IDs).
Missing field was causing 400 Bad Request on all findings POSTs from
the dojo_worker_loop (ZAP, UZI, Sliver, aggregate findings).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	samsonov/pentest_orchestrator/main.py
```

### Diff Summary

```
 samsonov/pentest_orchestrator/main.py | 4 ++++
 1 file changed, 4 insertions(+)
```
