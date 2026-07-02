---
title: "[bojemoi] refactor(mcp-server): migrate to bojemoi-sdk"
date: 2026-07-02T19:21:34+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit 3e5fead par grafana-watcher dans bojemoi"
author: "grafana-watcher"
---

## Commit `3e5fead`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | grafana-watcher |
| **Hash** | `3e5fead99aa32edb67bb520bc491237d0bca0ecd` |


### Description

Replace local tools/{database,metasploit,defectdojo,osint}.py with
imports from the shared bojemoi-sdk package.

Changes:
- server.py: import from bojemoi.* instead of tools.*
  - sync defectdojo calls wrapped with asyncio.to_thread
  - tools/nmap kept local (nmap-specific, not in SDK)
- Dockerfile: build context now /opt/bojemoi/ (repo root),
  installs sdk/ before service requirements
- requirements.txt: remove deps covered by SDK (psycopg2, httpx, msgpack)
- tools/{database,metasploit,defectdojo,osint}.py: deleted
- sdk/bojemoi/database.py: add get_target_profile() (was missing)

Build command: docker build --no-cache -f mcp-server/Dockerfile -t localhost:5000/bojemoi-mcp:latest .

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	mcp-server/Dockerfile
M	mcp-server/requirements.txt
M	mcp-server/server.py
D	mcp-server/tools/database.py
D	mcp-server/tools/defectdojo.py
D	mcp-server/tools/metasploit.py
D	mcp-server/tools/osint.py
M	sdk/bojemoi/database.py
```

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
