---
title: "[bojemoi] feat(ak47): nmap local + msfrpc import via msf-teamserver (Option B)"
date: 2026-03-30T22:05:23+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit dc4caca par Betty dans bojemoi"
author: "Betty"
---

## Commit `dc4caca`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `dc4caca53147c67b9895a9badf7dcd262229b306` |


### Description

Replace msfconsole db_nmap with split approach:
- nmap -oX scan on ak47 (via ProtonVPN, no MSF required)
- msf_import.py: import XML via db.import_data msfrpc call
- Skip import if no hosts up (avoids RPC overhead for empty scans)
- Add msgpack to borodino:latest pip deps
- Add iproute2 + route-setup.sh to borodino-msf for uzi VPN routing
- Add MSF_HOST/MSF_PORT env vars to ak47-service

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	borodino/Dockerfile.borodino
A	borodino/msf_import.py
M	stack/40-service-borodino.yml
```

### Diff Summary

```
 borodino/Dockerfile.borodino  |  7 +++--
 borodino/msf_import.py        | 69 +++++++++++++++++++++++++++++++++++++++++++
 stack/40-service-borodino.yml |  2 ++
 3 files changed, 75 insertions(+), 3 deletions(-)
```
