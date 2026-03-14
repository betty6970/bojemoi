---
title: "Charité bien ordonnée : scanner ses propres Dockerfiles avec Trivy dans Gitea Actions"
date: 2026-03-03T20:00:00+00:00
draft: false
tags: ["cybersecurity", "devops", "docker", "gitops", "homelab", "selfhosted", "infosec", "opensource", "debutant-en-cyber", "apprendre-la-cyber", "build-in-public", "french-tech", "blue-team", "soc"]
summary: "J'intègre Trivy dans mon pipeline Gitea Actions pour scanner automatiquement mes 30+ Dockerfiles et stacks Docker Swarm à chaque push. Premier constat : mon propre infra avait des gaps évidents."
description: "Retour d'expérience sur l'intégration de Trivy dans Gitea Actions pour scanner misconfigurations IaC et secrets exposés — sans base de vulnérabilités, sur un runner Lightsail 916 MB RAM."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

Charité bien ordonnée commence par soi-même.

Je gère un homelab offensif — scans nmap massifs, exploitation Metasploit, threat intelligence. Mais mes propres Dockerfiles et stacks Docker Swarm n'avaient aucun scan de sécurité automatisé. Pas très cohérent.

## Pourquoi Trivy ?

Trivy est un scanner de sécurité open source d'Aqua Security qui couvre plusieurs surfaces d'attaque : vulnérabilités dans les images, misconfigurations IaC, secrets exposés dans le code.

Pour mon cas, deux scanners sont particulièrement pertinents et ne nécessitent **pas de téléchargement de base de vulnérabilités** (~300 MB — trop lourd pour mon runner Lightsail à 916 MB de RAM) :

- `trivy config` — misconfigurations dans les Dockerfiles et YAML
- `trivy fs --scanners secret` — secrets hardcodés dans le code

## L'Intégration Gitea Actions

Le workflow suit le même pattern que mon CI/CD Hugo existant : image de container + `git clone` manuel vers l'URL interne Gitea.

```yaml
name: Trivy Security Scan

on:
  push:
    branches: [main]
  pull_request:

jobs:
  trivy:
    runs-on: ubuntu-latest
    container:
      image: aquasec/trivy:latest

    steps:
      - name: Clone repo
        run: |
          git clone --depth 1 --branch "${GITHUB_REF_NAME:-main}" \
            "http://oauth2:${{ secrets.GITEA_TOKEN }}@gitea:3000/${GITHUB_REPOSITORY}.git" /repo

      - name: Scan — misconfigurations
        run: |
          trivy config \
            --severity HIGH,CRITICAL \
            --exit-code 0 \
            /repo
        continue-on-error: true

      - name: Scan — secrets exposés
        run: |
          trivy fs \
            --scanners secret \
            --exit-code 0 \
            /repo
        continue-on-error: true
```

`--exit-code 0` = mode advisory, aucun blocage de pipeline. On inventorie d'abord avant de durcir.

## Deux Bugs Corrigés en Route

**Bug 1** : Le runner Gitea Act monte automatiquement un volume sur `/workspace/owner/repo`. Clone vers `/workspace` → "not an empty directory". Fix : cloner vers `/repo`.

**Bug 2** : Le repo est privé. `git clone` sans credentials → "could not read Username". Fix : `oauth2:${{ secrets.GITEA_TOKEN }}` dans l'URL — le token est injecté automatiquement par Gitea Actions.

## Ce que le Premier Scan a Trouvé

### Misconfigurations (trivy config)

**USER root dans les Dockerfiles (DS-0002 — HIGH)**

Plusieurs images tournent en root sans déclaration explicite d'un utilisateur non-privilégié : `berezina`, `borodino`, `narva`, `karacho`... C'est une surface d'attaque classique — si le container est compromis, l'attaquant a directement les droits root.

**Secrets dans les build-args / ENV (CRITICAL)**

Les Dockerfiles `karacho`, `oblast` et `oblast-1` passent des secrets via des variables d'environnement ou des build-args. Ces secrets se retrouvent dans les layers de l'image et dans l'historique Docker.

**`apt-get` sans `--no-install-recommends` (DS-0029 — HIGH)**

Les Dockerfiles ZAP (`oblast/Dockerfile.zaproxy`) installent des paquets sans `--no-install-recommends`, ce qui gonfle inutilement la taille des images et augmente la surface d'attaque.

### Secrets exposés (trivy fs)

Aucun secret hardcodé détecté. Bonne nouvelle.

## La Suite

Le workflow est en place. Prochaines étapes :

1. Corriger les Dockerfiles critiques (secrets dans ENV en priorité)
2. Ajouter des `USER` non-root là où c'est possible sans casser le fonctionnement
3. Passer `--exit-code 1` sur le scanner de secrets une fois les faux positifs triés
4. Étendre à `trivy image` pour scanner les images buildées (nécessite plus de RAM)

L'infrastructure de sécurité commence par sa propre hygiène.
