---
title: "[borodino] Push 2 commit(s) to main"
date: 2026-07-04T00:48:02+02:00
draft: false
tags: ["push", "borodino", "main"]
categories: ["Git Activity"]
summary: "Push de 2 commit(s) par Claude Code dans borodino/main"
author: "Claude Code"
---

## Push to `borodino/main`

| | |
|---|---|
| **Repository** | borodino |
| **Branch** | `main` |
| **Commits** | 2 |
| **Pushed by** | Claude Code |

### Commits

- **cd6cc76** fix(sliver): C2 callback pipeline + implant generation workaround (Claude Code)
- **ada7c7b** feat(sliver): fix C2 callback pipeline — MTLS listener + Fly.io port 8888 (Claude Code)


### Diff Summary

```
 Dockerfile.sliver-c2          |  2 +-
 redirector/Dockerfile         |  3 ++-
 redirector/entrypoint.sh      |  6 +++--
 redirector/fly.toml           | 35 ++++++++++++++++++++++++++++
 redirector/nginx.conf         | 11 +++++++++
 sliver-entrypoint.sh          | 54 +++++++++++++++++++++++++++++++++++++++++--
 stack/40-service-borodino.yml |  6 +++--
 7 files changed, 109 insertions(+), 8 deletions(-)
```
