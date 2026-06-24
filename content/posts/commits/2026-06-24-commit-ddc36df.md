---
title: "[bojemoi] feat(orchestrator): add Telegram notifications for pwn and campaign completion"
date: 2026-06-24T21:35:14+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit ddc36df par Betty dans bojemoi"
author: "Betty"
---

## Commit `ddc36df`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `ddc36df09f77606245318d342e4ca211c03df87c` |


### Description

pentest-orchestrator is the single source of truth for campaign lifecycle —
workers are pure queue consumers. Move Telegram notifications here:
- Immediate alert on UZI pwn (send_telegram_pwned)
- Campaign summary on completion/timeout (send_telegram_campaign_done)
  with UZI/Nuclei/ZAP/Sliver results aggregated

Also mount telegram_bot_token + telegram_chat_id secrets on the service.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	samsonov/pentest_orchestrator/main.py
M	stack/40-service-borodino.yml
```

### Diff Summary

```
 samsonov/pentest_orchestrator/main.py | 53 +++++++++++++++++++++++++++++++++++
 stack/40-service-borodino.yml         |  2 ++
 2 files changed, 55 insertions(+)
```
