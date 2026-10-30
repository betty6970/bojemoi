---
title: "[myai] fix(executor): augmenter ThreadPoolExecutor max_workers 4→16"
date: 2026-10-30T22:50:52+01:00
draft: false
tags: ["commit", "myai", "main"]
categories: ["Git Activity"]
summary: "Commit cbce5af par Betty dans myai"
author: "Betty"
---

## Commit `cbce5af`

| | |
|---|---|
| **Repository** | myai |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `cbce5afbbb15ccd2cc4d3a283d822f90d369bb4e` |


### Description

Pool global partagé saturé par LLM calls (30-60s chacun) → ops DB (<1ms)
bloquées → attacks restent status=pending indéfiniment → abort après 10 polls.
Toutes les ops sont I/O-bound (Ollama HTTP, psycopg2, subprocess).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	app/campaign_executor.py
```

### Diff Summary

```
 app/campaign_executor.py | 5 ++++-
 1 file changed, 4 insertions(+), 1 deletion(-)
```
