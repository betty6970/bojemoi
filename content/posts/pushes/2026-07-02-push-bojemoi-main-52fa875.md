---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-07-02T19:16:56+02:00
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

- **52fa875** feat(sdk): add bojemoi-sdk shared Python library (grafana-watcher)


### Diff Summary

```
 sdk/bojemoi/__init__.py                       |   3 +
 sdk/bojemoi/database.py                       | 168 +++++++
 sdk/bojemoi/defectdojo.py                     | 194 ++++++++
 sdk/bojemoi/metasploit.py                     | 250 ++++++++++
 sdk/bojemoi/osint.py                          | 137 ++++++
 sdk/bojemoi/pentest/__init__.py               |   1 +
 sdk/bojemoi/pentest/base.py                   | 655 ++++++++++++++++++++++++++
 sdk/bojemoi/pentest/campaign.py               | 153 ++++++
 sdk/bojemoi/pentest/dojo_pusher.py            |  88 ++++
 sdk/bojemoi/queue.py                          |  55 +++
 sdk/bojemoi/secrets.py                        |  18 +
 sdk/bojemoi/telegram.py                       |  76 +++
 sdk/bojemoi_sdk.egg-info/PKG-INFO             |  10 +
 sdk/bojemoi_sdk.egg-info/SOURCES.txt          |  18 +
 sdk/bojemoi_sdk.egg-info/dependency_links.txt |   1 +
 sdk/bojemoi_sdk.egg-info/requires.txt         |   5 +
 sdk/bojemoi_sdk.egg-info/top_level.txt        |   1 +
 sdk/pyproject.toml                            |  20 +
 18 files changed, 1853 insertions(+)
```
