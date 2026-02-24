---
title: "[bojemoi] Push 8 commit(s) to main"
date: 2026-02-24T22:49:29+01:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 8 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 8 |
| **Pushed by** | Betty |

### Commits

- **636b468** gitignore: exclude blog-repo/ (nested git repo) (Betty)
- **393c5e7** blog,osint: add draft posts and OSINT report (Betty)
- **15c03a7** suricata: add classification.config (Betty)
- **c335d28** grafana: add MITRE ATT&CK attack heatmap dashboard (Betty)
- **b5dc6b3** orchestrator: add Rapid7 VM manager service (Betty)
- **23d6c54** scripts: add blog automation scripts (Betty)
- **7751c16** suricata-attack-enricher: add enricher service (Betty)
- **b64e232** mitre-attack: add bojemoi-mitre-attack library to all consumers (Betty)


### Diff Summary

```
 .gitignore                                         |   1 +
 ...Homelab Threat Intelligence Platform with ML.md | 291 ++++++++++++++++++
 blog/threat-intel-homelab-post-fr.md               | 305 +++++++++++++++++++
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
 osint-reports/progruzspb-ru-20260222.md            | 138 +++++++++
 .../orchestrator/app/services/rapid7_manager.py    | 115 ++++++++
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
 samsonov/bojemoi-mitre-attack/setup.py             |  10 +
 scripts/commits-to-posts.sh                        | 123 ++++++++
 scripts/post-commit-blog.sh                        | 110 +++++++
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
 .../bojemoi-mitre-attack/setup.py                  |  10 +
 suricata-attack-enricher/enricher.py               | 235 +++++++++++++++
 suricata-attack-enricher/requirements.txt          |   1 +
 .../provisioning/dashboards/attack-heatmap.json    | 277 ++++++++++++++++++
 volumes/suricata/config/classification.config      |  50 ++++
 50 files changed, 4010 insertions(+)
```
