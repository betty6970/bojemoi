---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-06-23T00:52:36+02:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 1 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 1 |
| **Pushed by** | Betty |

### Commits

- **2687fad** feat(borodino): migration redis→valkey + feeder Sliver dans uzi (Betty)


### Diff Summary

```
 borodino/Dockerfile.borodino         |  2 +-
 borodino/Dockerfile.borodino-msf     |  2 +-
 borodino/Dockerfile.borodino-sliver  |  2 +-
 borodino/sliver-entrypoint.sh        | 60 +++++++++++++++++++++++++++++----
 borodino/thearm_bm12                 | 18 +---------
 borodino/thearm_nuclei               |  2 +-
 borodino/thearm_sliver/thearm_sliver |  2 +-
 borodino/thearm_uzi                  | 65 ++++++++++++++++++++++++++++++++++++
 stack/40-service-borodino.yml        | 11 ++++++
 9 files changed, 136 insertions(+), 28 deletions(-)
```
