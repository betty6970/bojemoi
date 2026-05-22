---
title: "[bojemoi] feat(alert-agent): activer le mode production et corriger le DNS du socket proxy"
date: 2026-05-22T13:16:12+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit cef2abc par Betty dans bojemoi"
author: "Betty"
---

## Commit `cef2abc`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `cef2abc75ee4c36a3530014ea822d8cc24fc0229` |


### Description

- DRY_RUN false → exécution réelle des actions correctives
- DOCKER_SOCKET_PROXY_URL : docker-socket-proxy → boot_docker-socket-proxy (nom DNS Swarm correct)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	stack/48-service-alert-agent.yml
```

### Diff Summary

```
 stack/48-service-alert-agent.yml | 4 ++--
 1 file changed, 2 insertions(+), 2 deletions(-)
```
