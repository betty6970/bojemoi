---
title: "[bojemoi] feat: Ollama AI template gen, C2 proxy_proto, ZAP throttle, vulnx removal"
date: 2026-04-04T00:23:54+02:00
draft: false
tags: ["commit", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Commit fb7c5ff par Betty dans bojemoi"
author: "Betty"
---

## Commit `fb7c5ff`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `fb7c5ffb383f76bef73929f3d716a83cbf252e23` |


### Description

Ollama × Nuclei AI (option 1):
- nuclei_ai.py: NucleiAI class with suggest_tags(), analyze_findings(),
  generate_templates() (up to 2 custom YAML templates per scan context)
- main.py: scan_details field in ScanRequest, AI template pre-scan pass,
  merge results, pyyaml added to pip install
- thearm_nuclei: enrich_tags() via Ollama, submit_scan() passes scan_details
- 51-service-ollama.yml: placement via node.labels.nvidia.vgpu instead of hostname

C2 redirector Proxy Protocol (real client IPs in redirector_hits):
- nginx.conf: listen 443 ssl proxy_protocol, log $proxy_protocol_addr
- provision-redirector.sh: --port 443:443/tcp:proxy_proto
- thearm_logpull: FLY_API_TOKEN env var (fix broken --access-token flag),
  level_re parser (fix rfind(']') bug finding wrong bracket)

ZAP/Faraday CPU fix (periodic 100% CPU on meta-69):
- zap_scanner.py: time.sleep(0.15) throttle between Faraday POSTs
- ZAP_CONCURRENCY 3→1, resource limits on zaproxy (2CPU/4G),
  zap-scanner (0.5CPU/256M), faraday (1.5CPU/2G)

Housekeeping:
- startover.sh: force-restart nuclei-api after borodino deploy
- Remove vulnx service (orphaned, superseded by nuclei)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	borodino/redirector/nginx.conf
M	borodino/thearm_logpull
M	borodino/thearm_nuclei
M	oblast-1/zap_scanner.py
M	samsonov/nuclei_api/main.py
A	samsonov/nuclei_api/nuclei_ai.py
M	scripts/provision-redirector.sh
M	scripts/startover.sh
M	stack/40-service-borodino.yml
M	stack/51-service-ollama.yml
```

### Diff Summary

```
 borodino/redirector/nginx.conf   |  12 +-
 borodino/thearm_logpull          |  24 ++--
 borodino/thearm_nuclei           |  82 ++++++++++-
 oblast-1/zap_scanner.py          |   1 +
 samsonov/nuclei_api/main.py      |  52 ++++++-
 samsonov/nuclei_api/nuclei_ai.py | 298 +++++++++++++++++++++++++++++++++++++++
 scripts/provision-redirector.sh  |   2 +-
 scripts/startover.sh             |   6 +
 stack/40-service-borodino.yml    |  79 ++++-------
 stack/51-service-ollama.yml      |   4 +-
 10 files changed, 482 insertions(+), 78 deletions(-)
```
