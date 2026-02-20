---
title: "[bojemoi] Push 3 commit(s) to main"
date: 2026-02-20T16:39:48+01:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 3 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 3 |
| **Pushed by** | Betty |

### Commits

- **3c0dd23** suricata: rotate eve.json hourly, add eve-cleaner sidecar (24h retention) (Betty)
- **571da38** docker: fix compileall -b for importable .pyc without source (Betty)
- **a067c7e** docker: compile Python sources, add .dockerignore for sensitive files (Betty)


### Diff Summary

```
 borodino/.dockerignore                 |  7 +++++++
 dozor/.dockerignore                    |  7 +++++++
 dozor/Dockerfile.dozor                 |  4 ++++
 karacho/.dockerignore                  |  7 +++++++
 karacho/Dockerfile.karacho             | 10 ++++-----
 medved/.dockerignore                   |  7 +++++++
 medved/Dockerfile.medved               |  3 +++
 provisioning/.dockerignore             |  8 +++++++
 provisioning/Dockerfile.provisioning   |  5 +++--
 razvedka/.dockerignore                 |  7 +++++++
 razvedka/Dockerfile.razvedka           |  3 +++
 samsonov/.dockerignore                 |  7 +++++++
 stack/48-service-dozor.yml             | 38 ++++++++++++++++++++++++++++++++++
 suricata-attack-enricher/.dockerignore |  7 +++++++
 suricata-attack-enricher/Dockerfile    | 19 +++++++++++++++++
 vigie/.dockerignore                    |  7 +++++++
 vigie/Dockerfile.vigie                 |  4 ++++
 volumes/suricata/suricata.yaml         |  3 ++-
 18 files changed, 145 insertions(+), 8 deletions(-)
```
