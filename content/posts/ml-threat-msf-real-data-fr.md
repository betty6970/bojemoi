---
title: "Entraîner un Modèle ML sur de Vraies Données d'Exploitation — et Éviter le Piège de l'Accuracy=1.0"
date: 2026-07-08T00:00:00+00:00
draft: false
tags: ["machine-learning", "threat-intelligence", "cybersecurity", "infosec", "homelab", "docker-swarm", "docker", "devops", "selfhosted", "opensource", "build-in-public", "french-tech", "apprendre-la-cyber", "debutant-en-cyber"]
summary: "J'ai branché mon modèle RandomForest sur 6 millions de vrais hosts Metasploit — et obtenu accuracy=1.0. Voilà pourquoi c'était un bug, pas un succès, et comment j'ai vraiment corrigé le tir."
description: "Retour d'expérience sur l'entraînement ML avec des données réelles issues d'un pipeline de scan offensif : dépendance circulaire features/labels, déséquilibre de classes extrême, et oversampling des hosts pwned."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

Quand on entraîne un modèle de machine learning sur des données synthétiques, on sait que c'est du bruit proprement structuré. Mais quand on le branche sur de vraies données de production — 6,15 millions de hosts, 33,7 millions de services, des années d'exploitation — et qu'on obtient `train_accuracy=1.0`, on a envie de se féliciter.

C'est un piège. Je suis tombé dedans deux fois de suite avant de comprendre ce qui se passait.

Voilà ce que j'ai appris.

## Le Contexte : ML Threat Intel sur un Pipeline Offensif

Mon homelab tourne sur Docker Swarm avec un pipeline de scan continu : `bm12` fait du fingerprinting massif, `uzi` tente des exploits sur les services détectés, `nuclei` cherche des CVE, et tout ça atterrit dans une base Metasploit (PostgreSQL) qui grossit à ~9 GB.

En parallèle, j'ai un service `ml-threat-intel-api` qui classe les IPs en `benign / suspicious / malicious` et calcule un score de réputation. Jusqu'ici, il tournait sur des données **synthétiques** — des distributions aléatoires que j'avais générées moi-même. Évidemment, le modèle apprenait parfaitement des patterns que j'avais inventés.

L'objectif : le brancher sur les vraies données MSF.

## Version 1 : Accuracy=1.0 (Premier Piège)

La première implémentation était directe. Pour chaque host dans MSF, je calculais :

```python
features = [
    reputation_score,   # min(100, port_scan_count*3 + malware_hits*15)
    age_days,
    0.0,                # report_count (indisponible)
    70.0,               # country_risk (fixe)
    50.0,               # asn_reputation (neutre)
    port_scan_count,
    malware_hits,       # ← COUNT(vulns) depuis MSF
    ...
]

# Labels
if malware_hits >= 3 or port_scan_count >= 10:
    label = 2  # malicious
elif port_scan_count >= 3 or malware_hits >= 1:
    label = 1  # suspicious
else:
    label = 0  # benign
```

Résultat après entraînement : `train_accuracy=1.0`, `test_accuracy=1.0`.

Le problème ? **Les labels sont une fonction déterministe des features.** Le modèle lit `malware_hits` à l'index 6, applique le seuil que j'ai codé dans les labels, et obtient accuracy parfaite — non pas parce qu'il a appris quelque chose, mais parce qu'il *réapprend la règle if/else que j'avais moi-même écrite*.

C'est de la tautologie, pas du machine learning.

## Version 2 : Accuracy=0.9999 (Deuxième Piège)

J'ai corrigé en séparant les sources : `confirmed_vulns` (COUNT des vulns MSF) pour les labels uniquement, et `filtered_port_count` en remplacement à l'index 6 des features.

```python
# confirmed_vulns → labels seulement, jamais dans X
if confirmed_vulns >= 3:
    label = 2
elif confirmed_vulns >= 1:
    label = 1
else:
    label = 0

# feature[6] = filtered_port_count (indépendant des labels)
features = [..., port_scan_count, filtered_port_count, ...]
```

Résultat : `train_accuracy=0.9999`.

Encore trop bon ? Oui. Cette fois le problème était différet : sur 50 000 hosts échantillonnés aléatoirement, il n'y avait que **5 hosts avec des vulns confirmées**. Soit 0,01% de la base.

La distribution réelle : `benign=49995, suspicious=3, malicious=2`.

Le modèle prédit "benign" pour tout, il a raison 99.99% du temps. L'accuracy est un indicateur inutile quand les classes sont aussi déséquilibrées.

## Version 3 : Oversampling des Hosts Pwned (La Vraie Solution)

Le problème n'est pas la proportion naturelle — elle est réaliste, la plupart des hosts scannés ne sont pas exploités. Le problème c'est qu'avec 5 exemples positifs, le modèle n'a rien à apprendre.

La solution : **fetcher exhaustivement tous les hosts pwned, puis échantillonner les benign**.

