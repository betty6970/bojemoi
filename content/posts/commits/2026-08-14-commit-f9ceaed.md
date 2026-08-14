---
title: "[myai] feat(myai): switch to Qwen2.5-Coder-1.5B (local GPU, ~30s/64tok)"
date: 2026-08-14T23:27:43+02:00
draft: false
tags: ["commit", "myai", "HEAD"]
categories: ["Git Activity"]
summary: "Commit f9ceaed par Betty dans myai"
author: "Betty"
---

## Commit `f9ceaed`

| | |
|---|---|
| **Repository** | myai |
| **Branch** | `HEAD` |
| **Author** | Betty |
| **Hash** | `f9ceaed06aefb446d434b571caed20d7ba355f3b` |


### Description

Replace StarCoder2-3B with Qwen/Qwen2.5-Coder-1.5B:
- 1.5B params → ~3GB float16 → fits entirely in T400 4GB VRAM
- No CPU offloading → ~30s/64tok vs 3-7min before
- safetensors format → compatible with PyTorch 2.2 + transformers 4.57
- Not gated → no HF token needed for download

Removed hf_token secret dependency, restored GPU placement constraint,
adjusted resource limits to 2CPU/3G RAM.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	app/codegen.py
```

### Diff Summary

```
 app/codegen.py | 2 ++
 1 file changed, 2 insertions(+)
```
