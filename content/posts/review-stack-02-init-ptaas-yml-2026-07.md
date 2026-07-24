---
title: "PTaaS Init : Comment on enregistre un nœud red-team en une seule passe avec HMAC et DefectDojo"
date: 2026-07-24
draft: false
tags: ["homelab", "docker", "cybersecurity", "build-in-public", "french-tech", "infosec"]
summary: "Décryptage du service d'initialisation PTaaS de Bojemoi Lab : un one-shot container qui génère une identité cryptographique par HMAC, provisionne DefectDojo et labellise le nœud Docker Swarm en moins de 30 secondes."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

## Le problème qu'on cherchait à résoudre

Quand on monte un lab red-team en mode *Penetration Testing as a Service* (PTaaS), la première question qui se pose est bête mais fondamentale : **comment identifier un nœud de manière unique sans gérer une PKI complète dès le départ ?**

On voulait quelque chose de simple, reproductible, et suffisamment robuste pour distinguer deux instances du lab déployées sur deux machines différentes. Le résultat, c'est `02-init-ptaas.yml` — un stack Docker Swarm one-shot qui tourne une seule fois, fait son travail, et disparaît (ou réessaie en cas d'échec).

---

## Ce que fait ce composant dans l'architecture globale

`02-init-ptaas.yml` est le **troisième acte** du bootstrap, après `01-boot` (infrastructure réseau, registry local) et `01-base` (PostgreSQL, DefectDojo, services core). Il suppose que PostgreSQL tourne déjà sur le réseau `backend` et que DefectDojo est joignable sur `http://defectdojo-nginx:8080`.

Son rôle est d'**enregistrer le nœud comme client PTaaS** en enchaînant quatre opérations :

1. **Calcul du serial** via `HMAC(telegram_key, local_key)`
2. **Création d'un produit DefectDojo** associé à ce serial
3. **Labellisation du nœud Docker** avec `ptaas.serial=<serial>`
4. **Persistance en base** dans la table `ptaas_identity`

Il y a aussi un cinquième point mentionné dans les commentaires — l'enregistrement blockchain — qui est honnêtement marqué `(stub)` pour l'instant. On y revient.

---

## Les choix techniques intéressants

### HMAC comme générateur de serial

Le choix de `HMAC(telegram_key, local_key)` pour dériver un identifiant est volontairement minimaliste. L'idée : deux clés séparées (`ptaas_telegram_key` pour l'identité réseau/bot, `ptaas_local_key` pour l'empreinte machine) combinées via HMAC donnent un serial déterministe mais non-réversible.

```
serial = HMAC-SHA256(telegram_key, local_key)
```

Avantage immédiat : **si on redeploie le lab sur la même machine avec les mêmes secrets, on retrouve exactement le même serial**. C'est important pour la cohérence des données dans DefectDojo — on ne crée pas un nouveau produit à chaque redémarrage.

C'est du crypto de bon sens, pas de la crypto de compétition. Pour un homelab red-team, c'est suffisant.

### Secrets Docker Swarm, pas de variables d'env

On aurait pu passer les clés en variables d'environnement. On ne l'a pas fait. Les quatre secrets sensibles (`postgres_password`, `ptaas_telegram_key`, `ptaas_local_key`, `dojo_api_token`) sont injectés via le mécanisme natif Docker Secrets, montés en `/run/secrets/` dans le container.

```yaml
secrets:
  - postgres_password
  - ptaas_telegram_key
  - ptaas_local_key
  - dojo_api_token
```

Ça évite qu'ils apparaissent dans `docker inspect`, dans les logs, ou dans un `ps aux` malencontreux. Bonne hygiène de base.

### Mount du socket Docker

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

C'est ce qui permet au container de labelliser le nœud lui-même via l'API Docker Engine. En pratique, le service appelle quelque chose comme `docker node update --label-add ptaas.serial=<serial> <node_id>`.

**C'est aussi le point le plus sensible de l'architecture.** Un container avec accès au socket Docker a, de facto, les droits root sur l'hôte. On l'accepte ici parce que c'est un service éphémère qui tourne uniquement sur le manager, avec des ressources limitées (`0.2 CPU`, `128M RAM`) et une politique de restart bornée (`max_attempts: 5`).

### Constraint `node.role == manager`

La labellisation des nœuds Swarm nécessite d'être exécutée depuis un manager. Le placement constraint l'impose explicitement, ce qui évite des erreurs d'API cryptiques si le scheduler décide de placer le service ailleurs.

### One-shot avec restart policy borné

```yaml
restart_policy:
  condition: on-failure
  delay: 10s
  max_attempts: 5
```

On ne veut pas que ce service tourne en boucle indéfiniment. Cinq tentatives avec 10 secondes d'intervalle, c'est assez pour absorber un démarrage lent de PostgreSQL ou de DefectDojo. Après ça, si ça échoue encore, il faut regarder les logs manuellement. C'est un choix délibéré : on préfère un échec visible à un retry infini silencieux.

---

## Points d'amélioration honnêtes

### Le stub blockchain

Le commentaire est transparent : `Registers on blockchain (stub)`. C'est une fonctionnalité voulue — l'idée à terme étant de tracer l'enregistrement des nœuds PTaaS sur une chaîne légère (probablement un simple contrat sur une testnet EVM) pour avoir une preuve d'existence immuable du serial. Pour l'instant, c'est un `pass` dans le code Python. On l'assume.

### Idempotence non garantie explicitement

Si le service est redéployé sur un nœud déjà initialisé, le comportement dépend entièrement de la logique applicative (`ptaas-init:latest`). Est-ce qu'on fait un `INSERT OR IGNORE` ou un `UPSERT` en PostgreSQL ? Est-ce que l'API DefectDojo tolère la création d'un produit au même nom ? Ces cas doivent être gérés dans le code, et ce n'est pas visible dans le YAML.

### Pas de healthcheck

Le service n'expose pas de healthcheck Docker. Pour un one-shot, c'est acceptable, mais ça compliquerait l'intégration dans un pipeline CI/CD qui attendrait une confirmation de succès propre.

### Image localhost:5000

On utilise le registry local du lab (`localhost:5000/ptaas-init:latest`). C'est pratique en développement, contraignant en production distribuée. Le flag `--resolve-image never` dans la commande de deploy est d'ailleurs là pour contourner la vérification de digest sur les images locales — un autre détail honnête à documenter.

---

## Ce qu'on a appris en le buildant

Le vrai apprentissage de ce composant, c'est que **l'initialisation d'infrastructure doit être pensée comme une transaction** : tout ou rien. Si la création du produit DefectDojo réussit mais que la persistance PostgreSQL échoue, on se retrouve dans un état incohérent. La version actuelle gère ça par retry global, pas par rollback partiel. C'est le prochain chantier.
