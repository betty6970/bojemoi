---
title: "[bojemoi] Push 2 commit(s) to main"
date: 2026-05-31T21:03:30+02:00
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

- **5d3d6c9** fix(grafana): refactore Services Status en 4 panels catégorisés (Betty)
- **f23efeb** fix(maintenance): docker-cleanup utilise le registry local (Betty)


### Diff Summary

```
 stack/02-service-maintenance.yml                   |   2 +-
 .../grafana/dashboards/pentest/c2-sessions.json    |  47 ++-
 .../dashboards/pentest/pentest-overview.json       | 451 ++++++++++++++++++---
 .../dashboards/pentest/pipeline-overview.json      | 144 +++----
 .../grafana/dashboards/pentest/scan-results.json   |  84 +++-
 .../dashboards/pentest/vuln-management.json        | 113 +++---
 6 files changed, 629 insertions(+), 212 deletions(-)
```
