---
title: "[bojemoi] suricata: fix filetype rotating -> regular, update eve-cleaner to size-based truncation"
date: 2026-02-21T17:57:48+01:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit 21aeedf par Betty dans bojemoi"
author: "Betty"
---

## Commit `21aeedf`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `21aeedf94885178bcc296daf4aa748cc264f8723` |


### Description

Suricata 8.0.3 does not support filetype: rotating. Revert to regular filetype.
eve-cleaner now truncates files by size (eve.json > 5G, fast/stats.log > 500M)
instead of deleting rotated files that never existed.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	stack/01-suricata-host.yml
```

### Diff Summary

```
 stack/01-suricata-host.yml | 8 ++++----
 1 file changed, 4 insertions(+), 4 deletions(-)
```