```python
# 1. Tous les hosts avec au moins une vuln confirmée (exhaustif)
cur.execute("""
    SELECT h.id, h.address::text, age_days,
           COUNT(DISTINCT CASE WHEN s.state='open' THEN s.id END) AS port_scan_count,
           COUNT(DISTINCT CASE WHEN s.state='filtered' THEN s.id END) AS filtered_port_count,
           COUNT(DISTINCT v.id) AS confirmed_vulns
    FROM hosts h
    LEFT JOIN services s ON s.host_id = h.id
    LEFT JOIN vulns v    ON v.host_id = h.id
    WHERE h.id IN (SELECT DISTINCT host_id FROM vulns)
    GROUP BY h.id, h.address, h.created_at
""")
pwned_rows = cursor.fetchall()  # → 184 hosts

# 2. Échantillon aléatoire de benign (ratio 5:1)
n_benign = max(len(pwned_rows) * 5, 1000)
cur.execute("""
    ... WHERE h.id NOT IN (SELECT DISTINCT host_id FROM vulns)
    LIMIT %s
""", (n_benign,))
benign_rows = cursor.fetchall()  # → 1000 hosts
```

Distribution finale : `benign=1000, suspicious=119, malicious=65`.

Résultat : `train_acc=0.9727`, **`test_acc=0.9331`**.

Ce gap train/test (4 points) indique que le modèle généralise réellement plutôt que mémoriser. Ce n'est pas parfait — 184 hosts pwned reste peu pour un RandomForest — mais c'est honnête.

## Ce que les Vulns MSF Représentent Vraiment

Un point important sur la qualité des labels : dans Metasploit, la table `vulns` est alimentée par les modules qui *tentent* un exploit. Certains enregistrements correspondent à des RCE confirmées (meterpreter, shell), d'autres à des tentatives qui ont retourné un faux positif.

Dans mon pipeline, `uzi` pousse ses résultats dans MSF via RPC. Les vulns enregistrées sont des exploits qui ont retourné `SESSION` — donc des compromissions réelles dans la grande majorité des cas. C'est de la ground truth exploitable, mais pas parfaite.

Pour améliorer encore, les prochaines étapes seraient :
- Croiser avec les sessions Sliver actives (compromissions confirmées avec beacon)
- Enrichir avec les findings DefectDojo validés par un analyste

## Ce que le Modèle Apprend Maintenant

Avec les bons labels et les bonnes features, le RandomForest peut maintenant apprendre des patterns réels :

- Un host avec 15 ports ouverts et 8 filtrés a plus de chances d'être exploitable qu'un host avec 2 ports ouverts
- Les hosts récemment ajoutés à la base (age_days faible) sont souvent des targets actives du pipeline
- La combinaison port_scan_count + filtered_port_count donne une empreinte d'exposition réseau

Ce ne sont pas des règles codées en dur — c'est ce que le modèle découvre dans les données.

## Architecture du Retrain Loop

Le tout est intégré dans l'API FastAPI avec un loop de retrain asynchrone :

```python
async def _retrain_loop(interval_hours: float):
    await asyncio.sleep(interval_hours * 3600)  # première run après 24h
    while True:
        async with _retrain_lock:
            metrics = await loop.run_in_executor(pool, train_from_msf)
            ml_pipeline.load_models()  # rechargement à chaud
        await asyncio.sleep(interval_hours * 3600)
```

Et un endpoint pour déclencher manuellement :

```bash
curl -X POST http://threat-intel.bojemoi.lab.local/models/retrain
# → {"status": "started", "last_retrain": null}
```

Le modèle se réentraîne automatiquement toutes les 24h sur les nouvelles données MSF, sans redémarrage du service.

## Les Leçons

**1. Accuracy=1.0 est presque toujours un bug.**
Soit les labels sont une fonction des features (dépendance circulaire), soit les classes sont tellement déséquilibrées que "prédire la classe majoritaire" suffit.

**2. Avec des données très déséquilibrées, la bonne métrique est recall sur la classe minoritaire.**
Une accuracy de 93% qui rate 40% des hosts malicious est moins utile qu'une accuracy de 85% qui les détecte tous.

**3. L'oversampling stratégique est plus honnête que le LIMIT aléatoire.**
Fetcher 50k hosts au hasard dans une base où 0,003% sont pwned donne un dataset inutile. Fetcher tous les pwned + un échantillon benign donne un dataset exploitable.

**4. Les données synthétiques ne sont pas inutiles — elles stabilisent.**
Mélanger 20% de données synthétiques aux vraies données évite que le modèle oublie les patterns généraux quand les vraies données sont trop concentrées sur un sous-ensemble.

Le code est dans le repo, le service tourne. Le prochain chantier : brancher les sessions Sliver pour avoir une ground truth encore plus propre.

---

*Build in public sur [@bojemoi_ptaas](https://t.me/bojemoi_ptaas)*
