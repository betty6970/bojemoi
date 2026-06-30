---
title: "[bojemoi] Push 2 commit(s) to main"
date: 2026-06-30T15:29:52+02:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 2 commit(s) par grafana-watcher dans bojemoi/main"
author: "grafana-watcher"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 2 |
| **Pushed by** | grafana-watcher |

### Commits

- **904a659** chore(lint): ruff auto-fix across all Python files (grafana-watcher)
- **e7bc7fc** feat(grafana-watcher): add grafana labels on masscan, zap, sliver, pentest-orchestrator, msf-teamserver (grafana-watcher)


### Diff Summary

```
 .claude/agent-memory/infra-daily-monitor/MEMORY.md | 261 ++++---------
 .claude/agent-memory/pipeline/MEMORY.md            |  34 +-
 arch-reviewer/arch_reviewer.py                     |   4 +-
 .../bojemoi_mitre_attack/mappings/__init__.py      |   9 +
 discord/cleanup.py                                 |   4 +-
 discord/populate.py                                |   5 +-
 discord/post_architecture.py                       |   6 +-
 discord/post_blueteam.py                           |   4 +-
 discord/post_infra_channels.py                     |   4 +-
 discord/post_intel_channels.py                     |   4 +-
 dozor/dozor/config.py                              |   1 -
 karacho/blockchain_postgres_api-1.py               | 429 ++++++++++-----------
 karacho/blockchain_postgres_api.py                 | 259 ++++++-------
 karacho/blockchain_service.py                      | 103 +++--
 karacho/client_api.py                              | 159 ++++----
 koursk-1/metrics_exporter.py                       |  41 +-
 koursk-2/modules/bojemoi.py                        |  92 ++---
 koursk-2/scripts/list_rsync_slave.py               |  67 ++--
 koursk-2/scripts/listrsyncslave.py                 |  30 +-
 koursk-2/scripts/rsync-master.py                   | 108 +++---
 mcp-server/tools/metasploit.py                     |   1 -
 mcp-server/tools/nmap.py                           |   1 -
 medved/honeypot/protocols/http_handler.py          |   3 +-
 medved/honeypot/protocols/rdp_handler.py           |   1 -
 oblast-1/zap_scanner.py                            |   2 -
 provisioning/orchestrator/alembic/env.py           |   2 +-
 provisioning/orchestrator/app/auth/dependencies.py |   2 +-
 provisioning/orchestrator/app/main.py              |   4 +-
 provisioning/orchestrator/app/metrics.py           |   3 +-
 .../orchestrator/app/middleware/ip_validation.py   |   2 +-
 .../orchestrator/app/middleware/metrics.py         |   2 +-
 .../orchestrator/app/services/cloudinit_gen.py     |  42 +-
 .../orchestrator/app/services/docker_client.py     |  66 ++--
 .../orchestrator/app/services/gitea_client.py      |   5 +-
 .../app/services/local_template_client.py          |   1 -
 .../orchestrator/app/services/xenserver_client.py  |  61 ++-
 .../app/services/xenserver_client_real.py          |  10 +-
 provisioning/orchestrator/app/test_all_services.py |  79 ++--
 provisioning/orchestrator/app/test_xenserver.py    |  19 +-
 ptaas-init/init.py                                 |   8 +-
 recon/pipeline.py                                  |   3 +-
 .../bojemoi_mitre_attack/mappings/__init__.py      |   9 +
 samsonov/nuclei_api/main.py                        |   6 +-
 samsonov/pentest_orchestrator/import_results.py    |   2 +-
 samsonov/pentest_orchestrator/plugins/base.py      |   1 -
 .../pentest_orchestrator/plugins/plugin_masscan.py |  72 ++--
 .../plugins/plugin_metasploit.py                   | 123 +++---
 .../pentest_orchestrator/plugins/plugin_nuclei.py  |  10 +-
 .../pentest_orchestrator/plugins/plugin_vulnx.py   |   3 +-
 .../pentest_orchestrator/plugins/plugin_zap.py     |  68 ++--
 samsonov/scripts/metrics_exporter.py               |   6 +-
 samsonov/scripts/pentest_orchestrator.py           |  88 ++---
 scripts/check_image.py                             |  90 ++---
 scripts/clean_image.py                             |  34 +-
 scripts/examples_usage.py                          |  69 ++--
 scripts/images_cross_build.py                      |  85 ++--
 scripts/metasploitable2_exploit.py                 |   1 -
 scripts/sync_registry.py                           |  79 ++--
 scripts/tannenberg.py                              |  34 +-
 sentinel/collector/collector.py                    |   8 +-
 stack/39-service-borodino-msf.yml                  |   5 +
 stack/40-service-borodino.yml                      |  35 ++
 stack/55-service-sentinel.yml                      |   2 +-
 .../bojemoi_mitre_attack/mappings/__init__.py      |   9 +
 suricata-attack-enricher/enricher.py               |   1 -
 tsushima/masscan_msf_script.py                     | 227 ++++++-----
 tsushima/vpn_masscan_pipeline.py                   | 331 ++++++++--------
 vigie/vigie/main.py                                |   1 -
 68 files changed, 1637 insertions(+), 1703 deletions(-)
```
