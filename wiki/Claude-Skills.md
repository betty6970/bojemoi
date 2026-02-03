# Claude Code Skills

Commandes personnalisées pour Claude Code dans Bojemoi Lab.

## Skills Disponibles

| Skill | Description |
|-------|-------------|
| `/monitor` | Statut système global |
| `/alerts` | Gestion des alertes Prometheus |
| `/faraday` | Gestion Faraday |
| `/swarm` | Docker Swarm operations |
| `/pentest` | Orchestrateur de pentest |

## /monitor

Vérifie l'état global du système.

```bash
/monitor
```

**Affiche:**
- Load average (1/5/15 min)
- Usage mémoire
- Top conteneurs par CPU
- Alertes actives
- Services avec problèmes

## /alerts

Gestion des alertes Prometheus/Alertmanager.

```bash
/alerts              # Liste les alertes actives
/alerts list         # Idem
/alerts rules        # Liste toutes les règles configurées
/alerts cpu          # Détail des alertes/métriques CPU
```

**Exemples:**
```bash
/alerts cpu
# Affiche:
# ✓ meta-76: 45.2% [█████████░░░░░░░░░░░]
# ✓ meta-70: 38.1% [███████░░░░░░░░░░░░░]
# ⚠️ meta-68: 87.3% [█████████████████░░░]
```

## /faraday

Opérations Faraday vulnerability management.

```bash
/faraday status      # Vérifie la connexion
/faraday workspaces  # Liste les workspaces
/faraday import      # Importe les résultats en attente
/faraday import --dry-run  # Prévisualise l'import
/faraday list        # Liste les fichiers de résultats
```

**Exemples:**
```bash
/faraday status
# {
#   "tool": "Faraday",
#   "status": "connected",
#   "url": "http://faraday:5985",
#   "workspaces": ["default", "production"]
# }

/faraday import
# Import complete: 5 imported, 0 failed
```

## /swarm

Gestion du cluster Docker Swarm.

```bash
/swarm status        # Vue d'ensemble cluster/services
/swarm nodes         # Statut des nodes
/swarm deploy base   # Déploie le stack base
/swarm deploy borodino  # Déploie le stack borodino
/swarm scale <service> <n>  # Scale un service
/swarm logs <service>  # Logs d'un service
```

**Exemples:**
```bash
/swarm status
# === Cluster Nodes ===
# ID     HOSTNAME   STATUS  AVAILABILITY  MANAGER STATUS
# xxx    meta-76    Ready   Active        Leader
# xxx    meta-70    Ready   Active
# xxx    meta-68    Ready   Active

/swarm scale borodino_ak47-service 3
# borodino_ak47-service scaled to 3

/swarm logs base_prometheus
# [derniers 50 logs avec timestamps]
```

## /pentest

Orchestrateur de tests de pénétration.

```bash
/pentest status      # Statut orchestrator et plugins
/pentest plugins     # Liste les plugins et fonctions
/pentest results     # Liste les résultats de scans
```

**Exemples:**
```bash
/pentest status
# === Orchestrator Status ===
# pentest-orchestrator: 1/1
# nuclei-api: 1/1
# zap-scanner: 2/2
#
# === Plugin Status ===
# ✓ plugin_faraday: connected
# ✓ plugin_nuclei: loaded
# ✓ plugin_zap: loaded

/pentest plugins
# [Faraday] plugin_faraday v1.0.0
#   Plugin pour Faraday vulnerability management
#   Functions: import_results, get_status, list_workspaces...
```

## Emplacement des Skills

Les skills sont définis dans:
```
/opt/bojemoi/.claude/commands/
├── alerts.md
├── faraday.md
├── monitor.md
├── pentest.md
└── swarm.md
```

## Créer un Nouveau Skill

1. Créer un fichier markdown dans `/opt/bojemoi/.claude/commands/`:

```bash
cat > /opt/bojemoi/.claude/commands/mon-skill.md << 'EOF'
# Mon Skill

Description de ce que fait le skill.

## Arguments

- `arg1` - Description
- `arg2` - Description

## Instructions

Instructions pour Claude sur comment exécuter le skill...

### Pour `arg1`:
```bash
commande à exécuter
```

## Output Format

Format de sortie attendu...
EOF
```

2. Le skill sera disponible immédiatement via `/mon-skill`

## Bonnes Pratiques

1. **Nommer clairement** - Utiliser des noms descriptifs
2. **Documenter les arguments** - Lister tous les arguments possibles
3. **Fournir des exemples** - Montrer les commandes exactes
4. **Gérer les erreurs** - Prévoir les cas d'erreur
5. **Format de sortie** - Définir un format clair et lisible
