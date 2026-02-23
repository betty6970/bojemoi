---
title: "[bojemoi] Push 3 commit(s) to main"
date: 2026-02-23T17:58:49+01:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 3 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 3 |
| **Pushed by** | Betty |

### Commits

- **a5d5aec** build: update BUILD_PROMPT.md (Betty)
- **729d1e3** orchestrator: add Rapid7 debug VM support, fix middleware lazy init (Betty)
- **41bed88** stack: add json-file logging (10m/3) to all services (Betty)


### Diff Summary

```
 BUILD_PROMPT.md                                    | 516 ++++++++++-----------
 borodino/.dockerignore                             |   2 -
 borodino/start_uzi.sh                              |   5 +
 provisioning/orchestrator/app/config.py            |   7 +
 provisioning/orchestrator/app/main.py              | 207 ++++++++-
 .../orchestrator/app/middleware/ip_validation.py   |   9 +-
 provisioning/orchestrator/app/models/schemas.py    |  76 +++
 stack/01-service-hl.yml                            | 106 ++++-
 stack/40-service-borodino.yml                      |  80 +++-
 stack/45-service-ml-threat-intel.yml               |   5 +
 stack/46-service-razvedka.yml                      |   5 +
 stack/47-service-vigie.yml                         |   5 +
 stack/65-service-medved.yml                        |   5 +
 volumes/suricata/suricata.yaml                     |   3 +-
 14 files changed, 730 insertions(+), 301 deletions(-)
```
