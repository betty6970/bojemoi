---
title: "[myai-orchestrator] fix(orchestrator): simplify clean_code() and increase MAX_NEW_TOKENS to 256"
date: 2026-08-14T18:38:41+02:00
draft: false
tags: ["commit", "myai-orchestrator", "main"]
categories: ["Git Activity"]
summary: "Commit a1f1eeb par Betty dans myai-orchestrator"
author: "Betty"
---

## Commit `a1f1eeb`

| | |
|---|---|
| **Repository** | myai-orchestrator |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `a1f1eeb136017425bcbd9cf0fb8b00feea4a5aff` |


### Description

clean_code() was too aggressive, stripping valid Python code by tracking
an in_code flag that could fail to trigger. New logic: extract from
markdown fences (regex), then find first import/from line and take
everything from there. Much simpler and more reliable.

MAX_NEW_TOKENS 128→256 to reduce truncation-induced SyntaxErrors.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	myai_orchestrator
M	stack/myai-orchestrator.yml
```

### Diff Summary

```
 myai_orchestrator           | 39 +++++++++++++++------------------------
 stack/myai-orchestrator.yml |  2 +-
 2 files changed, 16 insertions(+), 25 deletions(-)
```
