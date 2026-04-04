---
title: "[bojemoi] Push 2 commit(s) to main"
date: 2026-04-05T00:12:44+02:00
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

- **002f809** feat: uzi_scan_log + zap severity breakdown + nuclei [][]fix + eve-cleaner merge (Betty)
- **fb7c5ff** feat: Ollama AI template gen, C2 proxy_proto, ZAP throttle, vulnx removal (Betty)


### Diff Summary

```
 borodino/redirector/nginx.conf   |  12 +-
 borodino/thearm_logpull          |  24 ++--
 borodino/thearm_nuclei           |  82 ++++++++++-
 borodino/thearm_uzi              | 114 +++++++++++++--
 oblast-1/zap_scanner.py          | 118 +++++++++++++---
 samsonov/nuclei_api/main.py      | 111 +++++++++++++--
 samsonov/nuclei_api/nuclei_ai.py | 298 +++++++++++++++++++++++++++++++++++++++
 scripts/provision-redirector.sh  |   2 +-
 scripts/startover.sh             |   6 +
 stack/01-suricata-host.yml       |  21 ++-
 stack/40-service-borodino.yml    |  84 +++++------
 stack/48-service-dozor.yml       |  33 -----
 stack/51-service-ollama.yml      |   6 +-
 13 files changed, 763 insertions(+), 148 deletions(-)
```
