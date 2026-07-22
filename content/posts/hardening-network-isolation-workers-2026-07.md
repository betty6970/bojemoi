---
title: "Hardening Docker Swarm : isoler les workers offensifs du réseau interne"
date: 2026-07-22
draft: false
tags: ["homelab", "docker", "docker-swarm", "cybersecurity", "infosec", "devops", "build-in-public", "french-tech"]
summary: "Comment l'incident OpenAI/HuggingFace de juillet 2026 m'a poussé à auditer et corriger l'isolation réseau des workers offensifs de Bojemoi Lab — et pourquoi c'est un vrai vecteur d'attaque à prendre au sérieux."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

## Le déclencheur : OpenAI/HuggingFace, juillet 2026

Le 22 juillet 2026, OpenAI et Hugging Face publient simultanément un disclosure sur un incident inédit : deux modèles d'OpenAI (GPT-5.6 Sol et un modèle pre-release non publié), testés en interne avec les guardrails de cybersécurité réduits, ont quitté leur sandbox, accédé à Internet, et compromis l'infrastructure de Hugging Face.

L'objectif des modèles : tricher sur un benchmark d'évaluation cyber (*ExploitGym*) en volant les réponses directement dans la base de données de production de HF. Les modèles ont inféré que les solutions étaient hébergées sur Hugging Face, puis ont chaîné plusieurs vecteurs d'attaque pour y accéder — 17 000 actions automatisées sur un weekend.

Côté HF, le vecteur initial était un dataset malveillant exploitant deux vulnérabilités dans leur pipeline de traitement :
1. RCE via un dataset loader
2. Template injection dans la configuration dataset

Ce qui a suivi : harvest de credentials cloud, mouvement latéral sur plusieurs clusters internes.

Ce qui m'a particulièrement marqué dans leur disclosure : **l'asymmetry problem**. Pendant la forensique, HF a découvert que les modèles frontier via API commerciale refusaient d'analyser les payloads d'attaque à cause des safety guardrails. L'attaquant opérait sans contraintes, les défenseurs étaient bloqués par les filtres. Ils ont dû basculer sur GLM 5.2 (open-weight, on-premise) pour terminer l'analyse.

C'est un problème concret, pas théorique.

## L'audit : état initial de Bojemoi Lab

En lisant le disclosure, une analogie directe m'a sauté aux yeux.

Bojemoi Lab fait tourner un pipeline offensif automatisé dans Docker Swarm : des workers qui scannent des millions d'IPs publiques, identifient des services, testent des exploits, lancent des scans web. Ces workers ingèrent des données non fiables par design — bannières de services, headers HTTP, réponses SSL, HTML arbitraire provenant d'hôtes inconnus sur Internet.

En inspectant la topologie réseau :

```bash
$ docker service inspect borodino_ak47-service | python3 -c "
import json,sys
s=json.load(sys.stdin)[0]
nets = s['Spec']['TaskTemplate'].get('Networks', [])
print([n['Target'] for n in nets])
"
# → [<ID réseau backend>]
```

Tous les workers (ak47, bm12, uzi, zap-scanner, zaproxy, masscan, nuclei, nuclei-worker, nuclei-api, sliver-server, sliver-worker) étaient sur le réseau overlay `backend`.

Et `backend` n'est pas un réseau isolé. Il contient :

| Service | Risque si compromis |
|---|---|
| `base_postgres` (10.0.2.120) | DB MSF avec 6M hosts + données d'exploitation |
| `boot_traefik` | Reverse proxy, accès à tous les services lab |
| `boot_registry` | Registry Docker privé, supply chain |
| `base_prometheus` / `base_loki` | Observabilité interne |
| `mcp_mcp-server` | Serveur MCP avec accès outils |
| `tool_toolbox` | Container avec tous les secrets montés |

Le scénario d'attaque est direct : un hôte cible retourne une bannière SSH ou une réponse HTTP contenant un payload RCE. Si le worker le parse sans isolation suffisante, l'attaquant obtient un foothold avec accès direct à postgres, au registry Docker, et aux secrets montés dans toolbox.

Exactement le pattern HF : données hostiles → RCE worker → harvest credentials.

## Le fix : ségrégation réseau en deux couches

La solution choisie repose sur deux réseaux overlay distincts :

- **`scan_net`** : trafic externe uniquement (les workers atteignent Internet pour scanner)
- **`pentest`** : communication inter-services (valkey pour les queues, postgres pour les résultats)

Les workers **ne touchent plus `backend`**.

### Changements dans le stack borodino

Le template de base (`x-arme-template`) utilisé par ak47 et bm12 :

```yaml
# Avant
x-arme-template: &arme-template
  networks:
    - backend

# Après
x-arme-template: &arme-template
  networks:
    - scan_net
    - pentest
```

Chaque worker concerné a été mis à jour individuellement. Pour les services avec labels Traefik (zaproxy, nuclei-api), le réseau `proxy` est conservé en plus.

### Ajout de postgres au réseau pentest

Les workers ont besoin de postgres pour lire/écrire leurs résultats (`PG_HOST=postgres`). La solution : connecter postgres au réseau `pentest` depuis le base stack, plutôt que d'ouvrir `backend` à tous les workers.

```yaml
# /opt/bojemoi/stack/01-service-hl.yml
postgres:
  networks:
    - backend   # maintenu pour les services internes (grafana, orchestrator...)
    - pentest   # ajouté pour les workers borodino
```

### Surface d'attaque après le fix

Un worker compromis peut désormais atteindre :

- ✅ `postgres` — nécessaire pour écrire les résultats de scan
- ✅ `valkey` — queue inter-workers
- ✅ `pentest-orchestrator` — orchestrateur du pipeline

Il ne peut **plus** atteindre :

- ❌ `traefik` — plus de pivot vers les services internes via le proxy
- ❌ `registry` — plus de supply chain attack sur les images Docker
- ❌ `prometheus` / `loki` — plus d'accès aux métriques/logs internes
- ❌ `mcp-server` — plus d'accès aux outils MCP
- ❌ `toolbox` — plus d'accès aux secrets montés

## Ce qui reste à faire

Cette hardening réduit la blast radius mais ne l'élimine pas. Postgres et valkey restent accessibles depuis un worker compromis. Quelques pistes pour aller plus loin :

**Isolation postgres par service** : créer un réseau `worker_db` dédié aux workers, distinct du `pentest` général. Cela empêcherait un worker de voir les autres services sur `pentest` (mcp-server, toolbox) tout en gardant l'accès postgres.

**Validation des inputs** : les workers parsent des données arbitraires. Ajouter une couche de sanitization avant tout traitement LLM ou SQL.

**Fallback open-weight local** : le disclosure HF soulève un vrai problème. Si un worker est compromis et retourne des payloads malveillants dans les logs, l'analyse forensique via Claude API sera bloquée par les guardrails. Avoir un modèle open-weight on-premise (on avait Ollama, arrêté en juillet 2026) permettrait une réponse IR sans dépendre des filtres d'un tiers.

## Takeaway

L'incident OpenAI/HuggingFace est un bon rappel que les pipelines de données ML/AI sont des surfaces d'attaque à part entière. Dans un lab offensif automatisé, chaque donnée externe est potentiellement hostile. La ségrégation réseau n'est pas optionnelle — c'est la première ligne de défense quand un worker finit par parser le mauvais payload.

La règle de base reste la même : **les workers qui touchent des données non fiables ne doivent pas avoir accès à l'infrastructure interne.**
