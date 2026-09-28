---
title: "[borodino] feat(dispatcher): host priority scoring + RAG context from past attacks"
date: 2026-09-28T17:33:22+02:00
draft: false
tags: ["commit", "borodino", "main"]
categories: ["Git Activity"]
summary: "Commit b9ca2ac par Claude Code dans borodino"
author: "Claude Code"
---

## Commit `b9ca2ac`

| | |
|---|---|
| **Repository** | borodino |
| **Branch** | `main` |
| **Author** | Claude Code |
| **Hash** | `b9ca2aced6f3002641a10affdbf7c4fff718a54b` |


### Description

- host_scorer.py: heuristic scoring 0-100 (type, attack_surface, CVEs,
  threat_score, arch, confidence) — pure Python, no extra deps
- rag_context.py: MiniLM + Faiss IndexFlatIP, loads 500 past completed
  attacks, find_similar() returns top-3 (cosine > 0.5 threshold)
- campaign_dispatcher: LIMIT 1→20, picks best scored host, injects
  rag_context into hints before /attack (fully non-blocking)
- Dockerfile.borodino: sentence-transformers + faiss-cpu + scikit-learn
  added with || true (graceful fallback on Alpine without C compiler)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	Dockerfile.borodino
M	campaign_dispatcher.py
A	host_scorer.py
A	rag_context.py
```

### Diff Summary

```
 Dockerfile.borodino    |  14 ++++
 campaign_dispatcher.py |  37 ++++++++--
 host_scorer.py         | 133 ++++++++++++++++++++++++++++++++++++
 rag_context.py         | 178 +++++++++++++++++++++++++++++++++++++++++++++++++
 4 files changed, 358 insertions(+), 4 deletions(-)
```
