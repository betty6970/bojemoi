---
title: "[myai] feat(exploit-memory): RAG + phi4 exploit generation (Option A+B)"
date: 2026-10-30T23:38:20+01:00
draft: false
tags: ["commit", "myai", "main"]
categories: ["Git Activity"]
summary: "Commit b7defce par Betty dans myai"
author: "Betty"
---

## Commit `b7defce`

| | |
|---|---|
| **Repository** | myai |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `b7defcebb7052c5d115cb4a2e1fb4964f1f210c5` |


### Description

- exploit_memory.py : nouvelle table pgvector (384 dims, ivfflat), fonctions
  store/recall/mark_tested/get_uncovered_cves
- campaign_executor._phase_exploit : flow RAG → MSF → phi4 génération
  - Étape 1 : recall_exploit (cosine ≥ 0.78) → exécute en kali, mémorise résultat
  - Étape 2 : plugins MSF statiques (inchangé)
  - Étape 3 : Option B — phi4 génère exploit Python → kali-exec-api → stocké tested=True
- Helpers : _recall_exploit_rag, _execute_in_kali (base64+proxy auto), _detect_success,
  _generate_exploit_phi4 (max 2 retries), _mark_exploit_tested, _store_generated_exploit
- main.py : init_exploit_memory_table() au démarrage + thread exploit-gen (Option A)
  Worker background : 1 exploit/30min pour les CVEs non couverts, phi4 via Ollama

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	app/campaign_executor.py
A	app/exploit_memory.py
M	app/main.py
```

### Diff Summary

```
 app/campaign_executor.py | 354 ++++++++++++++++++++++++++++++++++++++++-------
 app/exploit_memory.py    | 236 +++++++++++++++++++++++++++++++
 app/main.py              |  86 ++++++++++++
 3 files changed, 629 insertions(+), 47 deletions(-)
```
