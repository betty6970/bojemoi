---
title: "Zéro credential en clair dans alertmanager.yml — Docker secrets à la rescousse"
date: 2026-03-14T21:00:00+00:00
draft: false
tags: ["cybersecurity", "devops", "docker", "docker-swarm", "homelab", "selfhosted", "infosec", "opensource", "blue-team", "soc", "gitops", "debutant-en-cyber", "apprendre-la-cyber", "build-in-public", "french-tech"]
summary: "Mon alertmanager.yml avait deux credentials en clair : un token Telegram et un mot de passe SMTP. Je les ai migrés vers des Docker secrets en dix minutes — sans patcher l'image ni écrire une ligne de script."
description: "Migration pas-à-pas de credentials Alertmanager vers des Docker secrets en Swarm mode : bot_token_file et smtp_auth_password_file, sans entrypoint personnalisé."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

J'ai intégré Trivy dans mon pipeline CI pour scanner mes Dockerfiles. Premier résultat : Trivy me signale des secrets hardcodés dans mon propre `alertmanager.yml` commité en clair dans le repo.

Ironie du sort — l'outil de scan de sécurité me trouve une faille dans ma configuration de monitoring.

## Le Problème

Mon `alertmanager.yml` contenait deux credentials en clair :

```yaml
global:
  smtp_auth_password: '8_qz7oZmQVBGhkvo-U64tA'   # mot de passe SMTP Proton Mail Bridge

receivers:
  - name: 'telegram-perimeter'
    telegram_configs:
      - bot_token: '8174135689:AAH...'             # token du bot Telegram
```

Ces deux valeurs étaient commitées dans le repo Git. Toute personne ayant accès au repo (ou à un backup) pouvait :

- Envoyer des messages à n'importe quel chat Telegram via le bot
- S'authentifier sur le serveur SMTP du bridge Protonmail

## La Solution Native d'Alertmanager

Alertmanager supporte nativement la lecture de credentials depuis des fichiers, via les paramètres suffixés `_file`. Pas besoin de script d'entrypoint, pas besoin de patcher l'image.

| Paramètre inline | Équivalent fichier |
|---|---|
| `bot_token` | `bot_token_file` |
| `smtp_auth_password` | `smtp_auth_password_file` |
| `api_key` (PagerDuty, etc.) | `api_key_file` |

La documentation Alertmanager liste ces variantes pour la plupart des intégrations. C'est la façon propre de gérer les secrets en environnement conteneurisé.

## Mise en Œuvre en Docker Swarm

### 1. Créer les secrets Docker

Le token Telegram existait déjà comme secret Swarm (`telegram_bot_token`, créé 6 semaines plus tôt pour le service Telegram). Réutilisation directe.

Pour le mot de passe SMTP, création d'un nouveau secret :

```bash
echo -n '8_qz7oZmQVBGhkvo-U64tA' | docker secret create alertmanager_smtp_pass -
```

```bash
docker secret ls | grep -E "telegram_bot|smtp"
# rfi2cjxk...   telegram_bot_token      6 weeks ago
# r5zodtm4...   alertmanager_smtp_pass  just now
```

### 2. Mettre à Jour alertmanager.yml

```yaml
global:
  smtp_auth_password_file: /run/secrets/alertmanager_smtp_pass   # ← fichier

receivers:
  - name: 'telegram-perimeter'
    telegram_configs:
      - bot_token_file: /run/secrets/telegram_bot_token           # ← fichier
```

Les credentials en clair disparaissent du fichier. Le repo est propre.

### 3. Monter les Secrets dans la Stack

Dans la définition du service alertmanager (`stack/01-service-hl.yml`) :

```yaml
services:
  alertmanager:
    # ...
    secrets:
      - telegram_bot_token
      - alertmanager_smtp_pass

secrets:
  telegram_bot_token:
    external: true
  alertmanager_smtp_pass:
    external: true
```

### 4. Appliquer sans Rebuild

Puisqu'il n'y a pas de changement d'image, un simple `service update` suffit :

```bash
# Première migration (bot token)
docker service update \
  --secret-add telegram_bot_token \
  --force \
  base_alertmanager

# Deuxième migration (SMTP)
docker service update \
  --secret-add alertmanager_smtp_pass \
  --force \
  base_alertmanager
```

Docker Swarm monte automatiquement les secrets dans `/run/secrets/<nom>` à l'intérieur du container. Alertmanager lit les fichiers au démarrage.

## Vérification

```bash
docker service ps base_alertmanager
# Running   21 seconds ago   ← pas de crash

docker service logs base_alertmanager --since 30s
# level=INFO msg="Loading configuration file" ...
# (pas d'erreur d'authentification)
```

Et dans `alertmanager.yml` désormais commité :

```yaml
global:
  smtp_auth_password_file: /run/secrets/alertmanager_smtp_pass

receivers:
  - name: 'telegram-perimeter'
    telegram_configs:
      - bot_token_file: /run/secrets/telegram_bot_token
```

Aucun credential en clair. Trivy est content.

## Ce que Docker Swarm Garantit sur les Secrets

- Les secrets sont chiffrés au repos (dans la Raft store) et en transit (TLS mutuel entre les nœuds)
- Montés en `tmpfs` dans le container — jamais écrits sur disque
- Visibles uniquement par les tâches qui en ont besoin (déclaration explicite dans le service)
- Non récupérables via `docker secret inspect` (seulement les métadonnées)

Pour les faire tourner sur les bons nœuds, les contraintes de placement Swarm font déjà le travail.

## Generalisation

Ce pattern `*_file` n'est pas propre à Alertmanager. On le retrouve dans :

- **Prometheus** : `bearer_token_file`, `password_file` dans les scrape configs
- **Grafana** : `GF_DATABASE_PASSWORD__FILE`, `GF_SECURITY_ADMIN_PASSWORD__FILE`
- **Loki** : idem via les variables d'environnement `_FILE`
- **Traefik** : les providers supportent les fichiers de secrets

Le principe est identique : paramètre standard remplacé par son équivalent `_file` pointant vers `/run/secrets/<nom>`.

## Bilan

| | Avant | Après |
|---|---|---|
| Credentials dans le repo | ✗ 2 en clair | ✓ 0 |
| Alertmanager fonctionnel | ✓ | ✓ |
| Changement d'image requis | — | Non |
| Script d'entrypoint custom | — | Non |
| Temps de migration | — | ~15 min |

La leçon : avant d'écrire un script de substitution de variables ou de patcher une image, vérifier si l'outil ne supporte pas déjà nativement la lecture depuis des fichiers. Alertmanager, Prometheus, Grafana — la plupart des outils de l'écosystème Prometheus le font.
