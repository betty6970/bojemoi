---
title: "Suricata en mode host sur Docker Swarm : pourquoi on triche (et pourquoi c'est OK)"
date: 2026-07-23
draft: false
tags: ["homelab", "docker", "cybersecurity", "build-in-public", "french-tech", "infosec"]
summary: "Analyse du stack Suricata de Bojemoi Lab : comment intégrer un IDS/IPS en network_mode host dans un environnement Docker Swarm, avec exporter Prometheus et nettoyage automatique des logs."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

## TL;DR

Suricata ne joue pas bien avec Docker Swarm. On le sait. On a quand même trouvé un compromis fonctionnel, et cet article explique pourquoi on a fait ces choix — y compris les moins glorieux.

---

## Le problème fondamental : Swarm et la capture réseau

Docker Swarm est excellent pour orchestrer des services applicatifs. Mais dès qu'on veut faire de la capture de paquets **à la couche physique**, les choses se compliquent sérieusement.

Un service Swarm tourne dans un réseau overlay (`ingress` ou custom). Les paquets qu'il voit sont déjà encapsulés, NATés, transformés. Pour un IDS comme Suricata, c'est rédhibitoire : tu n'analyses plus le trafic réel, tu analyses l'ombre d'un trafic.

La solution honnête ? **Sortir Suricata du Swarm et lui donner accès direct à l'interface réseau physique.**

C'est ce que fait `stack/01-suricata-host.yml` — et c'est assumé dès le premier commentaire du fichier :

```yaml
# Suricata IDS/IPS — standalone docker compose (NOT Swarm)
# Requires network_mode: host for real packet capture on eth0.
```

---

## Architecture du stack : trois rôles, trois conteneurs

### 1. `suricata` — le moteur IDS/IPS

```yaml
network_mode: host
cap_add:
  - NET_ADMIN
  - SYS_NICE
  - NET_RAW
```

`network_mode: host` est le choix central. Le conteneur partage la stack réseau du nœud hôte. Suricata peut ainsi écouter sur `eth0` directement, comme s'il était installé en bare-metal.

Les capabilities ajoutées sont les trois pilliers de la capture réseau sous Linux :
- **NET_RAW** : ouvrir des raw sockets, lire les paquets bruts
- **NET_ADMIN** : manipuler les interfaces (mode promiscuité, règles nftables si IPS)
- **SYS_NICE** : ajuster la priorité des threads de capture pour éviter les drops sous charge

Les options Suricata méritent attention :

```yaml
SURICATA_OPTIONS=-i eth0 --set stream.reassembly.depth=0 --set detect.profile=low
```

- `stream.reassembly.depth=0` : pas de limite sur la profondeur de réassemblage TCP. En homelab avec peu de RAM, c'est un pari — ça peut consommer beaucoup sur des transferts massifs. À monitorer.
- `detect.profile=low` : profil de détection économique. On sacrifie de la couverture pour des performances acceptables sur du matériel modeste. C'est honnête pour un lab.

### 2. `suricata-exporter` — le pont vers Prometheus

Ce conteneur lit les métriques Suricata via son **Unix socket** (`suricata-command.socket`) et les expose au format Prometheus. C'est un pattern propre : Suricata ne connaît pas Prometheus, l'exporter fait le pont sans modifier le moteur.

```yaml
command:
  - '--suricata.socket-path=/var/run/suricata/suricata-command.socket'
```

La communication passe par un volume partagé monté en lecture seule côté exporter. Le `depends_on` garantit que Suricata démarre en premier — même si ça ne garantit pas que le socket existe déjà au moment où l'exporter tente de s'y connecter. Un `restart: unless-stopped` compense ce race condition de démarrage.

L'exporter rejoint le réseau `monitoring` (externe, donc géré par le Swarm), ce qui lui permet d'être scraped par Prometheus même si le reste du stack est hors Swarm.

### 3. `eve-cleaner` — gestion des logs à l'ancienne

C'est le composant le plus artisanal — et probablement le plus honnête du stack.

Suricata génère un fichier `eve.json` en append continu. Il n'y a **pas de rotation native** du fichier actif dans Suricata (contrairement aux fichiers horodatés qu'il crée lui-même). Résultat : sans intervention, `eve.json` grossit indéfiniment.

La solution ici : un conteneur Alpine qui tourne une boucle shell toutes les heures.

```sh
# Suppression des fichiers archivés de plus de 48h
AGE_H=$(( (NOW - MTIME) / 3600 ))
if [ "$AGE_H" -ge "$KEEP_HOURS" ]; then rm -f "$f"; fi

# Troncature de eve.json si > 5GB
if [ "$EVE_KB" -ge "$MAX_KB" ]; then truncate -s 0 "$EVE"; fi
```

Points notables :
- `truncate -s 0` plutôt que `> file` ou `rm` : Suricata conserve son file descriptor ouvert, la troncature vide le fichier sans casser le handle. C'est le bon geste.
- La compatibilité `stat` est gérée avec deux syntaxes (`-c %Y` Linux, `-f %m` macOS) — vestige probable de dev en local sur Mac.
- Le logging de l'opération est verbose et structuré, ce qui est bien pour le debug.

---

## Ce qui manque (et on le sait)

### Déploiement multi-nœuds manuel

Le commentaire dit tout : `Deploy on each node: docker compose -f stack/01-suricata-host.yml up -d`. Il n'y a pas d'automatisation de déploiement sur plusieurs nœuds. Sur un cluster de 5 machines, c'est 5 commandes SSH manuelles. Un Ansible playbook serait le prochain palier évident.

### Le race condition au démarrage

`suricata-exporter` démarre après `suricata` mais le socket Unix peut mettre quelques secondes à apparaître. Les premières tentatives de connexion échouent. Le `restart: unless-stopped` rattrape ça, mais c'est du bricolage. Une `healthcheck` sur Suricata testant l'existence du socket serait plus propre.

### `detect.profile=low` en production

Acceptable pour un lab, problématique pour une vraie infrastructure. Ce paramètre réduit la précision de certaines détections comportementales. À revoir si le lab évolue vers de la détection d'incidents réels.

### L'enrichissement des alertes est ailleurs

Le commentaire final pointe vers `stack/01-service-hl.yml` pour le `suricata-attack-enricher`. Ce découpage est logique (l'enrichisseur a besoin du réseau overlay Swarm et des secrets), mais ça crée une dépendance inter-fichiers non évidente à l'onboarding.

---

## Ce qu'on retient

Ce fichier est un bon exemple de pragmatisme en homelab : on fait ce qui marche, on documente les compromis, et on ne prétend pas que c'est parfait. `network_mode: host` dans un environnement Swarm n'est pas élégant, mais c'est la seule façon d'avoir un IDS qui voit vraiment le trafic.

L'
