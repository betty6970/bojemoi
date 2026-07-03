---
title: "[borodino] feat(sliver): fix C2 callback pipeline — MTLS listener + Fly.io port 8888"
date: 2026-07-03T22:54:16+02:00
draft: false
tags: ["commit", "borodino", "main"]
categories: ["Git Activity"]
summary: "Commit ada7c7b par Claude Code dans borodino"
author: "Claude Code"
---

## Commit `ada7c7b`

| | |
|---|---|
| **Repository** | borodino |
| **Branch** | `main` |
| **Author** | Claude Code |
| **Hash** | `ada7c7bb240076e5a058ed20a1ab399587b40d2e` |


### Description

- sliver-entrypoint.sh: resolve LHOST from C2_REDIRECTORS (like UZI),
  start MTLS listener on :8888 after daemon ready, use C2_LHOST for implant generation
- stack: remove broken SLIVER_LHOST=sliver-server, add C2_REDIRECTORS env,
  port 8888 mode host→ingress, mount sliver-implants volume in sliver-worker
- redirector: add libnginx-mod-stream, nginx stream block TCP proxy :8888→sliver-server
  via VPN (SLIVER_VPN_IP=10.8.0.18), expose port 8888 in fly.toml

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	redirector/Dockerfile
M	redirector/entrypoint.sh
A	redirector/fly.toml
M	redirector/nginx.conf
M	sliver-entrypoint.sh
M	stack/40-service-borodino.yml
```

### Diff Summary

```
 redirector/Dockerfile         |  3 ++-
 redirector/entrypoint.sh      |  6 ++++--
 redirector/fly.toml           | 35 +++++++++++++++++++++++++++++++++++
 redirector/nginx.conf         | 11 +++++++++++
 sliver-entrypoint.sh          | 23 +++++++++++++++++++++--
 stack/40-service-borodino.yml |  6 ++++--
 6 files changed, 77 insertions(+), 7 deletions(-)
```
