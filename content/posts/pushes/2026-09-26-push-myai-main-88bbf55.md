---
title: "[myai] Push 1 commit(s) to main"
date: 2026-09-26T11:56:45+02:00
draft: false
tags: ["push", "myai", "main"]
categories: ["Git Activity"]
summary: "Push de 1 commit(s) par Betty dans myai/main"
author: "Betty"
---

## Push to `myai/main`

| | |
|---|---|
| **Repository** | myai |
| **Branch** | `main` |
| **Commits** | 1 |
| **Pushed by** | Betty |

### Commits

- **88bbf55** feat(myai): refactorer vers modèle plugin + intégration impacket SMB (Betty)


### Diff Summary

```
 app/attack_planner.py    |  16 +++--
 app/campaign_executor.py | 183 +++++++++++++++++------------------------------
 app/codegen.py           |   8 ++-
 app/plugin_base.py       |  91 +++++++++++++++++++++++
 app/plugins/impacket.py  |  81 +++++++++++++++++++++
 app/plugins/nuclei.py    |  54 ++++++++++++++
 app/plugins/sliver.py    |  50 +++++++++++++
 app/plugins/zap.py       |  49 +++++++++++++
 requirements.txt         |   1 +
 stack/myai.yml           |   6 +-
 10 files changed, 415 insertions(+), 124 deletions(-)
```
