---
title: "thearm_logpull : Centraliser les logs nginx de redirecteurs hétérogènes dans un lab red-team"
date: 2026-07-16
draft: false
tags: ["homelab", "docker", "cybersecurity", "build-in-public", "french-tech", "infosec"]
summary: "Analyse technique de thearm_logpull, le collecteur de logs nginx qui agrège les accès de redirecteurs Fly.io et Lightsail dans la base PostgreSQL du lab Bojemoi pour une visibilité opérationnelle en temps quasi-réel."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

## Contexte : pourquoi un collecteur de logs dédié ?

Dans une infrastructure red-team un peu sérieuse, les redirecteurs sont en première ligne. Ils reçoivent les callbacks des implants, absorbent le bruit des scanners et des bots, et constituent souvent la seule trace de ce qui se passe réellement sur le réseau. Le problème : quand ces redirecteurs sont déployés sur des clouds hétérogènes — ici Fly.io d'un côté, AWS Lightsail de l'autre — les logs restent éparpillés sur des interfaces complètement différentes.

`thearm_logpull` est la réponse pragmatique à ce problème. C'est un daemon Python qui tourne dans le Swarm, qui va chercher les logs là où ils sont, et qui les normalise dans une table PostgreSQL centrale (`redirector_hits`) partagée avec le reste du lab, notamment Metasploit Framework.

## Ce que fait le composant, concrètement

Le script s'organise autour d'une boucle principale très simple : toutes les `LOOP_INTERVAL` secondes (3600 par défaut), il déclenche `run_once()` qui :

1. **Tire les logs Fly.io** via le CLI `fly logs`, en passant le token d'API comme variable d'environnement
2. **Tire les logs Lightsail** via SSH avec une clé PEM et un `sudo tail`
3. **Parse les deux sources** avec une regex nginx combined log unique
4. **Upserte les résultats** dans `redirector_hits` avec une logique de déduplication par `(source_ip, server)`

Le tout en moins de 300 lignes. C'est volontairement minimal.

## Les choix techniques qui méritent attention

### La gestion des secrets en couches

La fonction `_read_secret()` implémente un ordre de priorité explicite : variable d'environnement legacy → variable d'environnement standard → fichier Docker secret dans `/run/secrets/`. C'est un pattern qu'on voit peu souvent écrit aussi clairement, et qui évite l'effet tunnel où le secret n'est lisible que d'une seule façon. En pratique, ça permet de faire tourner le script en local avec un simple `export`, et en production avec les secrets Docker Swarm sans changer une ligne de code.

### La regex nginx : un choix assumé

```python
NGINX_RE = re.compile(
    r'^(\d{1,3}(?:\.\d{1,3}){3})'
    r'[^"]*"(?:\w+) '
    r'(\S+) HTTP/[^"]*"'
    r' (\d{3})'
    r'[^"]*"[^"]*"'
    r' "([^"]*)"'
)
```

On extrait IP, path, status code et user-agent depuis le format Combined Log de nginx. Le choix de la regex plutôt qu'un parser dédié (comme `nginx-log-parser`) est honnêtement un compromis : ça marche à 95% des cas, ça n'a aucune dépendance supplémentaire, et le format Combined Log est suffisamment stable pour qu'on puisse vivre avec. Le `search()` plutôt que `match()` est une bonne idée ici : les logs Fly.io arrivent préfixés par des métadonnées de runtime, donc on ne peut pas supposer que la ligne commence par l'IP.

### Le nettoyage des codes ANSI pour Fly.io

Fly.io est une joie à intégrer en CLI : le binaire `fly logs` envoie des codes d'échappement ANSI dans stdout même quand on est dans un subprocess Python. Le code gère ça proprement avec une regex dédiée et extrait ensuite le contenu nginx via le marker de niveau de log `[info]`. C'est le genre de détail qui prend 45 minutes à déboguer la première fois.

### L'upsert PostgreSQL avec `ON CONFLICT`

```sql
INSERT INTO redirector_hits (source_ip, server, ...)
VALUES (...)
ON CONFLICT (source_ip, server) DO UPDATE SET
    last_seen  = now(),
    hit_count  = redirector_hits.hit_count + 1,
    sample_path = EXCLUDED.sample_path,
    sample_ua   = EXCLUDED.sample_ua
```

La table joue un double rôle : compteur de hits et snapshot de la dernière activité. Le `hit_count` incrémental permet de repérer rapidement les IPs qui reviennent souvent — potentiellement des scanners persistants ou, plus intéressant, des blue teamers qui traquent l'infrastructure. Le cast `%s::inet` pour l'IP est une bonne pratique PostgreSQL qui offre des possibilités de requêtes CIDR plus tard.

### Le filtre des IPs privées

```python
PRIVATE_RE = re.compile(
    r'^(10\.|172\.(1[6-9]|2\d|3[01])\.|192\.168\.|127\.|::1|fd)'
)
```

Simple et efficace. On élimine le bruit interne avant l'insertion. Ça couvre RFC1918 + loopback + ULA IPv6. Ce qu'il manque : les IPs `169.254.x.x` (link-local) et `100.64.x.x` (Carrier-Grade NAT), qui peuvent apparaître dans certaines infrastructures cloud.

## Les limitations honnêtes

**Le `tail` ne gère pas la rotation des logs.** Si nginx fait un logrotate entre deux pulls, les nouvelles lignes du fichier `access.log` seront récupérées correctement, mais on peut avoir un gap ou un doublon sur la transition. En production réelle, il faudrait soit `tail -F` en continu (et changer d'architecture), soit tracker la position avec un fichier d'état.

**Les doublons entre cycles.** Chaque pull récupère les N dernières lignes sans mémoriser jusqu'où on était arrivé. L'upsert `ON CONFLICT` absorbe les doublons proprement, mais ça signifie que `hit_count` peut être légèrement surestimé si la même IP apparaît dans la fenêtre chevauchante de deux pulls consécutifs.

**SSH avec `StrictHostKeyChecking=no`.** C'est pratique pour un lab, mais c'est une ouverture à une attaque MITM si le segment réseau n'est pas de confiance. À noter clairement dans la doc.

**Le `fly logs` récupère les N dernières lignes en snapshot.** Ce n'est pas du streaming, donc sur un redirecteur sous forte charge, on peut rater des événements entre deux pulls. L'alternative propre serait un vrai pipeline Loki/Vector, mais c'est beaucoup plus de complexité pour un lab.

**Pas de retry sur la connexion PostgreSQL.** Si le conteneur postgres redémarre pendant un pull, on perd le cycle sans mécanisme de backoff.

## Pistes d'amélioration

- **Ajouter un timestamp de référence** en DB pour ne puller que les lignes nouvelles depuis le dernier run, éliminant les doublons structurellement
- **Intégrer un lookup GeoIP** (MaxMind mmdb) pour enrichir les hits avec pays et ASN — utile pour la threat intel
- **Exposer des métriques Prometheus** (hits par serveur, latence des pulls, erreurs
