---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-09-22T23:04:09+02:00
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

- **6c35e9f** feat(pentest-orchestrator): retirer auto-dispatch, seul qwen décide la suite (grafana-watcher)


### Diff Summary

```
 samsonov/pentest_orchestrator/Dockerfile           |  16 +
 samsonov/pentest_orchestrator/README.md            |  31 +
 samsonov/pentest_orchestrator/config/config.json   |  32 +
 .../pentest_orchestrator/cve_campaign_agent.py     | 549 ++++++++++++++++
 samsonov/pentest_orchestrator/cve_ip_matcher.py    | 668 ++++++++++++++++++++
 samsonov/pentest_orchestrator/feedback_loop.py     | 435 +++++++++++++
 samsonov/pentest_orchestrator/import_results.py    | 260 ++++++++
 samsonov/pentest_orchestrator/main.py              | 584 +++++++++++++++++
 samsonov/pentest_orchestrator/plugins/__init__.py  |  68 ++
 samsonov/pentest_orchestrator/plugins/base.py      | 655 +++++++++++++++++++
 .../pentest_orchestrator/plugins/plugin_masscan.py | 700 +++++++++++++++++++++
 .../plugins/plugin_metasploit.py                   | 409 ++++++++++++
 .../pentest_orchestrator/plugins/plugin_nuclei.py  | 372 +++++++++++
 .../pentest_orchestrator/plugins/plugin_vulnx.py   | 195 ++++++
 .../pentest_orchestrator/plugins/plugin_zap.py     | 302 +++++++++
 .../pentest_orchestrator/plugins/requirements.txt  |   1 +
 samsonov/pentest_orchestrator/results/.imported    |   9 +
 .../results/scan_20260131_163545.json              |  80 +++
 .../results/scan_20260131_202104.json              |  80 +++
 .../results/scan_20260202_181040.json              |  80 +++
 20 files changed, 5526 insertions(+)
```
