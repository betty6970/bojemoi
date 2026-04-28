---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-04-28T16:34:51+02:00
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

- **c22ad9c** feat(borodino/orchestrator): host_debug host_id + post-exp Phase0 + LLM Ollama (Betty)


### Diff Summary

```
 ARCHITECTURE.md                                    |  15 ++
 borodino/thearm_uzi                                | 263 ++++++++++++++-------
 provisioning/cloud-init/alpine/database.yaml       |   9 +
 provisioning/cloud-init/alpine/minimal.yaml        |  15 ++
 provisioning/cloud-init/alpine/webserver.yaml      |   9 +
 provisioning/orchestrator/app/main.py              |  56 +++--
 provisioning/orchestrator/app/models/schemas.py    |  16 ++
 provisioning/orchestrator/app/services/database.py |  73 ++++--
 .../orchestrator/app/services/rapid7_manager.py    |  37 +--
 .../orchestrator/app/services/vulnhub_manager.py   |  28 ++-
 .../app/services/xenserver_client_real.py          |  84 ++++++-
 stack/40-service-borodino.yml                      |  39 +--
 12 files changed, 474 insertions(+), 170 deletions(-)
```
