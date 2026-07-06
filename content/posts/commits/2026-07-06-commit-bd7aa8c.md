---
title: "[borodino] fix(bm12): fix nmap service import — schema + service_count always updated"
date: 2026-07-06T17:03:12+02:00
draft: false
tags: ["commit", "borodino", "main"]
categories: ["Git Activity"]
summary: "Commit bd7aa8c par Claude Code dans borodino"
author: "Claude Code"
---

## Commit `bd7aa8c`

| | |
|---|---|
| **Repository** | borodino |
| **Branch** | `main` |
| **Author** | Claude Code |
| **Hash** | `bd7aa8c29edf03c8669aed94370c653ca44a64dd` |


### Description

thearm_bm12:
- ON CONFLICT (host_id, port, proto) → services table has UNIQUE on 5 cols
  → remplacé par UPDATE + INSERT séparés (pas de conflit de schéma)
- service_count recalculé TOUJOURS après scan nmap (même si 0 services upsertés)
  → corrige service_count=0 quand ProtonVPN est bloqué par cible mais masscan
     avait déjà trouvé les services

wg-gateway-start.sh:
- tun-mtu reste 1500 dans le protocole OpenVPN (stabilité tunnel)
- MTU OS réduit à 1400 via ip link (double encapsulation VXLAN/OpenVPN)

Résultat: 81.27.51.123 → service_count=6, os_name='Linux 2.6.32' ✅

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	thearm_bm12
M	wg-gateway-start.sh
```

### Diff Summary

```
 thearm_bm12         | 30 ++++++++++++++++++------------
 wg-gateway-start.sh |  5 +++++
 2 files changed, 23 insertions(+), 12 deletions(-)
```
