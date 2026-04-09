---
title: "[bojemoi] Push 2 commit(s) to main"
date: 2026-04-09T16:22:46+02:00
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

- **0e0519a** feat(uzi): brute-force credentials Phase 0 sur 15 services (Betty)
- **440a412** feat: make project distributable — templatize stacks + install wizard (Betty)


### Diff Summary

```
 .env.example                         | 224 +++++++++++++++++++
 .gitignore                           |   2 +
 README.md                            | 225 +++++++++++++++----
 borodino/thearm_uzi                  | 303 ++++++++++++++++++++++++-
 install.sh                           | 415 +++++++++++++++++++++++++++++++++++
 scripts/create-secrets.sh            | 212 ++++++++++++++++++
 stack/01-service-hl.yml              | 200 ++++++++---------
 stack/01-suricata-host.yml           |  18 +-
 stack/40-service-borodino.yml        | 241 ++++++++++++--------
 stack/45-service-ml-threat-intel.yml |   8 +-
 stack/46-service-razvedka.yml        |   4 +-
 stack/47-service-vigie.yml           |   4 +-
 stack/48-service-dozor.yml           |   6 +-
 stack/49-service-mcp.yml             |   2 +-
 stack/50-service-trivy.yml           |   2 +-
 stack/51-service-ollama.yml          |  40 +++-
 stack/55-service-sentinel.yml        |   4 +-
 stack/56-service-dvar.yml            |   4 +-
 stack/60-service-telegram.yml        |   4 +-
 stack/65-service-medved.yml          |   2 +-
 20 files changed, 1656 insertions(+), 264 deletions(-)
```
