---
title: "[bojemoi] feat(borodino): filtre IP mobiles/résidentielles dans ak47 et bm12"
date: 2026-05-13T16:46:02+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit e64ebfc par Betty dans bojemoi"
author: "Betty"
---

## Commit `e64ebfc`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `e64ebfc87703cbde735ac9090493bb39ebc52538` |


### Description

- bm12 get_random_host(): exclut os_name IN ('Android', 'Android TV', 'Windows Phone')
  → 6 802 hosts mobiles/consumer ignorés pour le scan de services

- ak47: filtre CIDR via jointure sur asn_exclude_ranges (vue matérialisée)
  → exclut les plages appartenant à des ASN mobiles, résidentiels ou satellite

- DB ip2location: import DB-IP ASN Lite (469 777 entrées, CC BY 4.0)
  → tables asn_lite, asn_exclude (998 ASNs: 280 mobile + 689 résidentiel + 29 satellite)
  → vue matérialisée asn_exclude_ranges (12 683 ranges indexées)

- Ajout update-asn-db.sh : script de mise à jour mensuelle automatique

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	borodino/thearm_ak47
M	borodino/thearm_bm12
A	borodino/update-asn-db.sh
```

### Diff Summary

```
 borodino/thearm_ak47      | 11 +++++++--
 borodino/thearm_bm12      | 27 ++++++++++++++--------
 borodino/update-asn-db.sh | 57 +++++++++++++++++++++++++++++++++++++++++++++++
 3 files changed, 84 insertions(+), 11 deletions(-)
```
