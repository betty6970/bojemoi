---
title: "Intégrer Nmap et Metasploit via MSFRPC : le pont XML de Bojemoi Lab"
date: 2026-07-17
draft: false
tags: ["homelab", "docker", "cybersecurity", "build-in-public", "french-tech", "infosec"]
summary: "Décryptage de msf_import.py, le script Python qui automatise l'ingestion des scans Nmap dans la base de données Metasploit via MSFRPC dans l'architecture Docker Swarm de Bojemoi Lab."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

## Le problème qu'on cherchait à résoudre

Dans un lab red-team, le scan réseau et l'exploitation sont deux phases distinctes, souvent gérées par des outils différents. Le problème classique : Nmap découvre des hôtes et des services, mais ces résultats restent dans un fichier XML quelque part sur le disque. Metasploit, lui, ne sait rien de tout ça. Il faut manuellement importer, corréler, ou pire — retaper des IPs à la main dans `msfconsole`.

`msf_import.py` est le petit pont qui automatise ce handoff. Il prend un fichier XML produit par Nmap et l'injecte directement dans la base de données Metasploit via l'API RPC. Simple sur le papier, mais quelques détails techniques méritent qu'on s'y attarde.

---

## Ce que fait le script, étape par étape

### 1. Validation préalable du XML

Avant même de toucher au réseau, le script effectue deux vérifications légères sur le contenu du fichier :

```python
if '<nmaprun' not in xml_data:
    print('[WARN] Empty/invalid nmap XML, skipping import')
    sys.exit(0)

if '<host ' not in xml_data and '<host>' not in xml_data:
    print('[INFO] No hosts up in scan, skipping import')
    sys.exit(0)
```

C'est du parsing XML "paresseux" — on évite d'instancier un parser complet (`lxml`, `xml.etree`) pour un check binaire : est-ce que ce fichier ressemble à un vrai résultat Nmap avec au moins un hôte actif ? Si non, on sort proprement sans solliciter MSFRPC. Dans un environnement où des dizaines de scans peuvent se déclencher en parallèle (scan de sous-réseaux morts, scan de plages RFC1918 vides), cette optimisation évite pas mal de bruit sur le bus RPC.

### 2. La sérialisation MessagePack

L'API MSFRPC n'utilise pas JSON. Elle utilise **MessagePack**, un format binaire de sérialisation compacte. Le choix de Metasploit Framework pour son RPC n'est pas anodin : MessagePack est environ 2x plus compact que JSON et significativement plus rapide à désérialiser pour des payloads larges — exactement ce qu'on veut quand on importe un XML de scan qui peut facilement dépasser plusieurs mégaoctets.

```python
data=msgpack.dumps([b'auth.login', 'msf', MSF_PASS]),
headers={'Content-Type': 'binary/message-pack'},
```

Le protocole MSFRPC attend des tableaux MessagePack où le premier élément est le nom de la méthode en bytes, suivis des arguments. C'est un protocole RPC minimaliste, documenté dans le wiki Metasploit, mais peu de ressources en parlent clairement.

### 3. Le flux auth → import → logout

Le script suit scrupuleusement le cycle de vie d'une session RPC :

1. **`auth.login`** → récupère un token de session
2. **`db.import_data`** → envoie le XML brut dans un champ `data` d'un dictionnaire MessagePack
3. **`auth.logout`** → invalide le token

Le timeout de 300 secondes sur l'import est intentionnel. Pour de gros fichiers XML (scans intensifs avec scripts NSE, détection d'OS, etc.), Metasploit peut prendre du temps à parser, déduire les services, et alimenter la base PostgreSQL sous-jacente. Trop court, et on timeout sur des scans légitimes.

### 4. Gestion du token avec double clé bytes/str

Un détail subtil et honnêtement un peu moche :

```python
token = result.get(b'token') or result.get('token')
```

Selon la version de la bibliothèque `msgpack` Python et les options de désérialisation, les clés peuvent revenir soit en `bytes` soit en `str`. Plutôt que de fixer le comportement avec `raw=False` dans `msgpack.loads()`, on gère les deux cas. C'est du code défensif pragmatique, mais c'est aussi un signal qu'on n'a pas totalement maîtrisé la configuration du client msgpack. On y reviendra.

---

## L'architecture dans laquelle ça s'inscrit

Dans Bojemoi Lab, ce script tourne typiquement comme une étape post-scan dans un pipeline orchestré par Docker Swarm. Le service `msf-teamserver` expose son API RPC sur le port 55553 en TLS (auto-signé, d'où le `verify=False`), et les autres services du stack peuvent l'appeler pour alimenter la base collaborative.

La configuration est entièrement pilotée par variables d'environnement (`MSF_HOST`, `MSF_PORT`, `MSF_RPC_PASS`), ce qui s'intègre naturellement avec les secrets Docker Swarm ou un Vault externe.

---

## Les limitations honnêtes

**Le mot de passe dans l'environnement.** `MSF_RPC_PASS` avec une valeur par défaut `totototo` — c'est un lab, on le sait, mais c'est exactement le genre de dette technique qui finit en prod si on n'y prend pas garde. Un TODO pour migrer vers Docker Secrets ou au moins forcer l'absence de valeur par défaut.

**`verify=False` partout.** Le TLS est là, mais sans vérification du certificat, on est vulnérable à un MITM interne. Dans un Swarm isolé c'est acceptable, mais câbler le CA du certificat auto-signé serait propre.

**Pas de retry.** Si MSFRPC est momentanément indisponible (redémarrage du service, healthcheck en cours), le script échoue sec. Un backoff exponentiel avec 3 tentatives serait bienvenu pour les pipelines automatisés.

**La double clé bytes/str.** Comme mentionné, `msgpack.loads(r.content, raw=False)` forcerait les clés en `str` et simplifierait le code. C'est un fix d'une ligne.

**Pas de gestion d'erreur sur l'import.** Si `db.import_data` retourne une erreur Metasploit (base inaccessible, XML malformé), le script affiche le statut mais sort avec code 0. Une vérification explicite du champ `result` pour détecter les erreurs améliorerait la robustesse dans les pipelines CI/CD.

---

## Ce qu'on apprend en lisant ce script

Ce composant illustre bien l'approche Bojemoi Lab : des scripts focalisés, unix-style, qui font une seule chose et s'intègrent dans un pipeline plus large. La validation préalable du XML avant d'ouvrir une connexion réseau, le respect du cycle auth/logout, et la gestion des timeouts adaptés aux charges réelles montrent une attention au comportement en production.

C'est loin d'être parfait — et c'est exactement l'intérêt de construire en public. Ces imperfections documentées valent mieux qu'une boîte noire prétendument parfaite.

Le code source complet du projet est disponible sur le dépôt Bojemoi Lab
