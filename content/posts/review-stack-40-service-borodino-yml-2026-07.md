---
title: "Borodino Stack : Anatomie d'un lab red-team complet sous Docker Swarm"
date: 2026-07-20
draft: false
tags: ["homelab", "docker", "cybersecurity", "build-in-public", "french-tech", "infosec"]
summary: "Plongée dans le fichier stack Borodino, le cœur orchestré du lab red-team Bojemoi : scanners distribués, C2 dual-framework, triage LLM et gestion des vulnérabilités, le tout sur Docker Swarm."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

## Un fichier YAML pour les gouverner tous

Le fichier `40-service-borodino.yml` est sans doute le plus dense du projet Bojemoi Lab. Résultat d'une fusion de huit fichiers sources distincts, il orchestre l'intégralité du pipeline offensif : de la découverte réseau jusqu'à la remontée des vulnérabilités dans DefectDojo, en passant par l'exploitation, le C2 et le triage automatisé par LLM. C'est à la fois la pièce maîtresse et le reflet honnête de toutes les décisions techniques (bonnes et moins bonnes) prises en cours de route.

Passons en revue ce que ce monstre fait vraiment.

---

## Architecture globale : le pipeline en couches

La stack se décompose en cinq couches fonctionnelles bien identifiables :

1. **Découverte** — `masscan-scanner` balaie des plages IP filtrées par pays (RU, BY, KZ par défaut) via ip2location, et stocke les résultats dans PostgreSQL/msf.
2. **Scan applicatif** — `zaproxy` + `zap-scanner` pour le DAST web, `nuclei` + `nuclei-api` + `nuclei-worker` pour les templates CVE/misconfiguration.
3. **Exploitation** — `ak47-service`, `bm12-service`, `uzi-service` (wrappeurs Metasploit/Sliver), `campagnewp-service` pour le ciblage WordPress.
4. **C2** — `sliver-server` + `sliver-worker` (Sliver gRPC), avec `msf-teamserver` référencé en externe et des redirecteurs Fly.io/Lightsail en façade.
5. **Reporting & triage** — DefectDojo (nginx + uWSGI + Celery), `dojo-triage` (Ollama/phi3:mini), `c2-monitor`, et Valkey comme bus de messages.

Ce qui est frappant, c'est la cohérence du flux de données : tout remonte dans PostgreSQL via le schéma msf, Valkey sert de queue inter-services, et DefectDojo centralise les findings. En théorie. En pratique, certains workers font encore du polling direct en base plutôt que de passer par la queue — c'est un dette technique assumée.

---

## Choix techniques notables

### YAML Anchors pour éviter la duplication

Le fichier exploite massivement les ancres YAML (`&arme-template`, `&deploy-template`, `&dojo-env`, etc.). C'est une approche propre pour factoriser les configurations répétitives. Les services `ak47`, `bm12`, `campagnewp` et `uzi` héritent tous du même template de base avec `<<: *arme-template`, ce qui garantit la cohérence des variables d'environnement PostgreSQL et de l'image de base.

Le template de déploiement `*deploy-template` normalise les contraintes Swarm : workers uniquement, max 5 réplicas par nœud, rollback automatique sur échec de mise à jour. C'est du bon sens opérationnel pour un cluster hétérogène.

### Masscan en mode `global`

`masscan-scanner` est déployé en mode `global` Swarm — une instance par worker. C'est intentionnel : chaque nœud scanne indépendamment, ce qui distribue la charge réseau. La configuration OpenVPN montée en bind (`/etc/openvpn/`) suggère que les workers sortent avec des IPs différentes. Pas parfait (on revient sur ce point), mais fonctionnel.

### Nym Mixnet comme proxy OSINT

`bm12-service` et `nuclei-api` exposent une variable `ALL_PROXY` / `NYM_PROXY` pointant vers `nym-proxy` (SOCKS5 sur port 1080). L'idée : anonymiser les appels aux APIs OSINT externes (AbuseIPDB, VirusTotal, Shodan) via le mixnet Nym. `nym-proxy` lui-même est déployé avec `replicas: 0` par défaut — on l'active manuellement. C'est honnête : le mixnet Nym ajoute une latence significative, on ne peut pas se permettre de le laisser actif en permanence pour tous les scans.

### Dual C2 : Metasploit + Sliver

C'est probablement le choix le plus intéressant. Plutôt que de tout miser sur Metasploit, la stack maintient deux frameworks C2 en parallèle :

- **Metasploit** via `uzi-service` (image `borodino-msf`) pour les modules d'exploitation et le brute-force multi-protocoles (SSH, FTP, Telnet, MySQL, MSSQL, SMB, IMAP, VNC, SNMP...). Les wordlists SecLists sont montées en lecture seule depuis l'hôte.
- **Sliver** via `sliver-server` + `sliver-worker` pour la gestion des sessions post-exploitation. Les implants générés sont partagés via un volume Docker entre le serveur et `uzi-service` (`SLIVER_ENABLED=true`).

La communication entre `uzi-service` et les redirecteurs externes (Fly.io `37.16.12.4` → VPN → Traefik:4444 → msf-teamserver) est documentée en commentaire. C'est rare et appréciable.

### Triage LLM avec Ollama

`dojo-triage` tourne toutes les 6 heures, récupère les findings DefectDojo en batch de 100, et les soumet à `phi3:mini` via Ollama pour une priorisation automatique. `OLLAMA_ENABLED=false` par défaut dans les workers nuclei — on tâte encore la pertinence des résultats. Honnêtement, phi3:mini sur des CVE techniques, c'est prometteur mais pas encore fiable à 100%.

### Karacho Blockchain API

`karacho-blockchain` est le service le plus mystérieux du lot. Une API Python qui expose un endpoint sur le port 5100, avec deux bases PostgreSQL distinctes (`karacho` et `msf`). Le nom et la structure suggèrent un mécanisme de licensing ou de sérialisation des engagements (d'où la config `ptaas_serial`). Les détails restent volontairement opaques dans cet article.

---

## Points d'amélioration : soyons honnêtes

**1. Le scan direct sans wg-gateway**
Le commentaire `# scan_net supprimé — wg-gateway retiré, scan direct depuis IP lab` mérite attention. La suppression du réseau WireGuard simplifie l'architecture, mais le scan sort désormais depuis les IPs du lab. Sur un homelab derrière une IP fixe résidentielle ou un VPS, ça laisse des traces très identifiables. Le mixnet Nym est là pour mitiger ça sur les appels OSINT, mais pas sur le scan masscan lui-même.

**2. `api.disablekey=true` sur ZAP**
ZAP tourne sans clé API sur le réseau interne. C'est acceptable dans un environnement isolé, mais si le réseau `pentest` est compromis ou mal segmenté, n'importe quel conteneur
