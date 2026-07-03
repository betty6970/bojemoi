---
title: "thearm_bm12 : un scanner de fingerprinting profond qui classe les serveurs tout seul"
date: 2026-07-03
draft: false
tags: ["homelab", "docker", "cybersecurity", "build-in-public", "french-tech", "infosec"]
summary: "Plongée technique dans thearm_bm12, le module du lab Bojemoi qui scanne, classe et enrichit automatiquement les hôtes découverts via des scripts NSE ciblés et un lookup OSINT."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

## Le rôle de thearm_bm12 dans la chaîne

Dans le pipeline d'attaque de Borodino (`ak47 → bm12 → uzi → zap → nuclei → sliver`), chaque maillon a une responsabilité unique. `thearm_bm12` occupe la deuxième position : il prend le relais après la phase de découverte massive et transforme une liste brute d'hôtes en fiches d'identité exploitables.

Concrètement, le script pioche un hôte dans la base PostgreSQL de Metasploit (`msf`), regarde quels ports/services y sont ouverts, lance un scan `nmap` **ciblé** avec les bons scripts NSE, puis en déduit trois choses : le **rôle du serveur** (web, mail, base de données, IoT…), son **architecture CPU**, et une **surface d'attaque** probable. Le tout est enrichi par un lookup OSINT (threat score, réputation, pays) avant d'être réécrit en base pour que le maillon suivant, `uzi`, sache quoi faire.

L'idée directrice : ne pas rescanner bêtement le monde entier avec `--script "*"`, mais appliquer la bonne sonde au bon service. C'est plus rapide, plus discret, et ça génère beaucoup moins de bruit.

## Les choix techniques que je trouve intéressants

### Des scripts NSE par catégorie, pas de wildcard

Le cœur du module est le dictionnaire `NSE_SCRIPTS`. À chaque famille de service correspond une liste précise de scripts. Pour du HTTP par exemple : `ssl-cert`, `http-headers`, `http-shellshock`, `http-webdav-scan`… Le commentaire dans le code est explicite : *« Scripts ciblés au lieu du wildcard dangereux `{service}*` »*. J'ai appris ça à mes dépens — un `http-*` peut embarquer des scripts intrusifs ou lents qui font exploser le temps de scan et lèvent des alertes IDS inutiles.

Quand le nom de service renvoyé par nmap est générique (un `unknown` ou un `tcpwrapped`), le fallback `NSE_BY_PORT` mappe le numéro de port vers une catégorie connue. Détail que j'aime bien : le port `5985` est mappé sur `http` avec le commentaire « WinRM uses HTTP transport ». Ce genre de petit savoir métier accumulé est ce qui fait la différence entre un scanner générique et un scanner qui connaît le terrain.

### Une classification pondérée plutôt qu'un simple "premier match"

`classify_server()` ne se contente pas de dire « il y a du port 80, donc c'est un serveur web ». Chaque rôle a un **poids** dans `SERVER_ROLES`. Le `remote_access` (SSH, RDP) a un poids de `0` — un choix délibéré, commenté : *« presque tous les serveurs ont SSH, ne pas surpondérer »*. À l'inverse, `vpn_proxy` et `voip` pèsent `3`, car leur présence est bien plus discriminante. Le score final produit une **confiance en pourcentage** (`top_score / total`), ce qui donne un signal exploitable plutôt qu'un label binaire.

### Le fingerprinting par banner, là où NSE s'arrête

Deux fonctions font le vrai travail d'analyse post-scan :

- `detect_arch_and_iot()` parcourt les banners (`services.info`) avec une liste de regex ordonnées du plus spécifique au plus générique (`aarch64` avant `arm`, `mipsel` avant `mips`). En parallèle, une liste de mots-clés IoT (`openwrt`, `rompager`, `hikvision`, `broadcom`…) permet de **surclasser** un hôte en `iot_embedded` même si sa signature de ports était ambiguë.
- `detect_vuln_indicators()` cherche des marqueurs de vulnérabilités façon VulnHub (`vsftpd 2.3.4`, `wp-login`, `phpmyadmin`, `open relay`…) tout en vérifiant que le port correspond bien au hint attendu, pour limiter les faux positifs.

Le résultat de ces heuristiques peut faire basculer le type vers `vuln_web`, ce qui alimente ensuite la priorisation des cibles pour nuclei.

### Un nmap "furtif" en une seule passe

`build_nmap_command()` fusionne tous les ports d'un hôte dans **une seule** commande, avec de l'évasion réseau intégrée : `--spoof-mac 0`, `-f --mtu 16`, `--data-length 64`, `--randomize-hosts`. La sortie est en XML sur stdout (`-oX -`), parsée directement en Python — pas de fichier temporaire, pas de `msfconsole` à piloter. Simple et efficace.

## Les points d'amélioration (soyons honnêtes)

Le build-in-public, c'est aussi montrer les coutures.

- **`subprocess.run(["/bin/sh", "-c", nmap_cmd])`** : la commande est construite par f-string. Ici les entrées viennent de la base et de nmap, donc le risque est théorique — mais passer un jour à `subprocess.run([...])` avec une liste d'arguments serait plus propre et éliminerait toute surface d'injection.
- **La gestion des connexions DB** : chaque helper ouvre et ferme sa propre connexion PostgreSQL. Sur un hôte avec beaucoup de services, on multiplie les allers-retours. Un pool de connexions (voire une seule connexion passée en paramètre) réduirait la latence et la charge sur Postgres.
- **Les regex de détection** sont puissantes mais fragiles : un banner tronqué à 1000 caractères peut couper la preuve d'une vuln. Et `evidence` est limité à 120 caractères, ce qui est parfois trop court pour du contexte réel.
- **Le `TABLESAMPLE SYSTEM(0.001)`** est astucieux pour piocher un hôte au hasard sans scanner toute la table, mais sur une base peu peuplée il peut renvoyer vide plusieurs fois de suite avant le fallback à `0.01`. Acceptable, mais à surveiller quand la base grossit.
- **Pas de rate limiting global** : chaque itération scanne un hôte, mais rien ne modère la cadence à l'échelle du swarm si plusieurs répliques tournent. Un verrou distribué ou une file serait le prochain chantier logique.

## Ce que j'en retiens

`thearm_bm12` est un bon exemple de « scanner qui pense ». Il ne se contente pas de balancer nmap : il pondère, classe, corrèle des banners et branche de l'OSINT pour prioriser. Les heuristiques codées en dur sont à la fois sa force (elles encodent du savoir terrain réel) et sa limite (elles vieillissent, il faut les maintenir). Pour un lab red-team open source, c'est exactement le bon niveau de compromis : lisible, hackable, et suffisamment précis pour alimenter la suite du pipeline sans noyer nuclei sous les faux positifs.

Le prochain pas ? Externaliser ces dictionnaires NSE et ces regex dans un fichier de config versionné, pour itérer sur les signatures sans toucher au code. À suivre.
