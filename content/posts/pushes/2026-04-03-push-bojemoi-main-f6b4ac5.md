---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-04-03T16:11:02+02:00
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

- **f6b4ac5** feat: Ollama/Mistral local inference + remove Burp Suite + C2 listener auto-start (Betty)


### Diff Summary

```
 .claude/commands/pentest.md                      |  2 +-
 borodino/start_msf_server.sh                     | 25 +++++++-
 borodino/thearm_ak47                             |  7 +-
 oblast-1/zap_scanner.py                          | 81 +++++++++++++++++++-----
 samsonov/pentest_orchestrator/config/config.json |  7 +-
 samsonov/pentest_orchestrator/main.py            |  4 +-
 scripts/provision-redirector.sh                  | 27 +++++++-
 scripts/test_wget.sh                             |  2 -
 stack/01-service-hl.yml                          |  5 +-
 stack/45-service-ml-threat-intel.yml             |  5 +-
 stack/51-service-ollama.yml                      | 51 +++++++++++++++
 stack/READ.me                                    |  2 +-
 wiki/Pentest-Orchestrator.md                     |  1 -
 13 files changed, 179 insertions(+), 40 deletions(-)
```
