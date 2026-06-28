---
title: "[bojemoi] fix(nuclei): parse bm12_v3 scan_details for tag enrichment"
date: 2026-06-28T22:07:08+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit b5e2adf par Betty dans bojemoi"
author: "Betty"
---

## Commit `b5e2adf`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `b5e2adf36483327dd35f9f3557ea24f354f9c629` |


### Description

extract_tags() was silently returning 'cve' for all hosts because:
1. products field is a list of dicts {"name": ..., "version": ...}
   but code called .lower() directly on the dict → AttributeError
2. evidence field (bm12_v3 format) was not parsed at all

Fix: read tags from evidence dict (service lists like ["ssh:22", "http:80"]),
primary_role, and legacy products — handling both dict and string formats.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	borodino/thearm_nuclei
```

### Diff Summary

```
 borodino/thearm_nuclei | 39 ++++++++++++++++++++++++++++++++++-----
 1 file changed, 34 insertions(+), 5 deletions(-)
```
