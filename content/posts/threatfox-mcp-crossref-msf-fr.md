---
title: "Construire son propre Falcon MCP : ThreatFox + Cross-Référence sur 6 millions d'hôtes"
date: 2026-08-06T23:00:00+00:00
draft: false
tags: ["threat-intelligence", "cybersecurity", "osint", "infosec", "homelab", "docker-swarm", "docker", "devops", "selfhosted", "opensource", "build-in-public", "french-tech", "apprendre-la-cyber", "debutant-en-cyber", "cobalt-strike", "c2", "mcp", "red-team"]
summary: "J'ai vu un post sur Dread décrivant l'usage des flux Falcon MCP pour tracker des C2 APT. Ce soir, j'ai reproduit ça avec mes propres sources gratuites — et trouvé un C2 Cobalt Strike actif dans ma base."
description: "Comment construire un serveur MCP avec ThreatFox (abuse.ch) pour croiser des IOCs C2 avec une base de 6 millions d'hôtes scannés, en partant de zéro avec des outils gratuits."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

Ce soir j'ai lu un post qui décrivait quelque chose d'intéressant : quelqu'un utilise les flux CrowdStrike Falcon via MCP pour interroger en langage naturel leur base de threat intelligence — APT12, Calypso, Pegasus, DarkHotel — et obtenir des listes d'IOCs C2 catégorisés par acteur.

Falcon coûte une fortune. Mais le principe est simple. Et j'avais déjà l'infrastructure pour faire pareil.

Ce post raconte comment j'ai construit l'équivalent en quelques heures, avec des sources gratuites, et ce que j'ai trouvé.

## C'est quoi MCP ?

MCP (Model Context Protocol) est un standard développé par Anthropic qui permet à un LLM de se connecter à des outils externes en temps réel. Quand je discute avec Claude Code, il peut appeler des outils — lancer un scan nmap, interroger ma base Metasploit, chercher des CVEs — parce que mon infrastructure expose ces capacités via un serveur MCP.

C'est exactement ce que CrowdStrike a fait : ils ont branché leur plateforme Falcon sur ce protocole. L'opérateur demande "montre-moi les C2 d'APT12 actifs cette semaine" et le LLM interroge Falcon automatiquement.

La différence avec un simple chatbot : les données sont **fraîches** et **contextualisées** à votre infra.

## Mon infrastructure de départ

J'ai un homelab Docker Swarm avec :
- Un serveur MCP maison (`mcp-server`) exposant une trentaine d'outils
- Une base Metasploit PostgreSQL avec **6,15 millions d'hôtes** scannés et leurs services
- Un pipeline de scanning automatique (masscan → classification → exploit → nuclei)

Le serveur MCP avait déjà `lookup_ip` qui interroge OTX pour une IP individuelle. Ce qui manquait : la **dimension flux** — interroger des feeds pour trouver des acteurs, des C2 connus, et surtout croiser ça avec ma propre base.

## Les sources gratuites

Deux sources abuse.ch, gratuites et bien maintenues :

**ThreatFox** — base d'IOCs C2 avec confiance, famille malware, tags de campagne. Nécessite une inscription gratuite pour l'API. Des milliers d'IOCs récents : Cobalt Strike, Sliver, Metasploit stagers, botnets.

**Feodo Tracker** — liste des C2 de botnets (Emotet, QakBot, IcedID). Complètement public, pas d'authentification. Moins d'entrées mais zéro friction.

## Ce qu'on a construit

Trois fonctions dans un nouveau module `bojemoi/cti.py` :

```python
threatfox_recent(days=7, ioc_type=None, malware=None)
# → IOCs récents, filtrables par type et famille malware

threatfox_search(ioc)
# → Est-ce que cette IP/domaine/hash est connue comme C2 ?

ioc_crossref(days=7, malware=None, min_confidence=50)
# → KILLER FEATURE
```

La killer feature c'est `ioc_crossref`. Le principe :

1. Récupérer les IOCs `ip:port` récents de ThreatFox
2. Extraire les IPs uniques
3. Une seule requête SQL sur les 6,15M hosts :

```sql
SELECT host(address::inet), os_name, scan_status, last_scanned
FROM hosts
WHERE host(address::inet) = ANY($1)
```

4. Retourner les matches avec le contexte des deux côtés (ce que ThreatFox sait + ce que mon scanner a vu)

Si un hôte que j'ai scanné correspond à un C2 connu — je le sais immédiatement.

## Le résultat

Premier test avec `ioc_crossref(days=2)` :

```
Source       : threatfox
IOCs uniques : 267
HITS MSF     : 1

  45.8.159.205  |  Cobalt Strike  |  scan_status: None
```

Un hit. `45.8.159.205`, C2 Cobalt Strike, port 8596, signalé la veille avec confiance 75% et tag `drb-ra`.

L'IP était dans ma base depuis mai 2026 — mon scanner masscan l'avait touchée — mais sans scan approfondi (status null).

## Confirmation manuelle

Scan nmap :

```
22/tcp    open   ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.7
8596/tcp  open   unknown
```

Sonde HTTP sur 8596 :

```
GET /  →  HTTP/1.1 404 Not Found
         Content-Type: text/plain
         Content-Length: 0
         [pas de header Server]

OPTIONS /  →  HTTP/1.1 200 OK
              Content-Type: text/html
              Allow: OPTIONS,GET,HEAD,POST
```

C'est la signature classique d'un **Cobalt Strike Malleable C2 HTTP profile** :
- 404 vide sur GET (requêtes non-beacon rejetées silencieusement)
- 200 sur OPTIONS (heartbeat beacon)
- Pas de header `Server` (obfuscation)
- Port 50050 fermé (UI teamserver non exposée — opérateur prudent)

Ubuntu 18.04 EOL. ASN AS49392 LLC Baxet, Moscou. Tag `drb-ra` = marqueur de campagne identifié dans la communauté CTI.

Finding documenté dans DefectDojo.

## Ce que ça change

La cross-référence est la partie qui m'intéresse le plus. Je ne cherche pas à savoir si une IP *existe* dans ThreatFox — je peux faire ça avec `lookup_ip`. Je veux savoir si parmi les millions d'hôtes que j'ai déjà scannés, certains sont de l'infrastructure C2 connue.

C'est une question différente, et la réponse change ce qu'on fait ensuite. Un hôte déjà dans ma base avec des services connus est immédiatement explorable — je connais déjà ses ports ouverts, son OS, son contexte.

La prochaine étape logique : automatiser ce cross-ref quotidiennement et alerter via Telegram quand un nouveau match apparaît.

## Reproduire ça

Tout ce qu'il faut :

- Un serveur MCP Python (le code est sur mon Gitea)
- Une clé ThreatFox gratuite (inscription sur threatfox.abuse.ch)
- Une base de données d'hôtes scannés (ou Shodan/Censys si vous n'avez pas de scanner)

La logique de cross-référence fonctionne avec n'importe quelle base SQL. Si vous avez une liste d'IPs que vous connaissez, vous pouvez la croiser avec ThreatFox en quelques lignes.

---

*Infrastructure : Docker Swarm, Python, PostgreSQL, ThreatFox API, abuse.ch Feodo Tracker*
