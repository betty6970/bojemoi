---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-05-21T23:25:51+02:00
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

- **9293f7c** refactor: supprimer Faraday legacy et renommer faraday-triage → dojo-triage (Betty)


### Diff Summary

```
 .claude/commands/faraday.md                        |  65 ----
 {faraday-triage => dojo-triage}/Dockerfile         |   0
 {faraday-triage => dojo-triage}/requirements.txt   |   0
 {faraday-triage => dojo-triage}/triage.py          |   0
 .../faraday-security-stack_legacy/.dockerignore    |  52 ---
 samsonov/faraday-security-stack_legacy/.gitignore  |  81 -----
 .../faraday-security-stack_legacy/CONTRIBUTING.md  | 122 -------
 .../INSTALLATION_ET_UTILISATION.txt                | 243 -------------
 samsonov/faraday-security-stack_legacy/LICENSE     |  50 ---
 samsonov/faraday-security-stack_legacy/Makefile    | 154 --------
 .../faraday-security-stack_legacy/QUICKSTART.md    | 185 ----------
 samsonov/faraday-security-stack_legacy/README.md   | 402 ---------------------
 .../configs/nginx/nginx.conf                       |  91 -----
 .../docker-compose.override.yml.example            |  44 ---
 .../docker-compose.yml                             |  78 ----
 samsonov/faraday-security-stack_legacy/examples.sh | 283 ---------------
 samsonov/faraday-security-stack_legacy/install.sh  | 281 --------------
 .../faraday-security-stack_legacy/requirements.txt |  20 -
 .../scripts/masscan_to_faraday.py                  | 187 ----------
 .../scripts/msf_to_faraday.py                      | 251 -------------
 .../scripts/orchestrator.sh                        | 291 ---------------
 .../scripts/zap/configure_zap.py                   | 139 -------
 .../scripts/zap_to_faraday.py                      | 211 -----------
 samsonov/faraday-security-stack_legacy/test.sh     | 157 --------
 volumes/faraday/config/server.ini                  |  17 -
 volumes/faraday/server.ini                         |  26 --
 wiki/Faraday.md                                    |   5 -
 27 files changed, 3435 deletions(-)
```
