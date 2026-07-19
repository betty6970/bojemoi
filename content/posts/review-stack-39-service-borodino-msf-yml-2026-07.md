---
title: "Metasploit en Docker Swarm : anatomie du stack borodino-msf"
date: 2026-07-19
draft: false
tags: ["homelab", "docker", "cybersecurity", "build-in-public", "french-tech", "infosec"]
summary: "Décortiquons le stack Docker Swarm qui orchestre msfrpcd comme teamserver Metasploit dans le lab red-team Bojemoi, avec ses choix techniques, ses compromis et ses limites honnêtes."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

## Le contexte : pourquoi un teamserver Metasploit dans Docker Swarm ?

Dans l'architecture Bojemoi Lab, le stack `borodino-msf` répond à un besoin simple mais structurant : avoir un daemon Metasploit (`msfrpcd`) toujours disponible, joignable via RPC depuis d'autres services, et intégré proprement dans l'écosystème Docker Swarm. C'est la colonne vertébrale offensive du lab — le composant qui reçoit les shells, pilote les sessions, et expose une API RPC que d'autres outils peuvent consommer.

Ce n'est pas révolutionnaire sur le papier. Mais le diable est dans les détails d'intégration, et c'est exactement ce qu'on va décortiquer.

---

## Architecture et dépendances : le problème de l'ordre de déploiement

Premier point notable, et franchement pas trivial à gérer proprement avec Docker Swarm : ce stack **doit être déployé avant** le stack `borodino` (le stack principal). Pourquoi ? Parce que c'est lui qui crée les réseaux overlay `pentest` et `borodino_scan_net`, que le stack suivant consomme comme réseaux externes.

Docker Swarm ne gère pas nativement les dépendances inter-stacks. Pas de `depends_on` à ce niveau d'abstraction. La solution adoptée ici est pragmatique : documenter la procédure dans le fichier YAML lui-même, en commentaire, avec les commandes exactes à exécuter dans l'ordre. C'est low-tech, c'est un peu artisanal, mais ça marche et ça ne nécessite pas d'introduire un orchestrateur supplémentaire (Ansible, Helm-like) juste pour gérer cet ordre.

Le réseau `pentest` est le bus de communication entre les services offensifs. Les autres services qui veulent parler à msfrpcd ou être dans la même plage réseau pour du mouvement latéral simulé s'y connectent. C'est une séparation réseau volontaire : le trafic offensif ne transite pas par le réseau `backend` généraliste.

---

## Ruby GC tuning : un détail qui change tout en production

Un des choix techniques les plus intéressants — et les moins documentés sur Internet — concerne le tuning du garbage collector Ruby directement via des variables d'environnement :

```yaml
- RUBY_GC_HEAP_GROWTH_FACTOR=1.1
- RUBY_GC_HEAP_FREE_SLOTS_MIN_RATIO=0.20
- RUBY_GC_MALLOC_LIMIT=16777216
- RUBY_GC_MALLOC_LIMIT_MAX=67108864
```

Metasploit Framework est écrit en Ruby. `msfrpcd` en production longue durée (et dans un lab qui tourne 24/7, c'est exactement ce scénario) peut développer une pression mémoire importante à cause du comportement par défaut du GC Ruby, trop agressif dans certains cas, pas assez dans d'autres.

Ce qu'on fait ici :
- **`HEAP_GROWTH_FACTOR=1.1`** : le heap Ruby ne grossit que de 10% à chaque expansion. Comportement conservateur qui évite des allocations massives soudaines.
- **`HEAP_FREE_SLOTS_MIN_RATIO=0.20`** : on maintient au minimum 20% de slots libres dans le heap. Le GC se déclenche moins souvent, mais de façon plus prévisible.
- **`MALLOC_LIMIT` et `MALLOC_LIMIT_MAX`** : on plafonne respectivement à 16 Mo et 64 Mo les seuils avant déclenchement du GC sur les allocations C-level. Crucial pour éviter les pics mémoire sur les gros modules MSF.

Résultat observé : une consommation mémoire plus stable, moins de spikes à 5-6 Go suivis de GC full bloquants. Le service reste réactif même après des heures de session active.

---

## Healthcheck et start_period : patience avec msfrpcd

```yaml
healthcheck:
  test: ["CMD", "nc", "-z", "127.0.0.1", "55553"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 600s
```

Le `start_period` à **600 secondes** (10 minutes) peut surprendre. C'est volontaire. `msfrpcd` avec la connexion à PostgreSQL, l'initialisation de la base `msf`, et le chargement des modules prend facilement 3 à 5 minutes sur un nœud worker chargé. Sans ce `start_period` généreux, Docker Swarm redémarrerait le container en boucle avant même qu'il ait fini de démarrer.

Le check lui-même est minimaliste : un `nc -z` sur le port 55553 (port MSFRPC par défaut). Il vérifie que le daemon écoute, pas qu'il est fonctionnel à 100%. C'est une limitation connue.

---

## Exposition réseau : Traefik comme proxy TCP pour Meterpreter

Le label Traefik le plus intéressant :

```yaml
- traefik.tcp.routers.meterpreter.rule=HostSNI(`*`)
- traefik.tcp.routers.meterpreter.entrypoints=meterpreter
- traefik.tcp.services.meterpreter.loadbalancer.server.port=4444
```

Le port 4444 (listener Meterpreter classique) est exposé via Traefik en mode TCP avec `HostSNI(*)`. Cela signifie que tout le trafic TCP entrant sur l'entrypoint `meterpreter` est forwardé vers le container msf, sans inspection TLS. C'est un choix délibéré : Meterpreter gère son propre chiffrement, on ne veut pas que Traefik tente de terminer le TLS.

---

## Points d'amélioration honnêtes

Voilà ce qui mériterait du travail :

**1. Le healthcheck est trop superficiel.** Un vrai check ferait un appel RPC minimal via `msfrpc` pour valider que l'API répond, pas juste que le port est ouvert.

**2. L'ordre de déploiement est manuel.** Un wrapper shell ou un Makefile avec des checks intermédiaires (`docker service ls --filter name=borodino-msf_msf-teamserver`) serait plus robuste que de la documentation commentée.

**3. Les ressources sont généreuses.** 6 Go de RAM en limite, c'est beaucoup pour un homelab. C'est le reflet d'une réalité MSF en production longue durée, mais ça mériterait un profiling plus fin selon les modules réellement utilisés.

**4. Pas de rotation de secret msf_rpc_password.** Le secret Docker est statique. Un mécanisme de rotation (même manuel avec une procédure documentée) devrait exister.

---

## Conclusion

Ce stack `borodino-msf` illustre bien le style du projet : pragmatique, fonctionnel, avec quelques optimisations non-évidentes (le GC Ruby, le start_period) qui font la différence en condition réelle. Ce n'est pas parfait — la gestion des d
