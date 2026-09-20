---
title: "[bojemoi] Push 4 commit(s) to main"
date: 2026-09-20T13:38:57+02:00
draft: false
tags: ["push", "bojemoi", "main"]
categories: ["Git Activity"]
summary: "Push de 4 commit(s) par grafana-watcher dans bojemoi/main"
author: "grafana-watcher"
---

## Push to `bojemoi/main`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Commits** | 4 |
| **Pushed by** | grafana-watcher |

### Commits

- **8afb722** feat(honeypot): ajouter honeypot-ingestor — boucle intelligence temps réel (grafana-watcher)
- **84d4b48** feat(scripts): versionner les scripts utilitaires (récupérés depuis meta-68) (grafana-watcher)
- **4c8b2eb** feat(volumes): récupérer les configs manquantes depuis meta-68 (grafana-watcher)
- **e53f772** fix(volumes): compléter le versionnement — provisioning/.env et dnsmask.d (grafana-watcher)


### Diff Summary

```
 .gitignore                                         |    5 +
 honeypot-ingestor/Dockerfile                       |   13 +
 honeypot-ingestor/classifier.py                    |  139 +
 honeypot-ingestor/ingestor.py                      |  315 ++
 scripts/CI_CD_check.sh                             |   60 +
 scripts/INTEGRATION_GUIDE.sh                       |  205 ++
 scripts/README.md                                  |  540 +++
 scripts/alertmanager-debug.sh                      |  149 +
 scripts/all_compil.sh                              |  283 ++
 scripts/bojemoi2.py                                |  905 +++++
 scripts/bojemoiBuild.sh                            |  289 ++
 scripts/bojemoiCadencer.sh                         |   19 +
 scripts/build_all.sh                               |    5 +
 scripts/c2-manage.sh                               |  415 +++
 scripts/c2-vpn-init-pki.sh                         |  255 ++
 scripts/cccp.sh                                    |  329 ++
 scripts/check_image.py                             |  356 ++
 scripts/check_image_v2.py                          |  481 +++
 scripts/check_new_images                           |   32 +
 scripts/cleanDocker.sh                             |  256 ++
 scripts/clean_image.py                             |  156 +
 scripts/cleaning_registry.sh                       |   43 +
 scripts/commits-to-posts.sh                        |  123 +
 scripts/create-nfs-volume.sh                       |    5 +
 scripts/create-secrets.sh                          |  212 ++
 scripts/deploy-base-stack.sh                       |   69 +
 scripts/deploy-stacks.log                          |    2 +
 scripts/deploy-worker-vm.sh                        |  239 ++
 scripts/download_ip.py                             |  238 ++
 scripts/download_ruby_dockerfiles_real.py          |   52 +
 scripts/encode.py                                  |  242 ++
 scripts/examples_usage.py                          |  301 ++
 scripts/gameover.sh                                |  182 +
 scripts/images_cross_build.py                      |  212 ++
 scripts/import_dbip_country.py                     |  119 +
 scripts/import_ripe_cidrs.py                       |  113 +
 scripts/import_vulnhub_ova.sh                      |  123 +
 scripts/index.html                                 |  370 ++
 scripts/init-proton-bridge.sh                      |   12 +
 scripts/init_postgres.sh                           |   15 +
 scripts/list_registry.sh                           |   10 +
 scripts/metasploitable2_exploit.py                 |  388 +++
 scripts/mockba.sh                                  |  286 ++
 scripts/nfs-install.sh                             |   70 +
 scripts/package-dist.sh                            |  305 ++
 scripts/post-commit-blog.sh                        |  110 +
 scripts/postgresql.sh                              |    7 +
 scripts/provision-redirector.sh                    |  116 +
 scripts/push_registry_onebyone.sh                  |   69 +
 scripts/recreate_databases.sql                     |   55 +
 scripts/run.sh                                     |   14 +
 scripts/search_dockerfile                          |  360 ++
 scripts/send_email.sh                              |   13 +
 scripts/stack_export.sh                            |  259 ++
 scripts/startover.sh                               |  305 ++
 scripts/sync-stack-images.sh                       |  140 +
 scripts/sync_registry.py                           |  332 ++
 scripts/sync_registry.sh                           |   16 +
 scripts/tannenberg.py                              |  155 +
 scripts/zaproxy-run-test.sh                        |    2 +
 stack/65-service-medved.yml                        |   45 +
 volumes/alloy/config/config-worker.alloy           |   64 +
 volumes/c2-vpn/.gitignore                          |    6 +
 volumes/c2-vpn/README.md                           |   46 +
 volumes/dnsmask/dnsmask.d/.gitkeep                 |    0
 volumes/dnsmask/dnsmask.d/01-base.conf             |   66 +
 volumes/grafana/dashboards/dashboard.yml           |   10 +
 .../general/docker-container-metrics.json          | 1737 ++++++++++
 .../dashboards/general/loki-stack-monitoring.json  |  239 ++
 .../grafana/dashboards/general/nvidia-dcgm.json    |  804 +++++
 .../grafana/dashboards/pentest/c2-sessions.json    |  316 ++
 .../dashboards/pentest/pentest-overview.json       |  999 ++++++
 .../dashboards/pentest/pipeline-overview.json      | 3653 ++++++++++++++++++++
 .../grafana/dashboards/pentest/scan-results.json   |  971 ++++++
 .../dashboards/pentest/vuln-management.json        | 1544 +++++++++
 .../dashboards/redteam-analyse/hosts-geo.json      |  412 +++
 .../security/dashboard-security-minimal.json       |   57 +
 volumes/grafana/dashboards/security/sentinel.json  |  812 +++++
 volumes/grafana/dashboards/security/vigie.json     |  328 ++
 .../dashboards/topology/service-topology.json      |   79 +
 volumes/grafana/datasources/prometheus.yml         |    7 +
 volumes/grafana/datasources/sentinel-postgres.yml  |   16 +
 .../provisioning/dashboards/attack-heatmap.json    |  277 ++
 volumes/nuclei/config/.nuclei-ignore               |   42 +
 volumes/nuclei/config/reporting-config.yaml        |  105 +
 volumes/nuclei/nuclei-config.yml                   |    7 +
 volumes/postgres/conf/pg_hba.conf                  |   22 +
 volumes/postgres/init/02-ip2location-schema.sql    |   60 +
 volumes/postgres/init/03-msf-custom-tables.sql     |   50 +
 volumes/postgres/postgres-entrypoint.sh            |   14 +
 volumes/prometheus/nodes.json                      |    9 +
 volumes/prometheus/rules/alert_rules.yml           |  447 +++
 volumes/prometheus/rules/alerts.yml                | 1054 ++++++
 volumes/prometheus/rules/recording_rules.yml       |  288 ++
 volumes/prometheus/rules/sentinel_alerts.yml       |   52 +
 volumes/provisioning/.env                          |   32 +
 volumes/rsync/keys/deploy-keys-to-docker.sh        |   74 +
 volumes/rsync/keys/distribute-public-keys.sh       |  109 +
 volumes/rsync/keys/generate-ssh-keys.sh            |   85 +
 volumes/rsync/keys/genkey.sh                       |  465 +++
 volumes/rsync/keys/rotate-ssh-keys.sh              |   32 +
 volumes/rsync/keys/test-ssh-keys.sh                |  140 +
 volumes/suricata/classification.config             |   51 +
 volumes/suricata/config/classification.config      |   50 +
 volumes/suricata/reference.config                  |   44 +
 volumes/suricata/threshold.config                  |   32 +
 volumes/suricata/update.yaml                       |    1 +
 volumes/traefik/certs/ca-cert.srl                  |    1 +
 volumes/traefik/key_gen.sh                         |   73 +
 109 files changed, 26718 insertions(+)
```
