---
title: "[bojemoi] feat(alert-agent): intégration Kimi K3 (Moonshot AI) comme backend LLM"
date: 2026-07-21T19:52:04+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit afd4b2c par grafana-watcher dans bojemoi"
author: "grafana-watcher"
---

## Commit `afd4b2c`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | grafana-watcher |
| **Hash** | `afd4b2c1c71b19410ef6f8402735f8f54c1bce94` |


### Description

Remplace Ollama (abandonné) par Kimi K3 via API Moonshot. Le backend
est configurable via LLM_BACKEND ("kimi" ou "ollama") sans rebuild.

- llm.py: refactor en _call_kimi/_call_ollama, dispatch selon config
- config.py: ajout kimi_api_key (secret), kimi_model, llm_backend
- stack: secret kimi_api_key monté, LLM_BACKEND=kimi par défaut
- fallback LLM unavailable → notify_only (au lieu de noop)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	alert-agent/alert_agent/__main__.py
M	alert-agent/alert_agent/config.py
M	alert-agent/alert_agent/llm.py
M	stack/48-service-alert-agent.yml
```

### Diff Summary

```
 alert-agent/alert_agent/__main__.py |  4 +--
 alert-agent/alert_agent/config.py   | 12 +++++++-
 alert-agent/alert_agent/llm.py      | 60 ++++++++++++++++++++++---------------
 stack/48-service-alert-agent.yml    |  5 ++++
 4 files changed, 54 insertions(+), 27 deletions(-)
```
