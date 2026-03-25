---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-03-25T22:44:39+01:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 1 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 1 |
| **Pushed by** | Betty |

### Commits

- **a79479d** feat: multi-stage Dockerfiles, DVAR IoT target, bm12/uzi ARM enrichment (Betty)


### Diff Summary

```
 .dockerignore                            |    1 +
 berezina/Dockerfile.berezina             |   73 +-
 borodino/.dockerignore                   |    1 +
 borodino/Dockerfile.berezina             |   29 +-
 borodino/Dockerfile.borodino             |   51 +-
 borodino/thearm_bm12                     |  151 ++++-
 borodino/thearm_uzi                      |  579 ++++++++++------
 borodino/toto                            | 1092 ++++++++++++++++++++++++++----
 discovery/Dockerfile                     |   27 +-
 discovery/breachforum_onion_discovery.py |  160 ++++-
 discovery/entrypoint.sh                  |    2 +-
 dvar/Dockerfile.dvar                     |   55 ++
 dvar/entrypoint.sh                       |   87 +++
 dvar/src/vuln_httpd.c                    |  194 ++++++
 koursk-2/Dockerfile.koursk-2             |    5 +
 koursk-2/scripts/rsync-start.sh          |    2 +-
 mcp-server/Dockerfile                    |    6 +-
 narva/Dockerfile.narva                   |   14 +-
 oblast/Dockerfile.zaproxy                |    7 +-
 scripts/cccp.sh                          |  173 +++--
 scripts/metasploitable2_exploit.py       |  388 +++++++++++
 scripts/startover.sh                     |    1 +
 sentinel/collector/Dockerfile            |    6 +-
 stack/40-service-borodino.yml            |   18 +-
 stack/56-service-dvar.yml                |   55 ++
 toto                                     |  945 ++++++++++++++++++++++++++
 tsushima/Dockerfile.tsushima             |   84 +--
 27 files changed, 3504 insertions(+), 702 deletions(-)
```
