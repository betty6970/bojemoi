---
title: "Anatomie du stack high-level Bojemoi : orchestration d'un lab red-team sous Docker Swarm"
date: 2026-07-22
draft: false
tags: ["homelab", "docker", "cybersecurity", "build-in-public", "french-tech", "infosec"]
summary: "Décryptage du fichier 01-service-hl.yml, le cœur observable du lab Bojemoi : comment on orchestre une vingtaine de services de monitoring, backup et sécurité offensive sur Docker Swarm sans se tirer une balle dans le pied."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

## C'est quoi ce fichier, concrètement ?

`01-service-hl.yml` est le deuxième stack déployé dans Bojemoi Lab, juste après `00-service-boot.yml` qui gère l'infrastructure de base (Traefik, CrowdSec, registry local). Ce fichier définit tous les services *applicatifs* du lab : la stack d'observabilité complète (Prometheus, Loki, Grafana, Tempo, Alloy), la messagerie (Postfix + Protonmail Bridge), la base de données centrale, le système de backup, et l'orchestrateur de provisioning.

En gros : si `00` pose les fondations réseau, `01` construit les murs. C'est là que le lab devient utilisable pour du travail red-team réel.

---

## Architecture des réseaux : isolation par usage

Le fichier déclare six réseaux Docker Swarm externes, tous créés en amont :

| Réseau | Usage |
|---|---|
| `proxy` | Trafic Traefik (exposition HTTP/HTTPS) |
| `backend` | Communication inter-services interne |
| `monitoring` | Scraping Prometheus, push Loki |
| `rsync_network` | Réplication de données master/slave |
| `mail` | Isolation de la chaîne email |
| `host` | node-exporter en mode réseau host |

C'est un pattern d'isolation solide. Chaque service n'est connecté qu'aux réseaux dont il a besoin — Postfix parle à `mail`, `backend` et `monitoring`, mais pas à `proxy` directement. Grafana, lui, touche les trois premiers. Cette segmentation limite la surface d'attaque latérale si un container est compromis.

**Ce qu'on aurait pu mieux faire** : le réseau `host` pour node-exporter expose le container au réseau physique de l'hôte. C'est intentionnel (pour collecter les métriques système réelles), mais ça reste un vecteur si l'image est compromise.

---

## Le système de secrets : Docker Swarm Secrets à fond

Tous les secrets sont `external: true`, créés via un script dédié `/opt/bojemoi/scripts/create-secrets.sh`. On compte 14 secrets gérés proprement :

```yaml
secrets:
  postgres_password:
    external: true
  telegram_bot_token:
    external: true
  grafana_admin_password:
    external: true
  # ... etc
```

Les mots de passe ne transitent jamais en clair dans les variables d'environnement — ils sont montés dans `/run/secrets/` et lus via `_FILE` suffixé (pattern standard Postgres, Grafana). C'est la bonne approche pour du Swarm en production.

**Limitation honnête** : pgadmin a `PGADMIN_DEFAULT_PASSWORD: bojemoi` en clair dans l'environnement. C'est un outil admin interne, mais c'est un écart de cohérence notable par rapport au reste du stack. À corriger.

---

## La stack d'observabilité : le vrai cœur du lab

### Prometheus → Loki → Tempo → Grafana

La chaîne suit le modèle LGTM (Loki, Grafana, Tempo, Mimir/Prometheus) de Grafana Labs :

- **Prometheus** : 15 jours de rétention, 10 GB max, compression WAL activée, remote-write receiver ouvert (pour les agents externes)
- **Loki** : exposition en mode `host` sur 3100, ce qui simplifie la collecte depuis les workers
- **Tempo** : ingestion multi-protocole (OTLP gRPC 4317, OTLP HTTP 4318, Zipkin 9411) — utile pour instrumenter des outils red-team custom
- **Grafana** : backend PostgreSQL (pas SQLite), plugins dynamiques via `GF_INSTALL_PLUGINS`

### Alloy : collecte à deux vitesses

Un pattern intéressant : deux instances d'Alloy avec des configs distinctes.

```yaml
alloy:          # manager — lit les logs rsync + /opt/bojemoi/logs
alloy-worker:   # mode global sur workers — lit /var/run/docker.sock directement
```

L'instance manager passe par le `docker-socket-proxy` (hérité du stack boot), l'instance worker monte le socket Docker en direct (`ro`). C'est un compromis pragmatique : sur les workers on accepte l'accès socket, sur le manager on passe par le proxy pour éviter l'exposition de l'API Docker complète.

---

## PostgreSQL SSL : un effort réel de durcissement

```yaml
command: >
  postgres
  -c ssl=on
  -c ssl_cert_file=/var/lib/postgresql/ssl/server.crt
  -c ssl_key_file=/var/lib/postgresql/ssl/server.key
  -c ssl_ca_file=/var/lib/postgresql/ssl/ca.crt
  -c hba_file=/etc/postgresql/pg_hba.conf
  -c shared_preload_libraries=pg_stat_statements
```

SSL mutuel activé, certificats injectés via Docker configs avec les bons UID/GID (999 = utilisateur postgres), `pg_hba.conf` externe, `pg_stat_statements` pour le monitoring de requêtes. C'est du niveau production pour un homelab.

Le port 5432 est exposé en mode `host` avec une note explicite : *"bind sur l'interface physique du manager — pas d'exposition internet"*. C'est honnête et pragmatique, même si ça suppose une confiance totale dans l'isolation réseau physique.

---

## La chaîne mail : Postfix → Protonmail Bridge

Un choix original : utiliser Protonmail comme relay SMTP chiffré de bout en bout depuis un lab red-team. La chaîne est :

```
services → Postfix (port 25) → Protonmail Bridge (port 1025) → Proton Mail
```

Un `mail-watchdog` teste la chaîne complète toutes les 10 minutes et expose des métriques Prometheus sur le port 9355. C'est exactement le genre de test end-to-end qu'on néglige en général.

**Limitation connue** : le `main.cf` de Postfix ne peut pas être injecté via Docker config (le commentaire dans le fichier l'explique — `postconf` modifie le fichier et les configs Docker sont read-only). La configuration passe donc par des variables d'environnement. Fonctionnel, mais moins auditable.

---

## Le système de backup rsync : master/slave sur Swarm

```yaml
rsync-master:
  deploy:
    placement:
      constraints:
        - node.role == manager

rsync-slave:
  deploy:
    mode: global
    placement:
      constraints:
        - node.labels.rsync.slave == true
```

Les slaves se déploient sur tous les nodes labellisés `rsync.slave=true`. Le master synchronise `/opt/bojemoi` toutes les 5 minutes vers les slaves. L'accès SSH est géré via un volume `ssh_keys` partagé.

**Pattern YAML intéressant** : l'utilisation des ancres YAML (`&mode-template`, `&deploy-template`) pour factoriser la configuration commune des services rsync. C'est propre et réd
