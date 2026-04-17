---
title: "[bojemoi] feat(packaging): package-dist.sh + Makefile + install/env fixes"
date: 2026-04-17T13:37:34+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit eb9a1ee par Betty dans bojemoi"
author: "Betty"
---

## Commit `eb9a1ee`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `eb9a1ee7a3e8e4ebd4fcc2eaed96bccb017bb639` |


### Description

- scripts/package-dist.sh: génère archive de distribution
  (.pyc only, stacks défensifs, Dockerfiles, configs, docs)
- Makefile: targets build/push/deploy/status/validate/clean/nodes
- install.sh: Faraday → DefectDojo, add dojo stack
- .env.example: Faraday → DefectDojo section

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	.env.example
A	Makefile
M	install.sh
A	scripts/package-dist.sh
```

### Diff Summary

```
 .env.example            |  18 +--
 Makefile                | 108 +++++++++++++++++
 install.sh              |  19 +--
 scripts/package-dist.sh | 305 ++++++++++++++++++++++++++++++++++++++++++++++++
 4 files changed, 432 insertions(+), 18 deletions(-)
```
