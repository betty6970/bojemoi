---
title: "[bojemoi] Push 3 commit(s) to main"
date: 2026-05-17T22:56:21+02:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 3 commit(s) par Betty dans bojemoi/main"
author: "Betty"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 3 |
| **Pushed by** | Betty |

### Commits

- **a3ef654** feat(uzi): traçabilité des décisions LLM en base postgres (Betty)
- **3a358c5** chore: nettoyage + refactor samsonov + mise à jour configs/docs (Betty)
- **a97505f** feat: resolve-image never + registry-gc + cccp notify + defectdojo email notifications (Betty)


### Diff Summary

```
 .claude/agents/osint-gatherer.md                   |   4 +-
 .claude/commands/borodino.md                       |   2 +-
 .claude/commands/connectivity.md                   |   2 +-
 .claude/commands/defectdojo.md                     |  63 ++
 .claude/commands/faraday.md                        |   6 +-
 .claude/commands/monitor.md                        |   4 +-
 .claude/commands/opsec-check.md                    |   4 +-
 .claude/commands/pentest.md                        |  10 +-
 .claude/commands/topology.md                       |  10 +-
 .env.example                                       |   2 +-
 ARCHITECTURE.md                                    |  12 +-
 BUILD_PROMPT.md                                    |  20 +-
 CLAUDE.md                                          |   6 +-
 Makefile                                           |  10 +-
 READ.me                                            |   2 +-
 README.md                                          |  19 +-
 archi.md                                           |  18 +-
 blog/architecture-bojemoi-lab-linkedin.md          |   2 +-
 blog/bojemoi-lab-sur-dockerhub.md                  |  10 +-
 blog/mcp-server-bojemoi-lab.md                     |  18 +-
 borodino/route-setup.sh                            |   4 +-
 borodino/thearm_nuclei                             |  18 +-
 borodino/thearm_uzi                                |  75 ++-
 discord/create_structure.sh                        |   2 +-
 discord/populate.py                                |  13 +-
 discord/post_blueteam.py                           |   2 +-
 discord/post_infra_channels.py                     |   2 +-
 discord/post_intel_channels.py                     |   2 +-
 discord/structure.yml                              |   2 +-
 docs/runbook/borodino-rebuild.md                   |   2 +-
 docs/runbook/docker-secrets.md                     |   2 +-
 docs/runbook/node-access.md                        |   7 +-
 docs/runbook/stack-deploy.md                       |  26 +-
 install.sh                                         |  12 +-
 mcp-server/tools/defectdojo.py                     |   2 +-
 oblast-1/Dockerfile.oblast-1                       |   6 +-
 oblast-1/zap_scanner.py                            |   6 +-
 provisioning/MANUAL.md                             |   2 +-
 samsonov/Dockerfile.samsonov                       |  14 +-
 samsonov/entrypoint.sh                             |  36 +-
 .../.dockerignore                                  |   0
 .../.gitignore                                     |   0
 .../CONTRIBUTING.md                                |   0
 .../INSTALLATION_ET_UTILISATION.txt                |   0
 .../LICENSE                                        |   0
 .../Makefile                                       |   0
 .../QUICKSTART.md                                  |   0
 .../README.md                                      |   0
 .../configs/nginx/nginx.conf                       |   0
 .../docker-compose.override.yml.example            |   0
 .../docker-compose.yml                             |   0
 .../examples.sh                                    |   0
 .../install.sh                                     |   0
 .../requirements.txt                               |   0
 .../scripts/masscan_to_faraday.py                  |   0
 .../scripts/msf_to_faraday.py                      |   0
 .../scripts/orchestrator.sh                        |   0
 .../scripts/zap/configure_zap.py                   |   0
 .../scripts/zap_to_faraday.py                      |   0
 .../test.sh                                        |   0
 samsonov/install-orchestrator.sh                   |   2 +-
 samsonov/nuclei_api/main.py                        |   6 +-
 samsonov/pentest_orchestrator/config/config.json   |  17 +-
 samsonov/pentest_orchestrator/import_results.py    |  14 +-
 samsonov/pentest_orchestrator/main.py              |  24 +-
 samsonov/pentest_orchestrator/plugins/base.py      |  31 +-
 .../pentest_orchestrator/plugins/plugin_nuclei.py  |  12 +-
 .../pentest_orchestrator/plugins/plugin_vulnx.py   |   4 +-
 samsonov/scripts/pentest_orchestrator.py           |  24 +-
 samsonov/server.ini                                |  10 +-
 samsonov/vulnx_wrapper/main.py                     |   2 +-
 "samsonov/\360\237\216\257-COMMENCEZ-ICI.txt"      |  12 +-
 scripts/CI_CD_check.sh                             |   2 +-
 scripts/CI_CD_deploy.sh                            |  94 ---
 scripts/c2-manage.sh                               |   2 +-
 scripts/cccp.sh                                    |  36 ++
 scripts/check_image_v2.py                          |   2 +-
 sentinel/setup.sh                                  |   2 +-
 stack/.gitlab-ci.yml                               |  10 +-
 stack/01-service-hl.yml                            |  18 +-
 stack/02-init-ptaas.yml                            |   2 +-
 stack/02-service-maintenance.yml                   |  38 ++
 stack/40-service-borodino.yml                      |  62 ++
 stack/42-service-recon.yml                         |   2 +-
 stack/47-service-vigie.yml                         |   2 +-
 stack/49-service-mcp.yml                           |   2 +-
 stack/55-service-sentinel.yml                      |   2 +-
 stack/56-service-dvar.yml                          |   2 +-
 stack/60-service-telegram.yml                      |   4 +-
 stack/65-service-medved.yml                        |   2 +-
 stack/README.md                                    |   6 +-
 vigie/vigie/config.py                              |   2 +-
 volumes/defectdojo/dojo_smtp_backend.py            |  32 +
 volumes/defectdojo/local_settings.py               |  25 +
 volumes/defectdojo/smtp_setup.py                   |  35 ++
 volumes/dnsmask/dnsmask.d/01-base.conf             |   3 +-
 volumes/generate_configs.sh                        | 680 ++++++++++-----------
 volumes/nginx/deploy.sh                            |   2 +-
 volumes/nginx/index.html                           |   4 +-
 volumes/prometheus/nodes.json                      |   1 -
 volumes/prometheus/prometheus.yml                  |  61 +-
 volumes/prometheus/rules/alerts.yml                |  24 +-
 wiki/Alertes.md                                    |   2 +-
 wiki/Claude-Skills.md                              |  42 +-
 wiki/DefectDojo.md                                 | 144 +++++
 wiki/Docker-Swarm.md                               |   4 +-
 wiki/Faraday.md                                    | 188 +-----
 wiki/Home.md                                       |   4 +-
 wiki/Pentest-Orchestrator.md                       | 277 ---------
 zarovnik/GITLAB-SETUP.md                           |  12 +-
 zarovnik/gitlab-ci-example.yml                     |  12 +-
 zarovnik/gitlab-runner-config-example.toml         |   2 +-
 112 files changed, 1205 insertions(+), 1258 deletions(-)
```
