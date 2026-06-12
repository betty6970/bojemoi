---
title: "[bojemoi] perf(ollama): phi3:mini + timeout 120s pour réduire les timeouts nuclei"
date: 2026-06-12T18:34:35+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit 8bacfe3 par Betty dans bojemoi"
author: "Betty"
---

## Commit `8bacfe3`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `8bacfe371259bdf8e1876574227621fc72b573a3` |


### Description

- OLLAMA_MODEL: mistral:latest (4.4GB) → phi3:mini (2.2GB)
  Libère ~1.3GB VRAM sur T400 4GB, élimine le CPU overflow llama-server
- OLLAMA_TIMEOUT: 60 → 120s sur nuclei-worker et nuclei-api
- Services concernés: nuclei-worker, nuclei-api, dojo-triage

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	stack/40-service-borodino.yml
```

### Diff Summary

```
 stack/40-service-borodino.yml | 8 ++++----
 1 file changed, 4 insertions(+), 4 deletions(-)
```
