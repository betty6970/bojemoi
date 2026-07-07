---
title: "Bojemoi Lab : l'architecture complète d'un homelab offensif/défensif sur Docker Swarm"
date: 2026-03-12T20:00:00+00:00
draft: false
tags: ["homelab", "docker", "docker-swarm", "devops", "gitops", "selfhosted", "opensource", "cybersecurity", "infosec", "threat-intelligence", "osint", "machine-learning", "blue-team", "soc", "build-in-public", "french-tech"]
summary: "Tour d'horizon complet de Bojemoi Lab : 4 nœuds Docker Swarm, 43 services, un pipeline de scan réseau massif, de la threat intelligence multi-sources et un stack d'observabilité full."
description: "Architecture détaillée de Bojemoi Lab — cluster Docker Swarm 4 nœuds, pipeline de reconnaissance (nmap → fingerprinting NSE → Metasploit), threat intelligence ML, IDS Suricata, honeypot multi-protocole, observabilité Prometheus/Grafana/Loki et CI/CD Gitea."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

J'ai construit Bojemoi Lab brique par brique depuis plusieurs mois. Il est temps de documenter ce que ça donne vraiment — pas juste un composant, mais l'ensemble du système.

Voici l'architecture complète.

---

## Vue d'ensemble

Bojemoi Lab est un cluster **Docker Swarm de 4 nœuds** qui fait tourner en permanence :

- Un **pipeline de reconnaissance réseau** (scan CIDR → fingerprinting → exploitation)
- Une **plateforme de threat intelligence** multi-sources (CTI, ML, OSINT, CERT)
- Un **stack défensif** (IDS, WAF, honeypot, règles dynamiques)
- Une **observabilité complète** (métriques, logs, traces)
- Des **interfaces de contrôle** (Telegram, MCP Claude, API REST)

Le tout sur des machines physiques à la maison, avec une infrastructure as code complète versionnée sur Gitea.

---

## Infrastructure physique

```
meta-76 (MANAGER)    Intel i9-10900X, 8 cores, 16 GB RAM
meta-68 (WORKER)     ─┐
meta-69 (WORKER)      ├─ IPs dynamiques (DHCP)
```

**Règle de placement fondamentale :**
- `meta-76` (manager) : PostgreSQL, Prometheus, Grafana, Loki, Traefik, Alertmanager — les services partagés
- Workers : tout le reste — scanning, threat intel, telegram, honeypot

Un registry Docker local tourne sur `localhost:5000`. Toutes les images sont buildées localement et poussées dedans avant déploiement.

---

## Les 12 stacks Docker

### Base — Services partagés (manager)

Le cœur du lab. Tout ce qui est partagé entre les services.

**PostgreSQL** — une seule instance, plusieurs bases :

| Base | Contenu |
|------|---------|
| `msf` | 6,15M hôtes, 33,7M services scannés — 9 GB |
| `bojemoi_threat_intel` | IoC classifiés, scores ML, cache OSINT |
| `ip2location` | CIDRs géolocalisés pour cibler les scans |
| `razvedka` | Mentions hacktivistes, alertes DDoS |
| `vigie` | Bulletins CERT-FR matchés par watchlist |
| `telegram_bot` | Historique commandes, sessions |
| `deployments` | Audit des déploiements (+ blockchain) |

**Observabilité :**
- Prometheus — scraping métriques (9 exporters : node, postgres, cadvisor, postfix, dozor, vigie, razvedka, medved, mcp)
- Grafana — dashboards provisionnés automatiquement
- Loki — agrégation logs (tous les services)
- Tempo — tracing distribué
- Alloy — collecteur unifié (pipeline vers Loki + Tempo)
- Alertmanager — routing vers Postfix/Proton Mail Bridge

**Mail :**
- Postfix (SMTP)
- Proton Mail Bridge — les alertes critiques partent chiffrées

**Orchestrateur provisioning :**
- FastAPI (port 8000, exposé en 28080)
- Déploie des VMs XenServer via cloud-init
- Gère les services Docker Swarm
- Stocke un audit trail blockchain en PostgreSQL

---

### Boot — Proxy et protection (manager)

