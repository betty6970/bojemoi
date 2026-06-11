---
title: "[bojemoi] fix(grafana): panneaux réseau par interface sur node_network_* au lieu de cAdvisor"
date: 2026-06-11T14:43:20+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit 03facaa par Betty dans bojemoi"
author: "Betty"
---

## Commit `03facaa`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `03facaa296fe26596ba9077bb7d5cfe45790922b` |


### Description

cAdvisor container_network_* n'expose pas tun0 ni les stats réelles du host.
Migration des panels 'Sent/Received Network Traffic par Interface' vers
node_network_transmit/receive_bytes_total avec filtre veth.*/lo/br-.*.
tun0, bond0, eth0, eth1, docker_gwbridge maintenant visibles.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	volumes/grafana/dashboards/general/docker-container-metrics.json
```

### Diff Summary

```
 .../dashboards/general/docker-container-metrics.json       | 14 +++++++-------
 1 file changed, 7 insertions(+), 7 deletions(-)
```
