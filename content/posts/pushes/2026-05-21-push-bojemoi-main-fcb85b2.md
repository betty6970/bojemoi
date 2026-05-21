---
title: "[bojemoi] Push 12 commit(s) to main"
date: 2026-05-21T13:14:32+02:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 12 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 12 |
| **Pushed by** | Betty |

### Commits

- **fcb85b2** feat(borodino): ajout stack borodino-msf + attente teamserver au démarrage (Betty)
- **0cfce58** fix(monitoring): suricata-exporter rejoint le réseau overlay monitoring (Betty)
- **ae80893** docs(borodino): clarifier les Dockerfiles — quelle image pour quel service (Betty)
- **18c4f4c** feat(uzi): ajout check honeypot/redirector_hits avant lancement exploits (Betty)
- **4a61175** fix(nuclei): rendre redirector_hits non-fatal dans is_honeypot_suspect (Betty)
- **028ab74** fix(bm12): remplacer msfconsole/db_nmap par nmap direct + parsing XML (Betty)
- **9d5307c** feat(toolbox): container outil Alpine+Python connecté à tous les networks et secrets (Betty)
- **19a2864** fix(ollama): KEEP_ALIVE=-1 pour garder mistral chargé en VRAM (Betty)
- **8a5e8c3** fix(gameover): préserver les volumes permanents au teardown (Betty)
- **0228c7a** fix(db): créer nuclei_scan_log et redirector_hits dans msf (Betty)
- **9d35be3** fix(nuclei): activer Ollama + timeout 60s dans nuclei-worker (Betty)
- **ff8708a** fix(alloy): contraindre alloy sur le manager (node.role == manager) (Betty)


### Diff Summary

```
 .claude/commands/pipeline.md                       | 270 +++++++++++++++++++++
 borodino/Dockerfile.borodino                       |   5 +-
 borodino/Dockerfile.borodino-msf                   |   6 +-
 borodino/thearm_bm12                               | 181 +++++++++++---
 borodino/thearm_nuclei                             |  17 +-
 borodino/thearm_uzi                                |  36 +++
 scripts/gameover.sh                                |  33 ++-
 scripts/startover.sh                               |  18 +-
 stack/01-service-hl.yml                            |   3 +
 stack/01-suricata-host.yml                         |   8 +-
 stack/39-service-borodino-msf.yml                  |  83 +++++++
 stack/40-service-borodino.yml                      |   2 +-
 stack/46-service-razvedka.yml                      |   4 -
 stack/51-service-ollama.yml                        |   1 +
 stack/98-service-toolbox.yml                       | 142 +++++++++++
 toolbox/Dockerfile                                 |  41 ++++
 volumes/alloy/config/config.alloy                  |   2 +-
 .../dashboards/pentest/pipeline-overview.json      | 134 +++++-----
 volumes/postgres/init/03-msf-custom-tables.sql     |  50 ++++
 19 files changed, 913 insertions(+), 123 deletions(-)
```
