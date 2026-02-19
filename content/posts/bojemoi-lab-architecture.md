---
title: "Bojemoi Lab — Architecture de la plateforme"
date: 2026-02-19
draft: false
tags: ["infrastructure", "docker-swarm", "metasploit", "security", "architecture"]
summary: "Vue d'ensemble complète de la plateforme Bojemoi Lab : orchestration Docker Swarm, workers de scan Metasploit, CTI, honeypot et pipeline de threat intelligence."
---

Bojemoi Lab est une plateforme hybride d'Infrastructure-as-Code déployée sur Docker Swarm (4 nœuds). Elle combine sécurité offensive, CTI, monitoring et orchestration de déploiement.

**Environnement :**
- Manager : meta-76 (Alpine/BusyBox, i9-10900X, 16 GB RAM)
- Workers : meta-68, meta-69, meta-70 (contrainte `node.role == worker`)
- Registry local : `localhost:5000`
- Gitea : `gitea.bojemoi.me`

---

## 1. Orchestrateur de déploiement

FastAPI avec middleware de validation IP géographique, chaîne blockchain SHA-256 pour l'audit immuable des déploiements, et intégration XenServer pour les VMs.

**Endpoints principaux :**
- `POST /api/v1/vm/deploy` — Déployer une VM sur XenServer
- `POST /api/v1/container/deploy` — Déployer un service Docker Swarm
- `GET /api/v1/blockchain/verify` — Vérifier l'intégrité de la chaîne d'audit

**Workflow VM :**
1. Validation IP source (whitelist Europe Occidentale, bypass RFC1918)
2. Récupération du template cloud-init depuis Gitea
3. Rendu Jinja2 avec les variables
4. Création VM via XenAPI
5. Enregistrement blockchain (karacho) + PostgreSQL

---

## 2. Borodino — Workers de scan Metasploit

Image `ruby:3.3-alpine` avec Metasploit Framework complet, nmap, pymetasploit3 et ProtonVPN.

### ak47 (15 répliques)

Script ash qui sélectionne des CIDRs depuis `ip2location_db1` via `TABLESAMPLE SYSTEM(1)` et lance `db_nmap -sS -A -O` via msfconsole. Les résultats alimentent la base `msf` (6,15M hosts, 33,7M services).

### bm12 v2 (15 répliques)

Fingerprinting profond des hosts existants :
- Sélection aléatoire via `TABLESAMPLE SYSTEM(0.001)`
- Mapping des services ouverts vers 25 catégories NSE ciblées (http, ssh, smtp, smb, dns, mysql, rdp…)
- Un seul msfconsole par host (timeout 600s)
- Classification : web / mail / dns / database / file_server / vpn_proxy / voip / iot_embedded / remote_access
- Résultat stocké dans `hosts.comments`, `hosts.scan_details` (JSON), `hosts.scan_status='bm12_v2'`

### uzi (1 réplique)

Exploitation via MsfRpcClient (pymetasploit3) sur port 55553. Itère les modules exploit Linux post-2021, tente chaque exploit avec chaque payload, alerte Telegram en cas de session ouverte.

---

## 3. Samsonov — Orchestrateur Pentest

Architecture plugin chargée dynamiquement depuis Redis (`pentest:commands`).

**Pipeline de scan :** Masscan → ZAP spider/active → Burp passive → Nuclei → VulnX → Metasploit

**Types de scan :** `full`, `web`, `network`, `vuln`, `cms`

Les résultats sont agrégés et importés dans Faraday.

---

## 4. Bibliothèque MITRE ATT&CK

Package Python partagé `bojemoi-mitre-attack` embarqué dans plusieurs images. Mappe 35+ catégories Suricata vers des techniques ATT&CK avec niveau de confiance (high/medium/low), couvrant : initial-access, reconnaissance, C2, credential-access, privilege-escalation, exfiltration, lateral-movement.

---

## 5. Suricata Attack Enricher

Service Python async qui suit `eve.json` de Suricata en temps réel, mappe chaque alerte vers ATT&CK, et insère en batch dans PostgreSQL (`bojemoi_threat_intel.suricata_attack_alerts`). Batch 50 entrées / flush 5s.

---

## 6. Services CTI

| Service | Rôle |
|---|---|
| **razvedka** | Surveille canaux Telegram hacktvistes (KillNet, CyberArmyOfRussia…), score l'intention DDoS ciblant la France |
| **vigie** | Scrape flux RSS ANSSI/CERT-FR, alerte sur nouvelles vulnérabilités selon une watchlist produits |
| **dozor** | Génère les règles blocklist Suricata depuis threat intel, reload via socket Unix |
| **ml-threat-intel** | Classificateur ML d'IoC (VT/AbuseIPDB/OTX/Shodan/Anthropic APIs) |

---

## 7. Honeypot Medved

Multi-protocole : SSH :22, HTTP :8888, RDP :3389, SMB :445, FTP :2121, Telnet :2323, Elasticsearch :9200. Toutes les interactions sont loguées dans la base `msf` et envoyées à Faraday.

---

## Stacks Docker Swarm

| Stack | Services principaux |
|---|---|
| **base** (manager) | postgres, grafana, prometheus, loki, tempo, alertmanager, orchestrator |
| **borodino** (workers) | ak47×15, bm12×15, uzi×1, karacho, masscan, nuclei, faraday, zaproxy, redis |
| **ml-threat-intel** (workers) | API classificateur IoC |
| **razvedka** (workers) | Monitor Telegram hacktvistes |
| **vigie** (workers) | Monitor ANSSI/CERT-FR |
| **dozor** (workers) | Générateur règles Suricata |
| **telegram** (workers) | Bot Telegram (interface Redis + docker-socket-proxy) |
| **medved** (workers) | Honeypot multi-protocoles |

---

## Base de données

Instance PostgreSQL partagée sur meta-76 :

| Base | Usage |
|---|---|
| `msf` | Metasploit — 6,15M hosts, 33,7M services, 9 GB |
| `ip2location` | CIDRs géolocalisation |
| `faraday` | Findings sécurité |
| `deployments` | État orchestrateur |
| `bojemoi_threat_intel` | Alertes Suricata enrichies ATT&CK |
| `karacho` | Blockchain audit déploiements |
