---
title: "[myai] fix(db): remplace connect-per-query par ThreadedConnectionPool psycopg2"
date: 2026-11-01T01:42:01+01:00
draft: false
tags: ["commit", "myai", "main"]
categories: ["Git Activity"]
summary: "Commit cb7b8ba par Betty dans myai"
author: "Betty"
---

## Commit `cb7b8ba`

| | |
|---|---|
| **Repository** | myai |
| **Branch** | `main` |
| **Author** | Betty |
| **Hash** | `cb7b8baae02e218c211e7c34190461e587f294dc` |


### Description

Chaque _connect() créait une nouvelle connexion TCP (handshake+auth).
Avec 16 attaques concurrentes, les connexions s'accumulaient plus vite
que le GC Python ne les libérait → saturation max_connections=200.

Solution: ThreadedConnectionPool par DB (myai=20, msf=8, autres=3).
_PooledConn wrappe la vraie connexion ; close() retourne au pool via
putconn() au lieu de fermer le socket. __setattr__/__getattr__ délèguent
tous les attributs (dont autocommit) vers la vraie connexion.

Résultat: 170 connexions idle → 6 connexions stables sous charge.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

### Files Changed

```
M	app/db.py
```

### Diff Summary

```
 app/db.py | 106 +++++++++++++++++++++++++++++++++++++++++++++++++++++++-------
 1 file changed, 94 insertions(+), 12 deletions(-)
```
