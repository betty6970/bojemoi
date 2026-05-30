---
title: "[bojemoi] fix(maintenance): docker-cleanup utilise le registry local"
date: 2026-05-30T23:47:10+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit f23efeb par Betty dans bojemoi"
author: "Betty"
---

## Commit `f23efeb`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `f23efeb8024aebbed127ce8e4177d76a5c0ec6f4` |


### Description

docker:27-cli (Docker Hub) remplacé par localhost:5000/docker:27-cli
pour éviter l'échec sur meta-68 qui n'a pas accès à Docker Hub.

Co-Authored-By: Claude Sonnet 4.6 (1M context) <noreply@anthropic.com>

### Files Changed

```
M	stack/02-service-maintenance.yml
```

### Diff Summary

```
 stack/02-service-maintenance.yml | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```
