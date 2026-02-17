---
title: "Track volumes/ config files in git"
date: 2026-01-27T14:23:49+01:00
draft: false
tags: ["commit", "bojemoi", "orchestrator", "config"]
categories: ["Git Activity"]
summary: "Commit bc2bfa1 par Betty — 94 fichier(s) modifié(s)"
author: "Betty"
---

## Commit `bc2bfa1`

| | |
|---|---|
| **Repository** | bojemoi |
| **Branch** | `main` |
| **Auteur** | Betty |
| **Hash** | `bc2bfa19ed035b4401f32e30fc9141fce9d45f1d` |
| **Date** | 2026-01-27 |

### Description

Add service configuration files from volumes/ directory to version control.
Updated .gitignore to:
- Remove volumes/ exclusion (configs should be tracked)
- Keep ignoring sensitive files (private keys, auth.txt, logs, sockets)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>

### Fichiers modifiés

```
M	.gitignore
A	volumes/READ.me
A	volumes/alert_rules.yml
A	volumes/alertmanager/alertmanager.yml
A	volumes/alertmanager/alertmanager.yml.txt
A	volumes/alloy/config/config.alloy
A	volumes/crowdsec/config/acquis.yaml
A	volumes/deploy.sh
A	volumes/dnsmask/dnsmask.conf
A	volumes/dnsmask/dnsmask.d/01-base.conf
A	volumes/faraday/config/server.ini
A	volumes/faraday/server.ini
A	volumes/generate_configs.sh
A	volumes/gitlab/cinc-stacktrace.out
A	volumes/gitlab/config.toml
A	volumes/gitlab/gitlab.rb
A	volumes/grafana/dashboards/dashboard-security-minimal.json
A	volumes/grafana/dashboards/dashboard.yml
A	volumes/grafana/dashboards/pentest/pentest-overview.json
A	volumes/grafana/datasources/prometheus.yml
A	volumes/grafana/grafana.ini
A	volumes/grafana/provisioning/dashboards/dashboards.yml
A	volumes/grafana/provisioning/datasources/datasources.yml
A	volumes/loki/loki-config.yml
A	volumes/monitoring/alertmanager/templates/default.tmpl
A	volumes/monitoring/grafana/provisioning/datasources/elasticsearch.yml
A	volumes/monitoring/logstash/config/logstash.yml
A	volumes/monitoring/logstash/pipeline/logstash.conf
A	volumes/nginx/conf.d/default.conf
A	volumes/nginx/conf.d/sites/faraday.conf
A	volumes/nginx/conf.d/sites/grafana.conf
A	volumes/nginx/conf.d/sites/prometheus.conf
A	volumes/nginx/conf.d/sites/zap.conf
A	volumes/nginx/conf.d/upstreams/upstreams.conf
A	volumes/nginx/deploy.sh
A	volumes/nginx/index.html
A	volumes/nuclei/nuclei-config.yml
A	volumes/openvpn/Read.me
A	volumes/openvpn/openvpn-config/.firewall
A	volumes/openvpn/openvpn-config/.firewall6
A	volumes/openvpn/openvpn-config/client.ovpn
A	volumes/openvpn/openvpn-config/fr.protonvpn.tcp.ovpn
A	volumes/openvpn/script/setup_tun.sh
A	volumes/openvpn/script/tun-check.sh
A	volumes/openvpn/script/vpn-manager.sh
A	volumes/postfix/main.cf
A	volumes/prometheus/nodes.json
A	volumes/prometheus/prometheus.yml
A	volumes/prometheus/rules/alert_rules.yml
A	volumes/prometheus/rules/alerts.yml
A	volumes/prometheus/rules/recording_rules.yml
A	volumes/provisioning/A.env
A	volumes/registry/config.yml
A	volumes/rsync/configs/rsyncd.conf
A	volumes/rsync/keys/deploy-keys-to-docker.sh
A	volumes/rsync/keys/distribute-public-keys.sh
A	volumes/rsync/keys/generate-ssh-keys.sh
A	volumes/rsync/keys/genkey.sh
A	volumes/rsync/keys/rotate-ssh-keys.sh
A	volumes/rsync/keys/test-ssh-keys.sh
A	volumes/rsync/ssh-keys/id_rsa
A	volumes/rsync/ssh-keys/id_rsa.pub
A	volumes/suricata/classification.config
A	volumes/suricata/reference.config
A	volumes/suricata/suricata.yaml
A	volumes/suricata/threshold.config
A	volumes/suricata/update.yaml
A	volumes/tempo/config/tempo.yaml
A	volumes/traefik/certs/ca-cert.srl
A	volumes/traefik/dynamic-config.yml
A	volumes/traefik/key_gen.sh
A	volumes/traefik/traefik-tls.yml
A	volumes/wireguard/config/.donoteditthisfile
A	volumes/wireguard/config/coredns/Corefile
A	volumes/wireguard/config/peer1/peer1.conf
A	volumes/wireguard/config/peer1/peer1.png
A	volumes/wireguard/config/peer1/publickey-peer1
A	volumes/wireguard/config/peer2/peer2.conf
A	volumes/wireguard/config/peer2/peer2.png
A	volumes/wireguard/config/peer2/publickey-peer2
A	volumes/wireguard/config/peer3/peer3.conf
A	volumes/wireguard/config/peer3/peer3.png
A	volumes/wireguard/config/peer3/publickey-peer3
A	volumes/wireguard/config/peer4/peer4.conf
A	volumes/wireguard/config/peer4/peer4.png
A	volumes/wireguard/config/peer4/publickey-peer4
A	volumes/wireguard/config/peer5/peer5.conf
A	volumes/wireguard/config/peer5/peer5.png
A	volumes/wireguard/config/peer5/publickey-peer5
A	volumes/wireguard/config/server/publickey-server
A	volumes/wireguard/config/show-client.sh
A	volumes/wireguard/config/templates/peer.conf
A	volumes/wireguard/config/templates/server.conf
A	volumes/wireguard/config/wg_confs/wg0.conf
```

### Statistiques

```
 94 files changed, 14653 insertions(+), 1 deletion(-)
```
