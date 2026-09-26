---
title: "[borodino] feat(sdk): ajouter impacket_tools — enum SMB + exec via smbexec/psexec"
date: 2026-09-26T11:56:54+02:00
draft: false
tags: ["commit", "borodino", "main"]
categories: ["Git Activity"]
summary: "Commit cd3aec4 par Claude Code dans borodino"
author: "Claude Code"
---

## Commit `cd3aec4`

| | |
|---|---|
| **Repository** | borodino |
| **Branch** | `main` |
| **Author** | Claude Code |
| **Hash** | `cd3aec4eb93e0065621dde258748d9bccd367ff1` |


### Description

smb_enumerate() : connexion anonyme, retourne os/domain/hostname/shares/anonymous_access
smb_exec() : smbexec puis psexec fallback, retourne outputs par commande

Import impacket lazy (try/except) — retourne error gracieux si non installé.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
A	sdk/bojemoi/pentest/impacket_tools.py
```

### Diff Summary

```
 sdk/bojemoi/pentest/impacket_tools.py | 219 ++++++++++++++++++++++++++++++++++
 1 file changed, 219 insertions(+)
```
