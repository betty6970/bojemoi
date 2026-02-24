---
title: "[bojemoi] protonmail-bridge: fix libfido2, add auto-login via secrets"
date: 2026-02-24T13:33:54+01:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit cfe9eaf par Betty dans bojemoi"
author: "Betty"
---

## Commit `cfe9eaf`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `cfe9eafa51768b67d15c13ba486c61d2391da2e3` |


### Description

- Add libfido2-1 and expect to image (bridge v3.22.0 requires libfido2)
- Replace entrypoint with auto-login script using Docker secrets
  (proton_username, proton_password) via expect CLI automation
- GPG key + pass store initialized on first run from /root volume
- Mount proton_username and proton_password secrets in stack service

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
A	Dockerfile.protonmail-bridge
A	entrypoint-protonmail.sh
M	stack/01-service-hl.yml
```

### Diff Summary

```
 Dockerfile.protonmail-bridge |  8 ++++++
 entrypoint-protonmail.sh     | 62 ++++++++++++++++++++++++++++++++++++++++++++
 stack/01-service-hl.yml      |  3 +++
 3 files changed, 73 insertions(+)
```
