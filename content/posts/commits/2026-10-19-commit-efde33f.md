---
title: "[borodino] fix(wg-gateway): add bridge network for internet access"
date: 2026-10-19T16:00:19+02:00
draft: false
tags: ["commit", "borodino", "main"]
categories: ["Git Activity"]
summary: "Commit efde33f par Claude Code dans borodino"
author: "Claude Code"
---

## Commit `efde33f`

| | |
|---|---|
| **Repository** | borodino |
| **Branch** | `main` |
| **Author** | Claude Code |
| **Hash** | `efde33f16980ae75e017254417a3d5cab8abe1a1` |


### Description

Container was only on borodino_scan_net overlay (no internet route).
OpenVPN could not connect to ProtonVPN servers → nuclei had 0 findings.

Changes:
- Add 'internet' bridge network so container can reach ProtonVPN
- Update scan_net IP: 10.0.6.10 → 10.0.9.10 (subnet changed 2026-10-14)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	wg-gateway/docker-compose.yml
```

### Diff Summary

```
 wg-gateway/docker-compose.yml | 9 ++++++---
 1 file changed, 6 insertions(+), 3 deletions(-)
```