- **Traefik** — reverse proxy, TLS automatique, routing
- **CrowdSec** — WAF collaboratif, bounce des IPs malveillantes

---

### Borodino — Pipeline de reconnaissance (workers)

C'est le cœur offensif du lab. Trois outils qui se chaînent :

#### ak47 — Scan CIDR (15 replicas)

Script ash qui :
1. Tire un CIDR aléatoire depuis `ip2location` avec `TABLESAMPLE SYSTEM()`
2. Lance `db_nmap -sS -A -O` via Metasploit
3. Stocke les résultats dans `msf.hosts` et `msf.services`

15 replicas en parallèle sur les 3 workers (max 5 par nœud).

#### bm12 v2 — Fingerprinting profond (15 replicas)

Script Python qui :
1. Sélectionne un hôte non encore fingerprinté
2. Lance des scripts NSE ciblés selon les services détectés (25 catégories : http, ssh, smtp, smb, dns, mysql, rdp...)
3. Classifie le serveur : `web` / `mail` / `dns` / `database` / `file_server` / `vpn_proxy` / `voip` / `iot_embedded` / `remote_access`
4. Stocke la classification JSON dans `hosts.scan_details`, le résumé dans `hosts.comments`, marque `scan_status = 'bm12_v2'`
5. Enrichit avec des scores OSINT (ip-api, OTX, ThreatCrowd, AbuseIPDB, VirusTotal, Shodan)

Un seul msfconsole par hôte (pas par service — gain de perfs majeur vs v1). Timeout 600s.

#### uzi — Exploit runner (3 replicas, désactivé)

Python + pymetasploit3. Sélectionne des hôtes Linux classifiés par bm12, tente des exploits Metasploit via RPC. En attente du service msfrpc (192.168.1.47:55553). `MODE_RUN=0` en production.

**Autres services Borodino :**
- DefectDojo (port 5985) — workspace de gestion des findings pentest
- OWASP ZAP — scanner d'applications web
- Nuclei — 25 templates de vulnérabilités
- Samsonov — importe les résultats nmap/nuclei dans DefectDojo
- Tsushima — agrégateur de résultats
- Redis — communication inter-services

---

### Threat Intelligence (workers)

#### razvedka — Prédiction DDoS

Surveille des canaux Telegram hacktivistes russes et ukrainiens (ddos_separ, RVvoenkor, CyberArmyofRussia, killnet_info...) et des comptes X/Twitter pour détecter le buzz DDoS ciblant la France.

Seuil d'alerte : 3 canaux actifs + 5 mentions = alerte Alertmanager.

Métriques sur port 9300.

#### vigie — Veille CERT-FR

Scrute les flux RSS ANSSI (alerte, avis, IOC) et les croise avec une watchlist de composants du lab :
`linux, docker, postgresql, traefik, grafana, prometheus, suricata, nginx, python, alpine, openssl, openssh...`

Alerte dès qu'un bulletin concerne un composant utilisé. Intervalle : 300s. Métriques port 9301.

#### dozor — Règles Suricata dynamiques

Consomme des feeds IoC toutes les 3600s, génère des règles Suricata dans `/opt/bojemoi/volumes/suricata/rules/blocklist.rules` et recharge Suricata via Unix socket (`/var/run/suricata/suricata-command.socket`).

Inclut un `eve-cleaner` qui purge les fichiers de log dépassant 5 GB.

#### ml-threat-intel — Scoring ML des IoC

API FastAPI qui classe les IoC (malware, C2, phishing, scanner...) avec un modèle ML entraîné, enrichit via OSINT (VirusTotal, AbuseIPDB, etc.) et mappe sur MITRE ATT&CK.

---

### Défense réseau (hors Swarm, host mode)

**Suricata** tourne en `docker-compose` classique (pas Swarm) avec `network_mode: host` sur `eth0`. Pas d'overlay réseau possible pour un IDS.

**EVE enricher** lit le JSON Suricata en temps réel et corrèle les alertes avec `bojemoi_threat_intel`.

---

### Honeypot — medved (manager, host mode)

Honeypot multi-protocole :

| Protocole | Port |
|-----------|------|
| SSH | 22 |
| HTTP | 8000 |
| RDP | 3389 |
| SMB | 445 |
| FTP | 2121 |
| Telnet | 2323 |

