---
title: "[bojemoi] borodino: add IPv6 support — ak47, bm12, uzi"
date: 2026-02-23T15:25:14+01:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit dc1cc3d par Betty dans bojemoi"
author: "Betty"
---

## Commit `dc1cc3d`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `dc1cc3dd1f188347076b568735ca4f63beacd072` |


### Description

- import_ipv6_cidrs.sh: new script to create ip2location_db1_v6 table
  and populate it from RIPE NCC delegated stats (curl -4, BEGIN/COMMIT batch)

- thearm_ak47: alternate 50/50 between ip2location_db1 (v4) and
  ip2location_db1_v6 (v6) each iteration, fallback on the other table
  if empty; detect IPv6 CIDR via ":" and pass -6 to db_nmap

- thearm_bm12: import ipaddress; filter fe80::/10 link-local addresses
  in TABLESAMPLE queries; detect IPv6 in build_nmap_command() and
  prepend -6 to db_nmap

- thearm_uzi: import ipaddress; filter fe80::/10 in get_random_host();
  wrap IPv6 addresses in brackets for Metasploit RHOSTS ([addr])

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
A	borodino/import_ipv6_cidrs.sh
M	borodino/thearm_ak47
M	borodino/thearm_bm12
M	borodino/thearm_uzi
```

### Diff Summary

```
 borodino/import_ipv6_cidrs.sh | 54 +++++++++++++++++++++++++++++++++++++++++++
 borodino/thearm_ak47          | 38 +++++++++++++++++++++++++-----
 borodino/thearm_bm12          | 17 +++++++++++---
 borodino/thearm_uzi           | 41 ++++++++++++++++++++++++++++----
 4 files changed, 136 insertions(+), 14 deletions(-)
```
