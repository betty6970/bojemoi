---
title: "Bojemoi Lab sur Docker Hub : 21 images open source pour un homelab red-team"
date: 2026-03-01
draft: false
tags: ["homelab", "docker", "docker-swarm", "devops", "selfhosted", "opensource", "cybersecurity", "infosec", "osint", "threat-intelligence", "build-in-public", "french-tech"]
summary: "J'ai publié les 21 images Docker de Bojemoi Lab sur Docker Hub. Tour d'horizon de ce que fait chaque composant et comment tout ça s'articule."
description: "Publication des images Docker de Bojemoi Lab sur Docker Hub — 21 images couvrant le scanning réseau, la threat intelligence ML, le honeypot multi-protocole, la veille CVE et plus encore."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

Les images Docker de Bojemoi Lab sont maintenant publiques sur Docker Hub : [`hub.docker.com/u/bettybombers696`](https://hub.docker.com/u/bettybombers696).

21 images. Un cluster Swarm de 4 nœuds. Quelques semaines de build en public. Voilà ce que ça donne.

---

## Pourquoi publier ?

Bojemoi Lab tourne sur un registre Docker local (`localhost:5000`). Pratique pour le cluster, mais ça ne sort pas de la maison. Publier sur Docker Hub, c'est :

1. **Garder une trace** — un registre public comme backup des images buildées
2. **Rendre ça reproductible** — quelqu'un d'autre peut puller et tester
3. **Build in public** — assumer ce qu'on construit, même quand c'est encore rough

Ce n'est pas du code parfait. C'est un lab qui tourne en prod, avec des vraies données de scan, des vraies alertes, et des vraies erreurs de conception corrigées en cours de route.

---

## Ce que contient le lab

Bojemoi Lab est un homelab red-team / threat intelligence qui tourne sur Docker Swarm (4 nœuds, Alpine/BusyBox). Les composants couvrent l'ensemble du cycle :

```
RECONNAISSANCE → SCANNING → EXPLOITATION → ANALYSE → DÉFENSE
```

Voici les grandes familles :

### Scanning et reconnaissance

**`borodino`** — le cœur offensif. Trois workers indépendants :
- `ak47` : scanne des plages CIDR via `db_nmap -sS -A -O`, alimente la base Metasploit
- `bm12` : fingerprinting profond des hôtes existants — 25 catégories de scripts NSE, classification (web / mail / dns / iot / vpn...), résultats stockés en JSON
- `uzi` : exploitation via `pymetasploit3`, cible les hôtes Linux vulnérables identifiés par bm12

**`tsushima`** — pipeline masscan avec rotation VPN pour du scanning haute vitesse.

**`oblast` / `oblast-1`** — OWASP ZAP pour le scan de vulnérabilités web.

### Threat intelligence

**`ml-threat-intel`** — le composant le plus élaboré. Une API FastAPI qui :
- Classe les IOCs (IP, domaines, hashs) en `benign / suspicious / malicious`
- Score la réputation de 0 à 100
- Agrège VirusTotal (35%), AbuseIPDB (30%), AlienVault OTX (20%), Shodan (15%)
- Lance des investigations complètes en 4 phases avec corrélation IA (Claude Haiku pour les menaces faibles, Claude Sonnet pour les critiques)

**`razvedka`** — collecte OSINT depuis des canaux Telegram et Twitter. Extraction NLP, scoring "buzz", stockage PostgreSQL. Le composant qui surveille ce que les attaquants disent avant d'agir.

### Défense et monitoring

**`dozor`** — agrégateur de feeds de menaces. Télécharge les blacklists, génère des règles Suricata, les recharge à chaud.

**`vigie`** — veille CVE. Surveille des flux RSS/Atom (CERT, NVD, advisories constructeurs), matche contre une watchlist de produits, alerte.

**`suricata-attack-enricher`** — enrichit les alertes Suricata avec du contexte threat intel avant de les envoyer au SIEM.

**`suricata_exporter`** — exporte les métriques Suricata vers Prometheus.

### Honeypot

**`medved`** — honeypot multi-protocole : SSH, HTTP, RDP, SMB, FTP, Telnet. Capture les tentatives de connexion, les credentials, reporte dans Faraday.

### Alertes et interaction

**`telegram-bot`** — le bot `@Betty_Bombers_bot`. Commandes `/analyze <ip>`, `/batch`, `/stats`. Les alertes critiques (score > 80) partent directement dans le groupe PTaaS.

### Infrastructure

**`provisioning`** — orchestrateur FastAPI pour déployer des VMs XenServer et des services Docker via GitOps (source de config : Gitea).

**`bojemoi-mcp`** — serveur MCP local. Claude Code peut interroger la DB Metasploit (6M+ hôtes), lancer des scans nmap, faire de l'OSINT et gérer Faraday — en langage naturel, sans quitter le terminal.

**`koursk` / `koursk-1` / `koursk-2`** — rsync daemon pour la réplication entre nœuds, avec exporter Prometheus.

**`karacho`** — API blockchain + PostgreSQL.

**`samsonov`** — intégration Faraday pour centraliser les findings de sécurité.

---

## La base de données derrière tout ça

Tout converge dans PostgreSQL (sur le manager, stack `base`) :

| Base | Contenu | Taille |
|------|---------|--------|
| `msf` | Hosts (6,15M), services (33,7M) — DB Metasploit | ~9 GB |
| `ip2location` | CIDRs géolocalisés — source de cibles pour ak47 | — |
| `bojemoi_threat_intel` | Cache IOCs, historique d'analyses, investigations | — |
| `faraday` | Findings de sécurité | — |

Un apprentissage douloureux : `ORDER BY RANDOM()` sur 6 millions de lignes = PostgreSQL à 459% CPU, load average à 9. Remplacé par `TABLESAMPLE SYSTEM()`. PostgreSQL est retombé à 29% CPU.

---

## Ce qui n'est PAS dans les images

Les images ne contiennent pas :
- Les credentials (clés API VirusTotal, AbuseIPDB, Anthropic, tokens Telegram...)
- Les données de scan (volumes PostgreSQL gitignorés)
- Les configurations réseau Swarm (overlay networks, secrets Docker)

Tout ça reste dans des Docker secrets et des volumes locaux. Les images sont des binaires propres.

---

## Stack technique

```
Orchestration  : Docker Swarm — 4 nœuds (meta-76 manager, meta-68/69/70 workers)
Base           : PostgreSQL 15, SQLAlchemy 2.0
Monitoring     : Prometheus + Grafana + Loki + Promtail
IDS            : Suricata 7 + CrowdSec
Vuln mgmt      : Faraday
API            : FastAPI + Uvicorn (Python 3.11)
IA             : Claude API (Anthropic) — Haiku + Sonnet
Lang           : Python, Bash/Ash (Alpine), un peu de Ruby (borodino)
```

---

## Reproduire le lab

Les images sont publiques. Pour les puller :

```bash
docker pull bettybombers696/ml-threat-intel:latest
docker pull bettybombers696/borodino:latest
docker pull bettybombers696/medved:latest
# etc.
```

Chaque image a un README sur Docker Hub avec les variables d'environnement et les dépendances.

Ce n'est pas un projet clé en main — les stack files Swarm, les secrets et la config réseau ne sont pas inclus. Mais les images sont là pour être inspectées, forkées ou adaptées.

---

## La suite

Les prochains posts couvriront en détail certains composants — notamment `ml-threat-intel` (le pipeline ML + agents Claude) et `razvedka` (l'OSINT Telegram). Il y a des choses intéressantes à raconter sur ce qui marche et ce qui ne marche pas quand on fait du threat intel en homelab.

---

*Build in public. Même les parties rough.*

#homelab #docker #docker-swarm #selfhosted #opensource #cybersecurity #osint #threat-intelligence #build-in-public #french-tech #devops #infosec
