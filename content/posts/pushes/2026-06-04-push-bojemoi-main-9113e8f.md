---
title: "[bojemoi] Push 2 commit(s) to main"
date: 2026-06-04T08:07:18+02:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 2 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 2 |
| **Pushed by** | Betty |

### Commits

- **9113e8f** fix(cadvisor): allowlisted_container_labels → whitelisted_container_labels (Betty)
- **dd71731** feat(orchestrator): déploiement VM async avec job tracking (Betty)


### Diff Summary

```
 provisioning/orchestrator/app/main.py              | 136 +++++++++++++--------
 provisioning/orchestrator/app/models/schemas.py    |  23 ++++
 .../app/services/xenserver_client_real.py          |  77 ++++++++++--
 stack/01-service-hl.yml                            |   2 +-
 4 files changed, 181 insertions(+), 57 deletions(-)
```
