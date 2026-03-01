---
title: "[bojemoi] uzi: skip LHOST for bind payloads — only set on reverse payloads"
date: 2026-03-01T14:57:51+01:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit ecc2fa3 par Betty dans bojemoi"
author: "Betty"
---

## Commit `ecc2fa3`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `ecc2fa358aacd4166fe8b6c98dc03a491f73624a` |


### Description

Bind payloads (bind_tcp, bind_awk, bind_netcat, etc.) don't expose an
LHOST option; setting it caused KeyError spam on every attempt.
Guard the assignment with `if 'reverse' in payload`.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	borodino/thearm_uzi
```

### Diff Summary

```
 borodino/thearm_uzi | 3 ++-
 1 file changed, 2 insertions(+), 1 deletion(-)
```
