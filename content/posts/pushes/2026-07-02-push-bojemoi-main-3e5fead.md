---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-07-02T19:21:34+02:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 1 commit(s) par grafana-watcher dans bojemoi/main"
author: "grafana-watcher"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 1 |
| **Pushed by** | grafana-watcher |

### Commits

- **3e5fead** refactor(mcp-server): migrate to bojemoi-sdk (grafana-watcher)


### Diff Summary

```
 mcp-server/Dockerfile          |   8 +-
 mcp-server/requirements.txt    |   3 -
 mcp-server/server.py           |  14 ++-
 mcp-server/tools/database.py   | 189 ----------------------------
 mcp-server/tools/defectdojo.py | 190 ----------------------------
 mcp-server/tools/metasploit.py | 272 -----------------------------------------
 mcp-server/tools/osint.py      | 140 ---------------------
 sdk/bojemoi/database.py        |   9 ++
 8 files changed, 25 insertions(+), 800 deletions(-)
```
