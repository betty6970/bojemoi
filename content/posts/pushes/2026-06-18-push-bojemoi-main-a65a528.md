---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-06-18T22:59:29+02:00
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

- **a65a528** fix(pipeline): nuclei timeout, MCP StreamableHTTP, UZI payload & target filtering (Betty)


### Diff Summary

```
 .claude/agent-memory/infra-daily-monitor/MEMORY.md | 64 ++++++++++++++++++++--
 .claude/agent-memory/pipeline/MEMORY.md            | 45 ++++++++++-----
 .mcp.json                                          |  4 +-
 alert-agent/alert_agent/webhook.py                 | 10 ++--
 borodino/thearm_uzi                                |  8 ++-
 mcp-server/server.py                               | 49 +++++++++--------
 samsonov/nuclei_api/main.py                        | 12 ++--
 stack/40-service-borodino.yml                      |  4 +-
 volumes/prometheus/rules/alert_rules.yml           | 10 ----
 9 files changed, 143 insertions(+), 63 deletions(-)
```
