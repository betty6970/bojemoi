---
title: "CI/CD Hugo avec Gitea Actions et Alpine"
date: 2026-02-06T19:00:00+00:00
draft: false
---

Comment ce blog se déploie tout seul en moins de 15 secondes, avec un pipeline minimaliste.

## L'architecture

Le pipeline repose sur trois briques :

- **Gitea Actions** avec `act_runner` pour l'orchestration CI/CD
- **Alpine Linux 3.19** comme image de build (~8 MB)
- **Hugo** installé via `apk` pour la génération du site statique

Le runner tourne sur le même serveur que Gitea et Nginx. Il monte directement le répertoire web en volume Docker — pas de SSH, pas de rsync, pas d'artefact intermédiaire.

## Le workflow

```yaml
jobs:
  build-deploy:
    runs-on: ubuntu-latest
    container:
      image: alpine:3.19
      volumes:
        - /var/www/blog.bojemoi.me:/deploy
    steps:
      - name: Install dependencies
        run: apk add --no-cache hugo git

      - name: Checkout repo
        run: |
          git clone --depth 1 --branch "${GITHUB_REF_NAME}" \
            "http://gitea:3000/${GITHUB_REPOSITORY}.git" .

      - name: Build Hugo site
        run: hugo --minify

      - name: Deploy to web root
        run: |
          rm -rf /deploy/*
          cp -r public/* /deploy/
```

Quelques choix notables :

- **Pas de `actions/checkout`** — cette action nécessite Node.js, absent d'Alpine. Un simple `git clone --depth 1` fait le travail en une fraction de seconde.
- **Volume mount direct** — le runner est configuré avec `valid_volumes` dans son `config.yaml` pour autoriser le mount de `/var/www/blog.bojemoi.me`. Le déploiement se résume à un `cp`.
- **Pas de thème externe** — les layouts sont embarqués dans le repo pour éviter toute dépendance réseau au build.

## Configuration du runner

Le point clé est le `config.yaml` de `act_runner` :

```yaml
container:
  network: gitea_gitea-internal
  valid_volumes:
    - /var/www/blog.bojemoi.me
```

Le réseau `gitea_gitea-internal` permet au conteneur de build de résoudre `gitea:3000` pour le clone. Sans ça, le checkout échoue avec `Could not resolve host: gitea`.

## Résultat

Push sur `main` → build Hugo → fichiers copiés → site live. Le tout en ~15 secondes, avec une empreinte minimale.