Tout log en PostgreSQL (`honeypot_events`), remonte dans un workspace DefectDojo dédié. Métriques port 9200.

---

### MCP Server — Intégration Claude Code (manager)

Serveur Model Context Protocol qui expose les données du lab directement dans Claude Code via HTTP/SSE (port 8001).

**Outils disponibles :**
- `query_hosts` / `query_services` / `get_host_details` — requêtes sur la DB msf
- `get_scan_stats` — statistiques globales
- `run_nmap` — lancer un scan depuis Claude
- `lookup_ip` — enrichissement OSINT
- `list_workspaces` / `get_vulns` / `add_vuln` — interface DefectDojo

Concrètement : je peux interroger 6 millions d'hôtes scannés directement depuis ma conversation Claude.

---

### Telegram Bot (workers)

Bot `@Betty_Bombers_bot` dans le groupe "Bojemoi PTaaS 😈".

Commandes : nmap, lookup IP, query hôtes, status services, résultats DefectDojo, OSINT enrichment. Communication avec les autres services via Redis pub/sub. Docker socket proxy pour les status.

---

## Flux de données — pipeline complet

```
ip2location DB (CIDRs géolocalisés)
        │
        ▼
    ak47 (x15)          ─── db_nmap -sS -A -O ───────────────→ msf.hosts / msf.services
        │
        ▼
    bm12 (x15)          ─── NSE ciblé + OSINT ──────────────→ hosts.scan_details (JSON)
        │                                                        hosts.scan_status = 'bm12_v2'
        ▼
    uzi (x3)            ─── Metasploit RPC ─────────────────→ vulns (désactivé)
        │
        ▼
    DefectDojo             ─── workspace pentest ───────────────→ findings
        │
        ▼
    Telegram Bot        ─── notifications + commandes
```

En parallèle :

```
Canaux Telegram hacktivistes → razvedka → Alertmanager → Email chiffré
Flux RSS ANSSI              → vigie    → Alertmanager → Email chiffré
Feeds IoC                   → dozor    → règles Suricata dynamiques
Trafic réseau               → Suricata → EVE enricher → threat_intel DB
Attaquants                  → medved   → PostgreSQL + DefectDojo
```

---

## Observabilité — stack complète

```
Services → métriques (9 exporters) → Prometheus
                                          │
                                          └→ Grafana (dashboards auto-provisionnés)
                                          └→ Alertmanager → Postfix → Proton Mail

Services → logs (stdout) → Alloy collector → Loki → Grafana explore
Services → traces        → Alloy collector → Tempo → Grafana explore
```

Tous les services custom exposent des métriques Prometheus. Les dashboards Grafana sont versionnés et provisionnés automatiquement au démarrage.

---

## CI/CD

- **GitLab CI** pour les stacks Docker Swarm (`.gitlab-ci.yml`)
  - Stages : validate → build → test → security (Trivy) → deploy → verify
  - Trivy scan : misconfigurations IaC + secrets exposés
- **Gitea Actions** pour le blog Hugo
  - Image Alpine → `hugo --minify` → volume mount direct vers `/var/www/blog.bojemoi.me/`

---

## Ce que ça représente

| Métrique | Valeur |
|----------|--------|
| Nœuds Swarm | 4 (1 manager + 3 workers) |
| Stacks Docker | 12 |
| Services | ~43 |
| Hôtes scannés en DB | 6,15M |
| Services réseau en DB | 33,7M |
| Taille PostgreSQL | 9 GB |
| Images Docker custom | 28 |
| Exporters Prometheus | 9 |

---

## Et maintenant ?

Le lab tourne en continu. bm12 fingerprinte en permanence de nouveaux hôtes. razvedka surveille les canaux hacktivistes. vigie me prévient dès qu'un composant que j'utilise a un CVE.

Prochaine étape : activer uzi quand le service msfrpc sera stable, et connecter les résultats de classification bm12 à des playbooks d'attaque ciblés.

Build in public. Tout est versionné sur Gitea. Les images sont sur Docker Hub.

→ **blog.bojemoi.me** pour les articles détaillés sur chaque composant.
