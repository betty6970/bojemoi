# Bojemoi Lab Wiki

Bienvenue sur le wiki de Bojemoi Lab - Infrastructure Docker Swarm avec outils de pentest et monitoring.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Docker Swarm Cluster                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   meta-68   │  │   meta-70   │  │   meta-76   │              │
│  │   (worker)  │  │   (worker)  │  │  (manager)  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
         │                  │                  │
    ┌────┴────┐        ┌────┴────┐        ┌────┴────┐
    │ Suricata│        │ Suricata│        │ Suricata│
    │ cAdvisor│        │ cAdvisor│        │ cAdvisor│
    │ Node-exp│        │ Node-exp│        │ Node-exp│
    └─────────┘        └─────────┘        └─────────┘
```

## Stacks Déployés

| Stack | Description | Fichier |
|-------|-------------|---------|
| base | Infrastructure de base (monitoring, proxy, DB) | `01-service-hl.yml` |
| borodino | Outils de pentest et scanners | `40-service-borodino.yml` |

## Liens Rapides

- [[Monitoring]] - Prometheus, Grafana, Alertmanager
- [[Alertes]] - Configuration et gestion des alertes
- [[Pentest-Orchestrator]] - Orchestrateur de scans
- [[Faraday]] - Gestion des vulnérabilités
- [[Docker-Swarm]] - Gestion du cluster
- [[Claude-Skills]] - Commandes Claude Code

## URLs des Services

| Service | URL |
|---------|-----|
| Grafana | https://grafana.bojemoi.lab |
| Prometheus | https://prometheus.bojemoi.lab |
| Alertmanager | https://alertmanager.bojemoi.lab |
| Traefik | https://traefik.bojemoi.lab |
| PgAdmin | https://pgadmin.bojemoi.lab |
| cAdvisor | https://cadvisor.bojemoi.lab |

## Contacts

- Email alertes: betty.bombers@proton.me
