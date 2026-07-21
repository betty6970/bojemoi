---
title: "Remplacer Ollama par Claude API dans un Alert-Agent Docker Swarm"
date: 2026-07-21T00:00:00+00:00
draft: false
tags: ["cybersecurity", "infosec", "homelab", "docker-swarm", "docker", "devops", "selfhosted", "opensource", "build-in-public", "french-tech", "apprendre-la-cyber", "threat-intelligence"]
summary: "Mon alert-agent appelait Ollama/Mistral pour prendre des décisions de remédiation. Problème : 40+ secondes de latence, timeouts, et une sévérité figée à 'warning'. Voilà comment j'ai branché Claude Haiku à la place — et pourquoi ça change vraiment quelque chose."
description: "Intégration de Claude API (Anthropic) dans un alert-agent Prometheus/Docker Swarm pour remplacer Ollama. Sévérité dynamique, latence réduite de 40s à 2s, architecture multi-backend."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

Mon homelab tourne sur Docker Swarm avec un pipeline de sécurité continu. Quand Prometheus déclenche une alerte — swap élevé, service crashé, disk plein — un composant que j'appelle l'**alert-agent** reçoit le webhook, enrichit le contexte avec des infos Docker, consulte un LLM pour décider quoi faire, et envoie le résultat sur Telegram.

Jusqu'ici, ce LLM c'était Ollama avec Mistral:latest, tournant en local sur meta-68.

Le problème : ça ne fonctionnait plus vraiment.

## Le Problème avec Ollama

Ollama était là depuis le début, mais au fil des mois, meta-68 est devenu de plus en plus chargé : MSF teamserver (6 GB RAM), ZAP qui scanne en continu, 15 replicas bm12, 3 replicas uzi... Le modèle Mistral avait du mal à répondre dans les temps.

En mesurant directement :

```
status: 200 time: 42.9 s
{"action":"assistant_response","message":"Understood. I have received a test message..."}
```

**43 secondes.** Et même là, Mistral ignorait le format JSON demandé et répondait en texte libre.

Avec un timeout à 30s dans le code, chaque alerte finissait en `notify_only` par défaut, sans décision LLM réelle. Le fallback prenait le relais — ce qui était mieux que rien, mais l'agent ne servait plus à grand chose.

## L'autre Problème : la Sévérité Figée

Toutes mes alertes arrivaient comme `⚠️ Severity: warning`. Pourquoi ? Parce que la sévérité affichée dans Telegram venait directement du label Prometheus, qui est défini statiquement dans les règles d'alerting.

`HighSeverityFindingsFound` → `warning`. `NodeHighSwapUsage` → `warning`. `DiskAlmostFull` → `warning`.

Tout est `warning`. C'est inutile — un swap à 85% sur le manager n'a pas le même impact qu'un disk à 99% sur le worker qui héberge la base MSF.

## La Solution : Claude API avec Évaluation Dynamique

J'ai intégré Claude Haiku (Anthropic) comme backend LLM, avec deux changements clés.

### 1. Architecture multi-backend

Le backend LLM est maintenant configurable via une variable d'environnement `LLM_BACKEND` :

```python
async def _call_claude(messages: list) -> dict:
    client = anthropic.AsyncAnthropic(api_key=settings.claude_api_key)
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    user_messages = [m for m in messages if m["role"] != "system"]
    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=256,
        system=system,
        messages=user_messages,
    )
    return _extract_json(response.content[0].text)
```

`LLM_BACKEND=claude` active Claude. `LLM_BACKEND=ollama` revient à Mistral local. `LLM_BACKEND=kimi` appellerait Kimi K3 via Moonshot AI. Pas de rebuild nécessaire pour switcher.

### 2. Sévérité évaluée par le LLM

J'ai modifié le system prompt pour demander au LLM d'évaluer la sévérité réelle de l'alerte, indépendamment du label Prometheus :

```
Severity levels (assess based on actual risk, ignore Prometheus label):
- critical: immediate risk of data loss, service outage, or security breach
- high: significant degradation, likely to escalate without action
- medium: noticeable issue, should be addressed soon
- low: minor issue, informational
- info: no real impact

Respond with ONLY a JSON object:
{"action": "<action>", "severity": "<severity>", "reason": "<brief reason>", "params": {}}
```

Le JSON de réponse inclut maintenant un champ `severity` que le LLM choisit lui-même. Ce champ remplace le label Prometheus dans le message Telegram.

### 3. Emojis adaptatifs

```python
severity_emoji = {
    "critical": "🔴",
    "high":     "🟠",
    "medium":   "🟡",
    "low":      "🔵",
    "info":     "⚪",
}.get(severity or "", "⚠️")
```

## Résultat

Avant :
```
🤖 Alert-Agent
🔔 Alert: NodeHighSwapUsage
⚠️ Severity: warning
🧠 LLM decision: notify_only
💬 Reason: LLM unavailable: ReadTimeout
✅ Action: notify_only
```

Après :
```
🤖 Alert-Agent
🔔 Alert: NodeHighSwapUsage
🟠 Severity: high
🧠 LLM decision: notify_only
💬 Reason: Swap at 85% on the Swarm manager — no Docker service to restart, but warrants monitoring. Escalate if it reaches 95%.
✅ Action: notify_only
```

Latence : **2.4 secondes** au lieu de 40+. La sévérité est maintenant contextuelle — le même `NodeHighSwapUsage` peut être `medium` à 60% et `high` à 85%.

## Ce que j'ai Gardé d'Ollama

Le stack `51-service-ollama.yml` est conservé avec `replicas: 0`. Si un jour Claude API est indisponible ou trop coûteux, un `docker service scale ollama_ollama=1` + `LLM_BACKEND=ollama` suffit à revenir en arrière.

C'est l'avantage de l'architecture multi-backend : pas de couplage fort avec un provider.

## Leçon

Un LLM local gratuit peut sembler idéal pour ce genre d'usage. Mais quand le node est déjà à 90% de sa capacité RAM/CPU, l'inference locale devient le goulot d'étranglement. À 0.25$ / million de tokens d'input pour Haiku, et avec des alertes qui se déclenchent quelques dizaines de fois par jour au max, le coût mensuel sera probablement inférieur à 1$.

Parfois, l'API cloud est la solution pragmatique.
