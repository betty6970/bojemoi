---
title: "Enrichissement OSINT d'adresses IP dans un homelab red-team : anatomie de osint_lookup.py"
date: 2026-07-18
draft: false
tags: ["homelab", "docker", "cybersecurity", "build-in-public", "french-tech", "infosec"]
summary: "Plongée dans le composant d'enrichissement OSINT du projet Bojemoi Lab : comment transformer une IP brute en verdict de menace en agrégeant six sources de threat intelligence, sans dépendances externes lourdes."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

## Ce fichier, à quoi il sert vraiment ?

Dans l'architecture de Bojemoi Lab, le composant `thearm_bm12` est chargé de tenir un registre des hôtes observés sur le réseau — paquets capturés, connexions détectées, assets découverts. Mais une IP brute, c'est peu d'information. Est-ce un hébergeur connu ? Un nœud Tor ? Un serveur déjà vu dans des rapports de malware ?

C'est là qu'intervient `osint_lookup.py`. Ce module Python synchrone se charge d'enrichir chaque enregistrement d'hôte avec des données de threat intelligence issues de **six sources externes**. Le résultat : un `threat_score` entre 0 et 100, un `threat_level` en cinq paliers (`clean` → `critical`), et un flag booléen `is_malicious`. Simple, lisible, exploitable directement dans un dashboard ou une règle d'alerte.

---

## Architecture du module : les choix techniques

### Zéro dépendance tierce

Premier choix assumé et honnête : le module n'utilise **aucune bibliothèque externe**. Pas de `requests`, pas de `httpx`, pas de SDK Shodan ou OTX. Tout passe par `urllib.request` de la stdlib Python.

C'est un choix de robustesse pour un homelab : moins de dépendances dans le `requirements.txt`, moins de surface d'attaque dans l'image Docker, et une image plus légère. En contrepartie, on perd la gestion fine des sessions HTTP, le retry automatique, et les connexions persistantes. Pour un usage en lab où les lookups ne sont pas à haute fréquence, c'est un compromis raisonnable.

### Gestion des secrets : la cascade en trois niveaux

La fonction `_read_secret()` illustre un pattern propre pour les environnements Docker Swarm :

```
legacy env var → env var standard → /run/secrets/<name>
```

La priorité donnée aux **Docker Secrets** (`/run/secrets/`) est la bonne approche en production Swarm : les secrets ne transitent pas dans les variables d'environnement du processus, ils sont montés en mémoire tmpfs. Le support des env vars reste là pour la compatibilité locale (docker-compose en mode dev). C'est du build-in-public honnête : on documente qu'on supporte les deux, on préférera les secrets en prod.

### Six sources, deux catégories

Le module sépare clairement deux familles de sources :

**Gratuites, sans clé :**
- **ip-api.com** — géolocalisation + détection proxy/VPN/hosting. Limite de 45 req/min en HTTP, ce qui peut devenir un goulot d'étranglement.
- **AlienVault OTX** — pulses de menaces et échantillons malware. L'API publique est généreuse mais non garantie.
- **ThreatCrowd** — votes communautaires et hashes associés. Le service a des disponibilités variables, la gestion silencieuse des erreurs (`return {}`) est donc essentielle ici.

**Optionnelles, avec clé :**
- **AbuseIPDB** — rapports d'abus avec score de confiance et flag Tor.
- **VirusTotal** — agrégation de 70+ moteurs antimalware.
- **Shodan** — ports ouverts et CVEs associés à l'hôte.

La fonction `_get()` absorbe silencieusement toutes les exceptions réseau. C'est pragmatique pour un lab : un timeout ou une API down ne doit pas bloquer le pipeline d'enrichissement. En production sérieuse, on voudrait distinguer les timeouts des erreurs 4xx/5xx, mais pour l'usage actuel c'est suffisant.

### Le scoring : une heuristique pondérée transparente

La fonction `_calculate_score()` est probablement la partie la plus intéressante intellectuellement. Elle implémente un **modèle de scoring additif avec plafonnement par catégorie** :

| Signal | Contribution max |
|--------|-----------------|
| Tor | +30 pts |
| Abuse reports | +30 pts |
| Malware samples + VT | +25 pts |
| OTX pulses | +15 pts |
| ThreatCrowd votes négatifs | +20 pts |
| CVEs Shodan | +20 pts |
| Proxy / Hosting | +10 / +5 pts |

Le score global est plafonné à 100. Les seuils de niveau (`25 / 50 / 70`) sont codés en dur — c'est une limitation connue, on y revient plus bas.

La logique des **votes ThreatCrowd négatifs** mérite d'être notée : dans ce système, un vote négatif signifie "malveillant". Le module le gère correctement avec `abs(votes)`, ce qui est un piège classique à ne pas rater.

---

## Points d'amélioration potentiels

Soyons honnêtes sur les limitations, c'est l'esprit du projet.

**1. Le mode synchrone va devenir douloureux.** Six appels HTTP séquentiels avec un timeout de 10 secondes chacun donnent jusqu'à **60 secondes de latence dans le pire cas**. Passer à `asyncio` + `aiohttp` (ou même `concurrent.futures.ThreadPoolExecutor`) réduirait ça à ~10-15 secondes (le plus lent des appels parallèles). C'est le chantier prioritaire si le volume d'IPs à enrichir augmente.

**2. Pas de cache.** Si la même IP externe est vue dix fois en une heure, on interroge dix fois les mêmes APIs. Un cache Redis avec TTL de quelques heures s'intègrerait naturellement dans l'architecture Swarm existante.

**3. Les seuils de scoring sont magic numbers.** Les valeurs `25 / 50 / 70` et les coefficients multiplicateurs mériteraient d'être externalisés dans un fichier de configuration YAML ou des variables d'environnement. Cela permettrait de calibrer le scoring par type d'environnement (plus agressif pour un honeypot, plus conservateur pour un réseau de prod).

**4. ThreatCrowd.** Le service est connu pour être instable et parfois abandonné. Il faudrait soit le monitorer activement, soit le remplacer par une source plus fiable (GreyNoise public API, par exemple, qui offre aussi un tier gratuit).

**5. Pas de gestion du rate limiting.** ip-api.com limite à 45 requêtes par minute sur l'endpoint HTTP non authentifié. Sans backoff exponentiel, on va silencieusement recevoir des réponses vides sous charge.

---

## Ce qu'on garde, ce qu'on améliore

Ce module fait exactement ce qu'il doit faire pour un lab red-team en phase de bootstrapping : il fonctionne, il est lisible, il est extensible, et il n'impose aucune dépendance lourde. La gestion des secrets est correcte pour Docker Swarm, la séparation des sources gratuites/payantes est bien pensée.

Le prochain jalon réaliste : **ajouter un pool de threads pour paralléliser les appels**, puis **brancher Redis pour le cache**. Deux PRs, pas une r
