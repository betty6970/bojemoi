---
title: "[bojemoi] uzi: add reverse shell listener via bojemoi.me relay"
date: 2026-02-19T16:58:21+01:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit ac1bc9a par Betty dans bojemoi"
author: "Betty"
---

## Commit `ac1bc9a`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `ac1bc9a42204e527116c4bdd82e0f4fa9088567e` |


### Description

- Stack: 1 replica pinned to meta-68, port 4444 host mode, LHOST/LPORT env vars
- thearm_uzi: start multi/handler at boot (linux/x64/meterpreter/reverse_tcp)
- thearm_uzi: LHOST/LPORT from env, fix LHOST injection in exploit options
- Infra: autossh reverse tunnel meta-68 → bojemoi.me:4444 (GatewayPorts clientspecified)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	borodino/thearm_uzi
M	stack/40-service-borodino.yml
```

### Diff Summary

```
 borodino/thearm_uzi           | 37 +++++++++++++++++++++++--------------
 stack/40-service-borodino.yml | 31 +++++++++++++++++++++++++++++--
 2 files changed, 52 insertions(+), 16 deletions(-)
```
