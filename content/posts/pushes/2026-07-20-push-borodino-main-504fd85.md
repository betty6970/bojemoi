---
title: "[borodino] Push 1 commit(s) to main"
date: 2026-07-20T16:58:17+02:00
draft: false
tags: ["push", "borodino", "main"]
categories: ["Git Activity"]
summary: "Push de 1 commit(s) par Claude Code dans borodino/main"
author: "Claude Code"
---

## Push to `borodino/main`

| | |
|---|---|
| **Repository** | borodino |
| **Branch** | `main` |
| **Commits** | 1 |
| **Pushed by** | Claude Code |

### Commits

- **504fd85** feat(campagne-nginx): campagne CVE-2026-42533 + misconfigs nginx (Claude Code)


### Diff Summary

```
 Dockerfile.borodino                                |   1 +
 .../cves/2026/cve-2026-42533-nginx.yaml            |  42 ++
 .../misconfigs/nginx/nginx-alias-traversal.yaml    |  36 ++
 .../misconfigs/nginx/nginx-crlf-injection.yaml     |  26 ++
 .../misconfigs/nginx/nginx-proxy-headers-ssrf.yaml |  43 +++
 .../misconfigs/nginx/nginx-stub-status.yaml        |  37 ++
 stack/40-service-borodino.yml                      |  30 ++
 thearm_campagne_nginx                              | 429 +++++++++++++++++++++
 8 files changed, 644 insertions(+)
```
