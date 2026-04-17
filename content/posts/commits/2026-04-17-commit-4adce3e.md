---
title: "[bojemoi] feat: new components — c2-monitor, ptaas-init, postgres-ssl, RIPE import"
date: 2026-04-17T13:20:30+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit 4adce3e par Betty dans bojemoi"
author: "Betty"
---

## Commit `4adce3e`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `4adce3e1621ea335306353b5fda41d5cf24274d3` |


### Description

- ARCHITECTURE.md: full architecture document
- c2-monitor/: C2 session monitoring service
- ptaas-init/: PTaaS initialization service
- borodino/Dockerfile.postgres-ssl: postgres with SSL support
- volumes/postgres/: custom entrypoint + postgresql.conf
- scripts/import_ripe_cidrs.py: RIPE CIDR import tool
- stack/02-init-ptaas.yml: PTaaS init stack

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
A	ARCHITECTURE.md
A	borodino/Dockerfile.postgres-ssl
A	c2-monitor/Dockerfile
A	c2-monitor/monitor.py
A	c2-monitor/requirements.txt
A	ptaas-init/Dockerfile
A	ptaas-init/init.py
A	ptaas-init/requirements.txt
A	scripts/import_ripe_cidrs.py
A	stack/02-init-ptaas.yml
A	volumes/postgres/conf/pg_hba.conf
A	volumes/postgres/postgres-entrypoint.sh
```

### Diff Summary

```
 ARCHITECTURE.md                         | 319 ++++++++++++++++++++++++++++++++
 borodino/Dockerfile.postgres-ssl        |   6 +
 c2-monitor/Dockerfile                   |  10 +
 c2-monitor/monitor.py                   | 205 ++++++++++++++++++++
 c2-monitor/requirements.txt             |   4 +
 ptaas-init/Dockerfile                   |  12 ++
 ptaas-init/init.py                      | 241 ++++++++++++++++++++++++
 ptaas-init/requirements.txt             |   3 +
 scripts/import_ripe_cidrs.py            | 113 +++++++++++
 stack/02-init-ptaas.yml                 |  64 +++++++
 volumes/postgres/conf/pg_hba.conf       |  22 +++
 volumes/postgres/postgres-entrypoint.sh |  14 ++
 12 files changed, 1013 insertions(+)
```
