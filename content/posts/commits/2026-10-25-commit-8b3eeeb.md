---
title: "[bojemoi] feat(exploit): plugin php_uaf — CVE-2026-109618 PHP 8.3.x UAF OOM longjmp"
date: 2026-10-25T11:43:03+01:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit 8b3eeeb par grafana-watcher dans bojemoi"
author: "grafana-watcher"
---

## Commit `8b3eeeb`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | grafana-watcher |
| **Hash** | `8b3eeebe471d7545f13139b630b9edc3532fb968` |


### Description

Two-stage exploit basé sur blog.offensive32.com/@0xmsdbg :
- Stage 0 : probe PHP version (X-Powered-By) — skip si ≠ 8.3.x
- Stage 1 : 248 champs multipart filler_[i] × 65KB via raw socket
             → OOM → _zend_bailout() → dangling ptr sur rfc1867_progress
- Stage 2 : follow-up request → ZendMM LIFO bin réutilise adresse libérée
             → UAF zval → RCE tentée (détection via uid=/gid= dans réponse)

Activé par hints["cve_id"]="CVE-2026-109618" (depuis cve_triage pipeline).
Hot-reload automatique depuis /opt/bojemoi/volumes/myai-plugins/.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
A	volumes/myai-plugins/php_uaf.py
```

### Diff Summary

```
 volumes/myai-plugins/php_uaf.py | 336 ++++++++++++++++++++++++++++++++++++++++
 1 file changed, 336 insertions(+)
```
