---
title: "thearm_nuclei : orchestrer des scans Nuclei intelligents depuis une base MSF dans un lab red-team"
date: 2026-07-14
draft: false
tags: ["homelab", "docker", "cybersecurity", "build-in-public", "french-tech", "infosec"]
summary: "Plongée dans thearm_nuclei, le worker Python qui sélectionne des cibles depuis une base Metasploit, orchestre des scans Nuclei via une API dédiée, et enrichit dynamiquement les tags grâce à Ollama — le tout piloté par une queue Valkey."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

## Contexte : un worker au cœur du pipeline de reconnaissance

Dans l'architecture de Bojemoi Lab, chaque composant a une responsabilité claire. `thearm_nuclei` est le **worker de scan de vulnérabilités**. Son rôle : piocher des cibles qualifiées dans une base PostgreSQL (celle de Metasploit Framework), les soumettre à une instance `nuclei-api`, et tracer les résultats. Il se positionne en aval des phases de découverte et d'OSINT (`bm12_v3`), et en amont du reporting vers DefectDojo.

Ce n'est pas un wrapper trivial autour de nuclei. Il y a plusieurs couches de logique qui méritent qu'on s'y attarde.

---

## Architecture : queue-first avec fallback DB

Le pattern central est un **BRPOP bloquant sur Valkey** (le fork Redis open source). Le worker dort proprement tant que la queue `pentest:nuclei_queue` est vide — zéro CPU gaspillé en busy-loop. C'est la bonne façon de faire dans un environnement containerisé où on a d'autres workloads qui tournent.

Ce qui est honnêtement bien pensé : le **fallback DB**. Si la queue est vide au bout de 30 secondes, le worker ne reste pas les bras croisés. Il appelle `pick_target()` et sélectionne lui-même un hôte depuis la base. Cela garantit une utilisation continue du lab sans qu'un composant amont soit obligé de pousser en queue.

```
item = r.brpop(QUEUE_KEY, timeout=BRPOP_TIMEOUT)
if item is None:
    row = pick_target(conn)  # fallback autonome
```

C'est un pattern **pull/push hybride** qu'on voit rarement documenté clairement — et qui fonctionne bien en pratique.

---

## Sélection des cibles : trois niveaux de priorité

`pick_target()` implémente une stratégie de priorisation en cascade avec trois requêtes SQL :

1. **Priorité 1** : hôtes avec ports web ouverts (80, 443, 8080, 8443, 8000, 8888, 3000, 9090) **ET** produits reconnus dans `PRODUCT_TAG_MAP`
2. **Priorité 2** : hôtes avec ports web seulement
3. **Fallback** : `TABLESAMPLE SYSTEM(1)` — un échantillon aléatoire de 1% de la table hosts, sans contrainte de port

Le filtre `is_hosting` exclut les IPs résidentielles (plages FAI grand public), ce qui réduit le bruit et — plus important en red team — limite l'exposition légale du lab. Le filtre IPv6 link-local (`fe80::`), lui, évite des tentatives de scan inutiles sur des adresses non routables.

Un point intéressant : l'exclusion des hôtes déjà dans `nuclei_scan_log` avec les statuts `completed`, `running` ou `no_findings` se fait via un sous-SELECT. C'est fonctionnel mais potentiellement lent à grande échelle — on y revient plus bas.

---

## Extraction et enrichissement des tags

C'est ici que le worker sort du lot. Plutôt que de lancer nuclei à l'aveugle, `extract_tags()` analyse le champ `scan_details` (JSON bm12_v3) pour construire un ensemble de tags Nuclei pertinents.

Le mapping `PRODUCT_TAG_MAP` couvre une quarantaine de produits : des CMS (WordPress, Drupal), des serveurs web (Apache, Nginx, IIS), des bases de données, des équipements réseau (Cisco, Fortinet, Palo Alto), des panels d'admin... Trois sources sont croisées :

- **`evidence`** : format bm12_v3 structuré (`{"web": ["http:80", "ssh:22"]}`)
- **`primary_role`** : rôle global de l'hôte détecté lors du scan précédent
- **`products`** : format legacy liste de chaînes ou de dicts

Tous les scans reçoivent par défaut les tags `cve,exposure,misconfiguration,panel,default-login` — un filet de sécurité raisonnable pour ne rien rater d'évident.

### Enrichissement via Ollama (optionnel)

`enrich_tags()` pousse le contexte du scan vers un modèle local (Mistral 7B par défaut) pour suggérer des tags supplémentaires. C'est désactivé par défaut (`OLLAMA_ENABLED=false`), ce qui est sage : ajouter de la latence LLM dans un pipeline de scan, ça se réfléchit.

Le prompt est minimaliste et contraint : retourner **uniquement** un JSON array de tags. La gestion du markdown dans la réponse (blocs ```json) est présente, ce qui montre que les LLMs locaux ne respectent pas toujours les consignes de format — vécu.

---

## Protection honeypot : ne pas scanner ses propres pièges

Avant chaque scan, `is_honeypot_suspect()` vérifie si l'IP cible a interagi avec les honeypots du lab ou ses redirecteurs. C'est un détail qu'on oublie souvent dans les labs : **scanner un honeypot bien configuré déclenche des alertes chez son opérateur**, et peut exposer votre infrastructure.

Ces IPs sont marquées `honeypot_suspect` dans `nuclei_scan_log` plutôt que `failed` — distinction utile pour l'analyse post-mortem.

---

## Gestion de la connexion DB pendant les scans longs

Un scan Nuclei peut durer jusqu'à 20 minutes (`SCAN_TIMEOUT=1200`). Garder une connexion PostgreSQL ouverte pendant tout ce temps serait une mauvaise idée dans un pool limité. Le code libère explicitement la connexion avant d'appeler `wait_for_scan()` et en ouvre une nouvelle pour écrire le résultat. Simple, efficace.

---

## Ce qui pourrait être amélioré

Soyons honnêtes sur les limitations actuelles :

**Performance SQL** : le `NOT IN (SELECT host_id FROM nuclei_scan_log WHERE status IN (...))` dans `pick_target()` sera douloureux si `nuclei_scan_log` grossit. Un index partiel sur `(host_id, status)` ou une réécriture en `NOT EXISTS` serait plus robuste.

**Pas de dead letter queue** : si un item Valkey est consommé mais que le scan échoue avant l'écriture en DB, il disparaît silencieusement. Un pattern avec `RPOPLPUSH` vers une queue "en cours" permettrait de récupérer les items crashés.

**Pas de rate limiting** : le worker consomme la queue aussi vite qu'il peut. Si nuclei-api est limité en workers, les soumissions peuvent s'empiler. Un sémaphore ou une vérification de la charge API avant soumission serait utile.

**L'enrichissement Ollama est synchrone** : si Ollama est lent (ce qui arrive avec un 7B sur CPU), ça bloque le pipeline. Une mise en cache des tags par
