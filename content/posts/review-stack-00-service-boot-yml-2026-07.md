---
title: "Bojemoi Lab — Décryptage de la stack de boot : DNS, reverse proxy et registry Docker Swarm"
date: 2026-07-21
draft: false
tags: ["homelab", "docker", "cybersecurity", "build-in-public", "french-tech", "infosec"]
summary: "Analyse technique du fichier `00-service-boot.yml` de Bojemoi Lab, la stack fondatrice qui orchestre DNS, Traefik, Docker Registry et sécurité des sockets dans un environnement Docker Swarm orienté red team."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

## Pourquoi une stack "boot" ?

Dans un homelab red team, tout le reste dépend de quelques composants fondamentaux : le DNS qui résout vos domaines internes, le reverse proxy qui route le trafic, et le registry qui stocke vos images custom. Si l'un d'eux tombe, c'est toute l'infrastructure qui s'effondre.

C'est exactement le rôle de `00-service-boot.yml` dans Bojemoi Lab. Ce fichier est délibérément numéroté `00` — il se déploie en premier, avant toutes les autres stacks. Il pose les fondations sur lesquelles tout le reste repose. Voici ce qu'il contient, pourquoi ces choix ont été faits, et ce qui pourrait être amélioré.

---

## Vue d'ensemble de l'architecture réseau

La première chose qui frappe à la lecture du fichier, c'est la liste des réseaux déclarés en `external` :

```yaml
networks:
  monitoring:
  backend:
  proxy:
  rsync_network:
  mail:
  pentest:
  iot:
  telegram_net:
```

Huit réseaux externes. Tous pré-créés en dehors de cette stack. C'est un choix architectural fort : **les réseaux sont des ressources de première classe**, pas des sous-produits d'une stack. Cela évite les dépendances circulaires entre stacks et permet à chaque service de rejoindre exactement les réseaux dont il a besoin — ni plus, ni moins.

Le réseau `pentest` et le réseau `iot` cohabitent dans la même déclaration que `monitoring` et `backend`. C'est une bonne illustration de la philosophie du lab : des périmètres séparés mais orchestrés depuis un seul plan de contrôle.

---

## Le Docker Socket Proxy : la bonne pratique qu'on oublie trop souvent

Le service `docker-socket-proxy` mérite une attention particulière. C'est souvent le premier service sacrifié dans les homelabs par souci de simplicité — on monte directement `/var/run/docker.sock` dans Traefik et on passe à autre chose. Ici, on a fait le choix inverse.

```yaml
docker-socket-proxy:
  image: tecnativa/docker-socket-proxy:0.2.0
  environment:
    - POST=1
    - DELETE=1
    - CONTAINERS=1
    - SERVICES=1
    - TASKS=1
    - NETWORKS=1
    - NODES=1
    - IMAGES=1
    - VOLUMES=1
    - INFO=1
    - SWARM=1
```

Le principe est simple : au lieu d'exposer le socket Docker brut (qui donne accès root complet à la machine hôte), on passe par un proxy HTTP qui filtre les appels à l'API Docker. Traefik, au lieu de parler directement au socket Unix, passe par `tcp://docker-socket-proxy:2375`.

**Ce que ça change concrètement :** si Traefik est compromis, l'attaquant ne peut pas spawner des containers arbitraires ou monter le système de fichiers hôte via l'API Docker. Le rayon d'explosion est limité.

Ce qui me gêne légèrement dans la configuration actuelle : `POST=1` et `DELETE=1` sont activés, ce qui autorise des opérations en écriture. Pour Traefik en mode Swarm, c'est techniquement nécessaire — mais ça mérite d'être documenté explicitement. Dans un contexte red team où ce proxy protège aussi potentiellement des agents C2 ou des scanners, durcir ces permissions serait une bonne prochaine étape.

---

## DNSMasq : le DNS interne du lab

```yaml
dnsmask:
  image: jpillora/dnsmasq:latest
  ports:
    - 53:53/udp
    - 53:53/tcp
```

DNSMasq sert ici à résoudre les domaines `.bojemoi.lab` en interne. L'UI web (webproc) est exposée uniquement via Traefik sous `dnsmasq.bojemoi.lab` — le port 8080 n'est plus publié directement. C'est un bon réflexe : toutes les interfaces d'administration passent par le reverse proxy avec TLS.

Un point à noter : l'image `jpillora/dnsmasq:latest` n'est pas pinnée sur un digest. Dans un environnement de lab red team, utiliser `latest` sur un service aussi critique que le DNS est un risque acceptable — mais dans un vrai déploiement, une mise à jour silencieuse pourrait casser la résolution DNS de toute l'infrastructure. À améliorer.

---

## Traefik : le reverse proxy avec Let's Encrypt DNS-01

Traefik est déployé en mode `global` sur les managers, ce qui signifie qu'il tourne sur chaque nœud manager du Swarm. La configuration est intéressante à plusieurs titres.

### Let's Encrypt via DNS-01 et Route53

```yaml
- --certificatesresolvers.letsencrypt.acme.dnschallenge=true
- --certificatesresolvers.letsencrypt.acme.dnschallenge.provider=route53
```

Le challenge DNS-01 via Route53 permet d'obtenir des certificats wildcard Let's Encrypt sans exposer le port 80 sur internet. C'est la bonne approche pour un homelab avec des domaines internes — les domaines `.bojemoi.lab` ne sont pas résolvables publiquement, mais si des sous-domaines publics sont utilisés, le challenge DNS fonctionne parfaitement.

Les credentials AWS sont passés via Docker Secrets, ce qui est correct. Ils ne transitent pas par les variables d'environnement en clair dans l'image.

### L'entrypoint Meterpreter

```yaml
- --entrypoints.meterpreter.address=:4444
```

C'est la touche red team du fichier. Le port 4444 — le port par défaut de Meterpreter — est exposé directement via Traefik. Bojemoi Lab assume clairement son positionnement : c'est un lab offensif, et le reverse proxy route aussi le trafic C2.

### Basic Auth sur le dashboard

```yaml
- traefik.http.middlewares.traefik-auth.basicauth.users=admin:$$apr1$$cwwK8JxY$$...
```

Le hash est dans les labels Docker. C'est fonctionnel mais pas idéal — le hash est visible pour quiconque peut lister les services Swarm (`docker service inspect`). Une amélioration serait de passer ce hash via un Docker Secret et de l'injecter dans un fichier de configuration dynamique Traefik.

---

## La gestion des secrets : un inventaire impressionnant

La section `secrets` du fichier liste 27 secrets externes :

- Clés API (Shodan, VirusTotal, OTX, AbuseIPDB, Anthropic)
- Tokens Telegram, Discord, Gitea
- Credentials Metasploit RPC, Defect Dojo
- Clés SSH, tokens Fly.io, credentials AWS

Tous sont déclarés `external: true`, ce qui signifie qu'ils doivent être créés manuellement (ou via `scripts/create-secrets.sh`) avant le déploiement. C'est la b
