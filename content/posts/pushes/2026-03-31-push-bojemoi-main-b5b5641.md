---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-03-31T20:36:25+02:00
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

- **b5b5641** feat(nuclei): Redis queue pipeline + dedicated Faraday workspaces + Redis Commander (Betty)


### Diff Summary

```
 borodino/Dockerfile.borodino                       |   6 +-
 borodino/redirector/Dockerfile                     |  18 +
 borodino/redirector/entrypoint.sh                  |  77 ++++
 borodino/redirector/nginx.conf                     |  63 ++++
 borodino/thearm_bm12                               |  23 +-
 borodino/thearm_logpull                            | 212 +++++++++++
 borodino/thearm_nuclei                             | 410 +++++++++++++++++++++
 samsonov/nuclei_api/main.py                        | 116 +++++-
 .../pentest_orchestrator/plugins/plugin_burp.py    | 326 ----------------
 .../pentest_orchestrator/plugins/plugin_nuclei.py  |  28 ++
 scripts/gameover.sh                                |  18 -
 scripts/stack_burp.export                          |  57 ---
 stack/40-service-borodino.yml                      | 139 ++++++-
 13 files changed, 1082 insertions(+), 411 deletions(-)
```
