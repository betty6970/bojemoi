---
title: "[bojemoi] Push 1 commit(s) to main"
date: 2026-03-30T16:51:02+02:00
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

- **9eb4c92** feat(c2): multi-redirector infrastructure + split borodino images (Betty)


### Diff Summary

```
 borodino/Dockerfile.borodino             |  62 +---
 borodino/Dockerfile.borodino-msf         |  58 ++++
 borodino/start_msf_server.sh             |  51 +++
 borodino/start_uzi.sh                    |  68 ++--
 borodino/thearm_uzi                      |  84 ++++-
 cloud-init/redirector-template.yaml      | 317 ++++++++++++++++++
 discovery/Dockerfile                     |  35 --
 discovery/breachforum_discovery_api.py   | 259 ---------------
 discovery/breachforum_onion_discovery.py | 529 -------------------------------
 discovery/entrypoint.sh                  |  33 --
 redirector/Dockerfile                    |  33 ++
 redirector/c2-proxy.conf                 |  39 +++
 redirector/nginx.conf                    |  43 +++
 scripts/Dockerfile.discovery             |  34 --
 scripts/breachforum_discovery_api.py     | 259 ---------------
 scripts/breachforum_onion_discovery.py   | 421 ------------------------
 scripts/c2-manage.sh                     | 415 ++++++++++++++++++++++++
 scripts/c2-vpn-init-pki.sh               | 255 +++++++++++++++
 scripts/docker-compose.discovery.yml     |  99 ------
 scripts/provision-redirector.sh          |  91 ++++++
 stack/40-service-borodino.yml            |  76 ++++-
 stack/66-service-discovery.yml           |  73 -----
 volumes/c2-vpn/.gitignore                |   6 +
 volumes/c2-vpn/README.md                 |  46 +++
 24 files changed, 1559 insertions(+), 1827 deletions(-)
```
