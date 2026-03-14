---
title: "[bojemoi] Push 2 commit(s) to main"
date: 2026-03-14T21:29:41+01:00
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

- **54cb79f** feat(sentinel): add MQTT broker + collector stack (Betty)
- **988b7d2** blog: add Alpine Linux post (FR + EN) (Betty)


### Diff Summary

```
 blog/choisir-alpine-linux-en.md     |  93 ++++++++++
 blog/choisir-alpine-linux-fr.md     |  93 ++++++++++
 sentinel/collector/Dockerfile       |   9 +
 sentinel/collector/collector.py     | 337 ++++++++++++++++++++++++++++++++++++
 sentinel/collector/requirements.txt |   3 +
 sentinel/esp32/sentinel_probe.ino   | 213 +++++++++++++++++++++++
 sentinel/mosquitto/mosquitto.conf   |  18 ++
 sentinel/setup.sh                   |  50 ++++++
 sentinel/sql/01-init-db.sql         |  28 +++
 sentinel/sql/02-tables.sql          |  93 ++++++++++
 sentinel/sql/03-grants.sql          |  18 ++
 sentinel/sql/apply.sh               |  45 +++++
 stack/55-service-sentinel.yml       | 140 +++++++++++++++
 13 files changed, 1140 insertions(+)
```
