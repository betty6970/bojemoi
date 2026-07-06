---
title: "[borodino] fix(ak47): scan direct sans VPN + patch wg-gateway up/down scripts"
date: 2026-07-06T23:22:46+02:00
draft: false
tags: ["commit", "borodino", "main"]
categories: ["Git Activity"]
summary: "Commit df7eedf par Claude Code dans borodino"
author: "Claude Code"
---

## Commit `df7eedf`

| | |
|---|---|
| **Repository** | borodino |
| **Branch** | `main` |
| **Author** | Claude Code |
| **Hash** | `df7eedf761a4efa8b8f3487e6b0dcd14a316fae1` |


### Description

- ak47: retire SCAN_GATEWAY_HOST et route-setup.sh wrapper
  nmap -sS (raw socket) incompatible avec NAT ProtonVPN — les SYN-ACK
  retournent sur l'IP VPN sans session établie → 0 hosts up permanent
  Solution: scan direct depuis l'IP du lab, VPN reste pour bm12/uzi

- wg-gateway: filtre directives 'up' et 'down' du profil ovpn
  Le profil NL référençait /etc/openvpn/update-resolv-conf absent

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	stack/40-service-borodino.yml
M	wg-gateway-start.sh
```

### Diff Summary

```
 stack/40-service-borodino.yml | 3 +--
 wg-gateway-start.sh           | 2 +-
 2 files changed, 2 insertions(+), 3 deletions(-)
```
