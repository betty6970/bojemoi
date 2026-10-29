---
title: "[myai] fix(report): deduplicate findings by (source, title) before DefectDojo push"
date: 2026-10-29T18:24:19+01:00
draft: false
tags: ["commit", "myai", "main"]
categories: ["Git Activity"]
summary: "Commit 74aacbf par Betty dans myai"
author: "Betty"
---

## Commit `74aacbf`

| | |
|---|---|
| **Repository** | myai |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `74aacbf1aaf50186e07892dedea6bbeaf612dd61` |


### Description

ZAP generates dozens of identical alerts per crawled page (e.g.
"Timestamp Disclosure - Unix" x50, "X-Content-Type-Options" x12).
Dedup keeps the first occurrence per (source, title) pair.
86 findings → ~12 unique for a typical ZAP scan.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	app/campaign_executor.py
```

### Diff Summary

```
 app/campaign_executor.py | 14 ++++++++++++++
 1 file changed, 14 insertions(+)
```
