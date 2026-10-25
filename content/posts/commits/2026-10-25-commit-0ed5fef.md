---
title: "[bojemoi] fix(alloy): filtre discovery.docker via relabel keep plutôt que filtre API Docker"
date: 2026-10-25T20:55:03+01:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit 0ed5fef par grafana-watcher dans bojemoi"
author: "grafana-watcher"
---

## Commit `0ed5fef`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | grafana-watcher |
| **Hash** | `0ed5fef7682f63b116ab92c40f2c81a0c3ef3b8a` |


### Description

Le filtre API Docker avec regex multiples ne matche pas les containers
standalone (ex: wg-gateway). Migration vers keep relabel côté Alloy.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	volumes/alloy/config/config-worker.alloy
```

### Diff Summary

```
 volumes/alloy/config/config-worker.alloy | 13 ++++++++-----
 1 file changed, 8 insertions(+), 5 deletions(-)
```
