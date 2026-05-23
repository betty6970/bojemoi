---
title: "[bojemoi] feat(scripts): ajouter recreate_databases.sql — recréation idempotente des DBs"
date: 2026-05-23T19:13:20+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit f4ace2c par Betty dans bojemoi"
author: "Betty"
---

## Commit `f4ace2c`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `f4ace2cf88a07cabe617b5538d8993f80598c8bc` |


### Description

Liste toutes les bases du lab avec leur stack source.
ON_ERROR_STOP off = safe si les bases existent déjà.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
A	scripts/recreate_databases.sql
```

### Diff Summary

```
 scripts/recreate_databases.sql | 55 ++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 55 insertions(+)
```
