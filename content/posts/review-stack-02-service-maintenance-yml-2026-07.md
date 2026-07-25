---
title: "Maintenance nocturne dans un lab red-team : anatomie d'une stack Docker Swarm qui se nettoie elle-même"
date: 2026-07-25
draft: false
tags: ["homelab", "docker", "cybersecurity", "build-in-public", "french-tech", "infosec"]
summary: "Décryptage de la stack de maintenance automatisée du Bojemoi Lab : nettoyage Docker, garbage collection du registry, VACUUM Postgres et watchdog DefectDojo — le tout orchestré sous Docker Swarm avec des choix techniques assumés et quelques limitations honnêtes."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

## Le problème que cette stack résout

Un lab red-team tourne en continu. Les outils de scan (Nuclei, ZAP, Metasploit) génèrent des images Docker temporaires, des couches orphelines dans le registry interne, des entrées PostgreSQL en état `running` depuis 3 jours parce qu'un container s'est crashé sans prévenir. Sans hygiène automatisée, le disque sature en deux semaines et les dashboards Prometheus affichent des métriques corrompues par des artefacts de runs passés.

La stack `02-service-maintenance.yml` est la réponse à ça : cinq services qui tournent en arrière-plan, invisibles, et qui font le ménage pendant que le reste du lab scanne des cibles.

---

## Les cinq services en détail

### `docker-cleanup` — Le balayeur global

C'est le service le plus critique en termes de surface d'opération. Il tourne en **mode `global`**, ce qui signifie qu'une instance est déployée sur **chaque nœud** du swarm. C'est le bon pattern ici : le Docker socket est local à chaque nœud, impossible de nettoyer les ressources d'un nœud depuis un autre.

```yaml
command:
  - "0 */2 * * * docker container prune -f --filter until=2h"
  - "0 3   * * * docker system prune -af --filter until=24h"
```

Deux jobs cron :
- Toutes les 2 heures : purge des containers morts depuis plus de 2h (les runs de scan courts)
- À 3h du matin : `system prune` agressif — images, volumes anonymes, réseaux, build cache

Le `--filter until=24h` sur le prune nocturne est une protection importante : on ne supprime que ce qui a plus de 24h, évitant de tuer des images fraîchement buildées. C'est un détail qui compte quand on fait du CI/CD interne.

**Point de sécurité notable** : le container monte `/var/run/docker.sock`. C'est le compromis classique — socket Docker = root sur le nœud. Dans un lab isolé c'est acceptable, en production ça mérite une réflexion sur Rootless Docker ou un proxy de socket type `tecnativa/docker-socket-proxy`.

### `registry-gc` — Le ramasse-miettes du registry

Ce service a `replicas: 0` par défaut. Il ne tourne pas en permanence — il est déclenché **manuellement** après des séries de rebuilds :

```bash
docker service scale maintenance_registry-gc=1
```

Il exécute le garbage collector natif de la `registry:2` avec `--delete-untagged=true`. La subtilité : le GC du registry Docker nécessite que le registry soit **arrêté ou en lecture seule** pendant l'opération, sinon on risque une corruption. Ici c'est géré par la politique opérationnelle (pas de push pendant le GC), ce qui est une limitation réelle à documenter dans le runbook.

Le `restart_policy: condition: none` est cohérent : un job one-shot qui se relance indéfiniment c'est un anti-pattern.

### `swarm-exporter` — Les métriques Swarm pour Prometheus

Un script Python custom qui expose des métriques sur l'état du swarm (services, tâches, nœuds) au format Prometheus. Il tourne uniquement sur le manager car l'API Swarm n'est accessible que depuis le manager.

Les labels de service sont particulièrement propres :

```yaml
labels:
  - prometheus.enable=true
  - prometheus.port=9324
  - prometheus.path=/metrics
  - prometheus.label.team=infrastructure
  - prometheus.label.component=swarm-exporter
```

C'est du **label-based service discovery** — Prometheus scrape automatiquement tout service étiqueté `prometheus.enable=true`. Pas besoin de modifier la config Prometheus à chaque ajout de service. Pattern élégant pour un homelab en évolution rapide.

**Limitation honnête** : l'image `localhost:5000/python:latest` avec le tag `latest` c'est une bombe à retardement pour la reproductibilité. En prod on épinglerait un hash ou au minimum une version sémantique.

### `dojo-token-watchdog` — Le gardien du token DefectDojo

Ce service résout un problème concret : les tokens API de DefectDojo ont une durée de vie, et quand ils expirent, tous les outils qui poussent leurs findings vers DefectDojo commencent à échouer silencieusement.

Le watchdog vérifie toutes les 5 minutes (`CHECK_INTERVAL_SECONDS: 300`) que le token stocké en secret Docker est toujours valide, et le renouvelle si nécessaire via l'API DefectDojo.

```yaml
environment:
  STARTUP_DELAY: "60"
```

Le délai de démarrage de 60 secondes laisse le temps à DefectDojo de démarrer complètement avant la première tentative. C'est du polling avec backoff implicite — pas élégant, mais ça marche.

**Ce que j'aurais fait différemment** : `pip install` au démarrage du container c'est lent et ça casse si PyPI est inaccessible. Les dépendances devraient être dans l'image de base. C'est du dette technique assumée pour aller vite.

### `db-maintenance` — L'hygiène PostgreSQL

Deux scripts cron injectés dynamiquement dans le container Postgres :

- **Dimanche 4h** : `VACUUM ANALYZE` sur les quatre tables critiques (`hosts`, `services`, `nuclei_scan_log`, `zap_scan_log`)
- **Lundi 5h** : purge des entrées de scan en erreur/timeout vieilles de 7 jours, et des entrées en état `running` depuis plus d'un jour (orphelines de containers crashés)

```sql
DELETE FROM nuclei_scan_log 
WHERE status='running' AND scanned_at < now() - interval '1 day';
```

Cette dernière requête est particulièrement importante : sans elle, la table accumule des phantômes de scans qui n'ont jamais terminé, faussant les statistiques de couverture.

**Limitation** : le `VACUUM ANALYZE` cible des tables nommées en dur. Si on ajoute une nouvelle table de scan, il faut penser à mettre à jour ce fichier. Un `VACUUM ANALYZE` sans cible (toute la base) serait plus maintenable, au prix d'un run légèrement plus long.

---

## Patterns architecturaux remarquables

**Cron-in-container** : plutôt qu'un CronJob Kubernetes, tous les jobs périodiques utilisent `crond -f` lancé comme PID 1 (ou presque). Simple, pas de dépendance externe, les logs sortent vers stdout via `/proc/1/fd/1`. C'est le pattern "cron dans Docker" le plus propre que j'aie vu sans surcouche.

**Secrets Docker natifs** : les mots de passe ne transitent jamais en variable d'environnement. Ils sont lus depuis `/run/secrets/` au moment de l'exécution. C'est la bonne pratique Swarm.

**Contraintes manager** : tous les services qui touchent à l
