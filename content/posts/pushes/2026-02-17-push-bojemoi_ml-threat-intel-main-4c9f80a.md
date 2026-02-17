---
title: "[bojemoi_ml-threat-intel] Push 1 commit(s) to main"
date: 2026-02-17T14:32:12+01:00
draft: false
tags: ["push", "bojemoi_ml-threat-intel", "main"]
categories: ["Git Activity"]
summary: "Push de 1 commit(s) par Betty dans bojemoi_ml-threat-intel/main"
author: "Betty"
---

## Push to `bojemoi_ml-threat-intel/main`

| | |
|---|---|
| **Repository** | bojemoi_ml-threat-intel |
| **Branch** | `main` |
| **Commits** | 1 |
| **Pushed by** | Betty |

### Commits

- **4c9f80a** Cleanup test posts (Betty)


### Diff Summary

```
 Dockerfile.ml-threat                               |   4 +
 api.py                                             |  49 ++++
 .../bojemoi_mitre_attack.egg-info/PKG-INFO         |   7 +
 .../bojemoi_mitre_attack.egg-info/SOURCES.txt      |  13 +
 .../dependency_links.txt                           |   1 +
 .../bojemoi_mitre_attack.egg-info/top_level.txt    |   1 +
 .../bojemoi_mitre_attack/__init__.py               |  23 ++
 .../bojemoi_mitre_attack/formatters.py             | 136 +++++++++
 .../bojemoi_mitre_attack/mapper.py                 | 324 +++++++++++++++++++++
 .../bojemoi_mitre_attack/mappings/__init__.py      |  11 +
 .../bojemoi_mitre_attack/mappings/osint.py         |  54 ++++
 .../bojemoi_mitre_attack/mappings/suricata.py      |  99 +++++++
 .../bojemoi_mitre_attack/mappings/vulnerability.py |  73 +++++
 .../bojemoi_mitre_attack/models.py                 |  36 +++
 bojemoi-mitre-attack/setup.py                      |  10 +
 database.py                                        |  35 +++
 investigator.py                                    |  23 ++
 17 files changed, 899 insertions(+)
```
