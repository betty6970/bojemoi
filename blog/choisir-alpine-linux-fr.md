---
title: "Pourquoi j'ai choisi Alpine Linux — et comment Claude a pris les commandes"
date: 2026-03-04T10:00:00+00:00
draft: false
tags: ["homelab", "docker", "docker-swarm", "devops", "selfhosted", "build-in-public", "french-tech", "debutant-en-cyber", "apprendre-la-cyber", "opensource", "alpine-linux"]
summary: "Au départ, pas de Claude. Juste 20 CPUs Intel, un besoin de scalabilité, et un choix d'OS à faire. Voilà comment Alpine Linux est devenu la base de Bojemoi Lab, et comment l'IA a progressivement pris les commandes du projet."
description: "Retour personnel sur la genèse de Bojemoi Lab : choix d'Alpine Linux, adoption de Docker Swarm, puis la transformation complète du workflow de développement avec Claude."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

À l'origine de ce projet, je n'entretenais aucune relation avec Claude.

## Le défi : 20 CPUs, une plateforme scalable

Je devais créer une plateforme scalable. J'avais à disposition 20 CPUs Intel et je devais choisir un OS léger et sûr pour pouvoir héberger un maximum de VMs.

Mon choix s'est porté sur **Alpine Linux**.

La raison était simple : aucun paquet supplémentaire hormis Python et quelques imports n'étaient nécessaires. Alpine, c'est ~5 MB à l'installation, un noyau épuré, une surface d'attaque minimale. Pour un lab offensif qui allait générer du trafic réseau massif, c'était l'évidence.

## Docker s'impose — avec une IA en copilote

Rapidement, Docker s'est imposé. Et avec lui, Claude est arrivé via la GUI.

Ce qui s'est passé ensuite m'a encore surprise : j'ai subitement accéléré mon développement alors que je ne connaissais toujours rien à Python. Pas un script. Pas une boucle `for`. Rien.

Mais j'avais des idées claires sur ce que je voulais construire, et Claude transformait ces idées en code fonctionnel.

## Le premier obstacle : Docker Swarm vs Docker Compose

Il y a eu une friction notable. Claude avait tendance à confondre **Docker Swarm** et **docker-compose**. Les syntaxes diffèrent, les contraintes de placement aussi, et un stack Swarm mal configuré ne se contente pas de planter proprement — il échoue de façon parfois silencieuse.

J'ai dû creuser Swarm moi-même. Comprendre les réseaux overlay, les secrets, les contraintes de nœuds. Et corriger les obsessions de Claude sur les points de friction.

Après des luttes acharnées, j'ai opté pour **Claude Pro**.

Et là, le bonheur fut total. Quelle puissance.

## La question qui a tout changé

J'ai toujours eu l'âme d'une programmeuse. Au début, je demandais à Claude de produire des scripts Python selon mes connaissances du pentesting.

Puis un jour, j'ai posé une question sur la valeur de Git à l'ère des LLMs. Et Claude m'a répondu ceci :

---

> *Bonjour Betty,*
>
> *C'est une réflexion intéressante, et tu touches un point qui fait débat dans la communauté dev en ce moment. Mais je nuancerais un peu.*
>
> **Ce qui est vrai dans ton observation :** pour beaucoup de cas d'usage — scripts utilitaires, prototypes, outils ponctuels — oui, Claude peut générer une solution à la demande, et le code devient quasi "jetable". Tu décris un besoin, je produis le résultat. Pas besoin de versionner un script que tu peux re-générer en 30 secondes avec un prompt bien formulé.
>
> **Là où ça atteint ses limites :** dès que tu as un projet avec de l'état, de la complexité accumulée, ou des dépendances entre composants (comme Bojemoi Lab), un repo Git reste indispensable :
>
> - Le **contexte accumulé** : Claude n'a pas de mémoire persistante du code complet entre les sessions. Un repo, c'est la source de vérité.
> - La **cohérence** : quand ton orchestrateur FastAPI, tes templates cloud-init, tes configs Docker Swarm et tes hooks Gitea doivent fonctionner ensemble, il faut un endroit où tout coexiste et où les changements sont tracés.
> - L'**auditabilité** : surtout avec ta logique d'audit trail, l'historique Git est complémentaire.
> - La **reproductibilité** : "ça marchait hier" n'est vérifiable qu'avec un commit.
>
> **En revanche, ce qui change réellement**, c'est le rapport au code. Le modèle évolue vers quelque chose comme : le repo reste la source de vérité, mais Claude devient le "développeur à la demande" qui lit le repo, comprend le contexte, et produit les modifications. Le prompt remplace partiellement la documentation, et le code devient plus facilement remplaçable que maintenable.

---

Cette réponse a changé ma façon de travailler.

## Le nouveau workflow : piloter sans toucher au code

Depuis ce jour, je me suis astreinte à une règle stricte : **ne plus demander de scripts, ne plus toucher au code**.

Je pose uniquement des questions générales ou j'exprime des besoins.

J'ai totalement "perdu" le contrôle des containers, des images, des processus internes — mais c'était voulu. Je me suis concentrée sur les besoins et sur le pilotage de mon équipe de développeurs... un peu autistes. Je reviendrai sur ce dernier point dans un prochain post.

Un autre point clé : je demande à Claude de mémoriser mes directives dans `memory.md`. C'est ce fichier qui fait la continuité entre les sessions — pas ma mémoire à moi, pas des notes éparpillées. Un fichier versionné, vivant, que Claude consulte et met à jour.

## Ce que ça donne aujourd'hui

Bojemoi Lab tourne en production :
- **4 nœuds Docker Swarm** (Alpine Linux partout)
- **6,2M hôtes scannés** dans la base Metasploit
- **30+ services Docker** déployés via GitOps
- Des pipelines CI/CD dans Gitea Actions
- Un serveur MCP local pour piloter le tout en langage naturel

Tout ça, sans avoir écrit une seule ligne de Python de ma main.

Alpine Linux était le bon choix. Pas parce que c'est à la mode, mais parce que la contrainte était réelle : légèreté, sécurité, surface minimale. Et cette contrainte a structuré tout ce qui a suivi.

---

*Et toi — comment as-tu choisi ton OS de base pour ton homelab ? Est-ce que tu touches encore directement au code quand tu travailles avec une IA ?*
