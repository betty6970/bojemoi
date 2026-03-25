---
title: "[bojemoi] fix(orchestrator): use docker-socket-proxy instead of direct socket"
date: 2026-03-25T23:19:08+01:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit d3bbec7 par Betty dans bojemoi"
author: "Betty"
---

## Commit `d3bbec7`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `d3bbec7b84da8e313944c74b1f56efe8c9822820` |


### Description

- Remove /var/run/docker.sock bind mount from orchestrator service
  (was failing with PermissionError since container now runs non-root)
- Add DOCKER_SWARM_URL=tcp://docker-socket-proxy:2375 env var
- Enable POST=1 DELETE=1 on boot/docker-socket-proxy (needed for
  service create/delete via orchestrator API)
- Fix config mode 0440→0444 so non-root appuser can read .env config

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	stack/01-service-hl.yml
```

### Diff Summary

```
 stack/01-service-hl.yml | 7 +++----
 1 file changed, 3 insertions(+), 4 deletions(-)
```
