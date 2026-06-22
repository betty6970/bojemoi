---
title: "[bojemoi] Push 2 commit(s) to main"
date: 2026-06-22T22:53:47+02:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 2 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 2 |
| **Pushed by** | Betty |

### Commits

- **baf6b82** feat: add arch-reviewer and sliver C2 worker (Betty)
- **02d406c** fix(uzi): corriger faux positifs http_login et creds non sauvegardés (Betty)


### Diff Summary

```
 arch-reviewer/Dockerfile             |  16 +
 arch-reviewer/arch_reviewer.py       | 377 ++++++++++++++++++++
 arch-reviewer/requirements.txt       |   2 +
 borodino/Dockerfile.borodino-sliver  |  27 ++
 borodino/Dockerfile.sliver-c2        |  28 ++
 borodino/sliver-entrypoint.sh        |  30 ++
 borodino/thearm_sliver/thearm_sliver | 671 +++++++++++++++++++++++++++++++++++
 borodino/thearm_uzi                  |  84 ++++-
 stack/40-service-borodino.yml        | 102 ++++++
 stack/72-service-arch-reviewer.yml   |  53 +++
 10 files changed, 1375 insertions(+), 15 deletions(-)
```
