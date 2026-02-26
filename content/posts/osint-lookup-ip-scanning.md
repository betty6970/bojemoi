---
title: "OSINT automatique pendant le scan d'IPs : enrichir la base en temps réel"
date: 2026-02-26T12:00:00+00:00
draft: false
tags: ["osint", "cybersecurity", "threat-intelligence", "homelab", "docker-swarm", "infosec", "docker", "devops", "selfhosted", "opensource", "debutant-en-cyber", "apprendre-la-cyber", "build-in-public", "french-tech", "soc", "blue-team"]
summary: "Comment j'ai ajouté un enrichissement OSINT automatique sur chaque IP lors du fingerprinting réseau — détection de menaces en temps réel, 20 minutes de dev avec Claude."
description: "Ajout d'un module OSINT (AbuseIPDB, AlienVault OTX, ip-api) dans l'outil bm12 de Bojemoi Lab pour enrichir automatiquement chaque host scanné avec un threat score et flaguer les IPs malveillantes."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

Voici la question du jour posée à Claude — et ce qui en a suivi.

> *Note : vous remarquerez l'absence de questionnement sur la légalité. Ces outils sont des outils de masscan/fingerprinting dans le cadre de mon homelab. Claude ne doute pas non plus.*

---

## La Question

> **Moi :** Je me demandais si dans ak47 ou BM12 ou uzi, s'il ne fallait pas faire une recherche OSINT comme pour `/register` du telegram_bot. Cela permettrait de mettre à jour le record host de msf dans la foulée et détecter plus rapidement les IPs malveillantes.

En clair : pendant qu'on scanne une IP (fingerprinting, ports, services), pourquoi ne pas interroger en même temps les bases de données publiques de threat intelligence ? On saurait immédiatement si l'IP est connue comme malveillante.

---

## L'Analyse de Claude

Claude a regardé ce que fait déjà `/register` côté bot Telegram :

- **Shodan** : ports, vulnérabilités
- **VirusTotal** : présence dans des listes malware
- **AbuseIPDB** : rapports d'abus
- **AlienVault OTX** : pulses de menace
- **IPInfo** : géolocalisation, ASN, détection proxy/VPN/Tor

Et a proposé un tableau de décision pour choisir où intégrer l'OSINT dans les outils borodino (ak47 / bm12 / uzi) :

| Outil | Pour | Contre |
|-------|------|--------|
| **ak47** | Volume maximum, enrichit dès la découverte | CIDR bulk → millions d'IPs → rate limits API immédiats |
| **bm12** | Déjà 1 host à la fois, déjà JSON dans `scan_details`, déjà update DB | Plus lent, mais contrôlable |
| **uzi** | Cible les hosts Linux vulnérables | Mode 0, pas prioritaire |

**Recommandation : bm12 est le bon endroit** — après le fingerprinting, avant le `UPDATE hosts`. On évite les rate limits en travaillant host par host.

---

## L'Implémentation

Réponse : **"oui, implémenter dans bm12"** → 20 minutes plus tard, c'était en prod.

### Ce qui a été créé

**`osint_lookup.py`** — module standalone réutilisable :
- Sans clé API : `ip-api.com` (géo, proxy/VPN/hosting), AlienVault OTX (pulses), reverse DNS
- Avec clé API optionnelle : AbuseIPDB (1000/jour gratuit), VirusTotal (4/min), Shodan
- Calcule un `threat_score` de 0 à 100
- Retourne `is_malicious` si score ≥ 70

**Intégration dans `thearm_bm12`** :
```text
# Avant (v2 sans OSINT) :
1. Sélection host → 2. NSE scripts → 3. Classification → 4. UPDATE DB

# Après (v2 avec OSINT) :
1. Sélection host → 2. NSE scripts → 3. Classification → 4. OSINT lookup → 5. UPDATE DB
```

### Ce qui est stocké en base

Dans `hosts.scan_details` (JSON existant), une nouvelle clé `osint` :

```json
{
  "server_type": "web",
  "confidence": 80,
  "osint": {
    "threat_score": 85,
    "threat_level": "critical",
    "is_malicious": true,
    "abuse_reports": 12,
    "malware_samples": 3,
    "is_proxy": false,
    "country": "RU",
    "asn": "AS12345"
  }
}
```

Pour les IPs malveillantes, `hosts.info` est aussi mis à jour :
```text
THREAT:CRITICAL score=85 abuse=12 malware=3
```

---

## Le Test en Production

Logs quelques minutes après le déploiement :

```text
[OSINT] Lookup 109.108.53.242...
[OSINT] 109.108.53.242 → score=0 (clean) OK
[DONE] 109.108.53.242 — type=web, services=7

[OSINT] Lookup 45.10.55.57...
[OSINT] 45.10.55.57 → score=72 (high) ⚠ MALICIOUS
[CLASS] 45.10.55.57 → web (confidence: 100%)
[DONE] 45.10.55.57 — type=web, services=3 ⚠ THREAT:HIGH score=72
```

Et voilà le travail : fingerprinting + OSINT pendant le masscan, pushé dans le repo Gitea, stack relancé, vérification. ✓

---

## Pour Aller Plus Loin

Pour activer les APIs payantes (plus de précision) :
```yaml
# dans le stack borodino
environment:
  - ABUSEIPDB_API_KEY=<votre_clé>
  - VIRUSTOTAL_API_KEY=<votre_clé>
  - SHODAN_API_KEY=<votre_clé>
```

Pour requêter les hosts malveillants détectés :
```sql
SELECT address, comments, scan_details->>'osint'
FROM hosts
WHERE scan_status = 'bm12_v2'
  AND info LIKE 'THREAT:%'
ORDER BY last_scanned DESC;
```

---

## Note Finale

> *Claude peut faire des erreurs, moi aussi.*
> *(1) : ak47, bm12, uzi sont les outils de masscan/fingerprinting de Bojemoi Lab.*

---

*Suivez le projet sur Telegram :*
- *Canal d'annonces* : [@bojemoi_ptaas](https://t.me/bojemoi_ptaas) — news, posts, releases
- *Groupe PTaaS* : **Bojemoi PTaaS 😈** — demandez le lien sur le canal
