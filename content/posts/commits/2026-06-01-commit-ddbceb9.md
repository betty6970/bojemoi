---
title: "[bojemoi_boot] refactor(boot): ajouter telegram_net + 14 configs depuis stack base"
date: 2026-06-01T16:10:59+02:00
draft: false
tags: ["commit", "bojemoi_boot", "main"]
categories: ["Git Activity"]
summary: "Commit ddbceb9 par Betty dans bojemoi_boot"
author: "Betty"
---

## Commit `ddbceb9`

| | |
|---|---|
| **Repository** | bojemoi_boot |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `ddbceb9ae2ca642a28734e8ae235882415099264` |


### Description

- networks: ajoute telegram_net (overlay, name: telegram_telegram_net)
- configs: migre 14 entrées depuis 01-service-hl.yml (alertmanager, prometheus,
  loki, tempo, alloy, grafana-ini, grafana-datasources, grafana-dashboards-provider,
  postfix, provisioning_env, postgres_init_sql, rsync_rsyncd, rsync_jobs,
  tls_alertmanager_config) — boot est désormais la source unique des configs

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	stack/01-boot-service.yml
```

### Diff Summary

```
 stack/01-boot-service.yml | 179 +++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 168 insertions(+), 11 deletions(-)
```
