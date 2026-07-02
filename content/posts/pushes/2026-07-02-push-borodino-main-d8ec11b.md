---
title: "[borodino] Push 1 commit(s) to main"
date: 2026-07-02T19:55:55+02:00
draft: false
tags: ["push", "borodino", "main"]
categories: ["Git Activity"]
summary: "Push de 1 commit(s) par Claude Code dans borodino/main"
author: "Claude Code"
---

## Push to `borodino/main`

| | |
|---|---|
| **Repository** | borodino |
| **Branch** | `main` |
| **Commits** | 1 |
| **Pushed by** | Claude Code |

### Commits

- **d8ec11b** refactor(workers): migrate bm12, uzi, sliver to bojemoi-sdk (Claude Code)


### Diff Summary

```
 .gitignore                                    |   1 +
 Dockerfile.borodino                           |   3 +
 Dockerfile.borodino-msf                       |   3 +
 Dockerfile.borodino-sliver                    |   5 +-
 sdk/bojemoi/__init__.py                       |   3 +
 sdk/bojemoi/database.py                       | 177 +++++++
 sdk/bojemoi/defectdojo.py                     | 194 ++++++++
 sdk/bojemoi/metasploit.py                     | 250 ++++++++++
 sdk/bojemoi/osint.py                          | 137 ++++++
 sdk/bojemoi/pentest/__init__.py               |   1 +
 sdk/bojemoi/pentest/base.py                   | 655 ++++++++++++++++++++++++++
 sdk/bojemoi/pentest/campaign.py               | 153 ++++++
 sdk/bojemoi/pentest/dojo_pusher.py            |  88 ++++
 sdk/bojemoi/queue.py                          |  55 +++
 sdk/bojemoi/secrets.py                        |  18 +
 sdk/bojemoi/telegram.py                       |  76 +++
 sdk/bojemoi_sdk.egg-info/PKG-INFO             |  10 +
 sdk/bojemoi_sdk.egg-info/SOURCES.txt          |  18 +
 sdk/bojemoi_sdk.egg-info/dependency_links.txt |   1 +
 sdk/bojemoi_sdk.egg-info/requires.txt         |   5 +
 sdk/bojemoi_sdk.egg-info/top_level.txt        |   1 +
 sdk/pyproject.toml                            |  20 +
 thearm_bm12                                   |  28 +-
 thearm_sliver/thearm_sliver                   |  41 +-
 thearm_uzi                                    |  90 +---
 25 files changed, 1901 insertions(+), 132 deletions(-)
```
