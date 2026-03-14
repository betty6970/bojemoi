Inspiré par l'annonce Kali Linux + Claude MCP, on a construit un serveur MCP local pour Bojemoi Lab en une session.
Résultat : Claude Code peut maintenant interroger directement la DB Metasploit (6M+ hosts), lancer des scans nmap, faire de l'OSINT, et gérer Faraday — sans sortir du cluster.

## Le déclencheur

> **Moi :** j'ai lu que Kali Linux a annoncé le support natif pour l'IA via MCP — Claude intégré directement dans les engagements pentest.

L'article décrivait une architecture avec Claude Desktop (cloud) + `mcp-kali-server` sur Kali Linux. L'idée : piloter nmap, Metasploit, SQLMap en langage naturel.

Claude a répondu :

> *Ton infra fait déjà mieux sur certains points : tout tourne en local (pas de cloud pour les données de scan), borodino = autonome, Faraday centralise les findings. Ce qui manque : l'interface conversationnelle.*

La différence entre leur approche et Bojemoi : ils ciblent l'humain qui pilote un engagement interactif, Bojemoi cible l'automatisation continue en arrière-plan. Mais les deux peuvent coexister.

---

## L'idée : un MCP server local

Au lieu d'envoyer les cibles vers Anthropic via Claude Desktop, on expose un serveur MCP **sur le cluster** — Claude Code (CLI sur meta-76) s'y connecte via HTTP/SSE local.

Architecture proposée :

```
Claude Code CLI (meta-76, host)
    ↕ HTTP/SSE localhost:8001
MCP Server (Docker service, manager node)
    ├── PostgreSQL msf DB   — réseau backend
    ├── Faraday API :5985   — réseau borodino_pentest
    ├── nmap subprocess
    └── OSINT lookup (ip-api, OTX, ThreatCrowd...)
```

9 outils exposés :

| Outil | Description |
|-------|-------------|
| `query_hosts` | Filtrer les hôtes msf (OS, classification, range) |
| `query_services` | Services d'un hôte |
| `get_host_details` | Détails + scan_details JSON bm12 |
| `get_scan_stats` | Stats globales DB |
| `run_nmap` | Scan ciblé (basic/full/stealth/udp/quick) |
| `lookup_ip` | OSINT enrichment (threat score, géo, abus) |
| `list_workspaces` | Workspaces Faraday |
| `get_vulns` | Vulnérabilités Faraday (filtrables) |
| `add_vuln` | Ajouter un finding |

---

## Implémentation

Fichiers créés :

```
/opt/bojemoi/mcp-server/
├── server.py          # Serveur MCP (FastAPI + SSE)
├── requirements.txt
├── Dockerfile
└── tools/
    ├── database.py    # Queries PostgreSQL (msf DB)
    ├── faraday.py     # API Faraday
    ├── nmap.py        # nmap subprocess
    └── osint.py       # OSINT lookup
```

Stack Docker séparée (`49-service-mcp.yml`) — pas dans borodino, service indépendant sur le manager.

Config Claude Code (`.mcp.json`) :

```json
{
  "mcpServers": {
    "bojemoi": {
      "url": "http://localhost:8001/sse",
      "type": "sse"
    }
  }
}
```

Un point de friction : le réseau Faraday s'appelle `borodino_pentest` (pas `pentest`) — corrigé dans le stack après le premier déploiement.

---

## Résultat

```
Service  : mcp_mcp-server  (meta-76, port 8001)
Health   : {"status":"ok","server":"bojemoi-mcp"}
DB       : 6.2M hosts, 34.2M services — connexion OK
```

Depuis cette session, dans Claude Code, je peux dire :

> *"Montre-moi les serveurs web classifiés par bm12 avec un threat score élevé"*

Et Claude interroge directement la DB via les outils MCP — sans commandes manuelles, sans quitter la session.

---

## Points de vigilance

L'article Kali Linux mentionnait plusieurs risques de ce type d'architecture :
- **Prompt injection** : l'output d'un outil malicieux peut manipuler l'IA
- **Escalade non voulue** : Claude pourrait lancer des actions imprévues
- **Audit trail** : difficile de tracer ce qui a été lancé et pourquoi

Sur Bojemoi, le risque est réduit : tout est local, les outils sont en lecture seule pour la DB msf, et `run_nmap` est limité aux modes prédéfinis. Faraday write (`add_vuln`) reste explicite.

---

## Rebuild

```bash
cd /opt/bojemoi
docker build -f mcp-server/Dockerfile -t localhost:5000/bojemoi-mcp:latest mcp-server/
docker push localhost:5000/bojemoi-mcp:latest
docker stack deploy -c stack/49-service-mcp.yml mcp --prune --resolve-image always
```

---

*Note : Claude peut faire des erreurs, moi aussi. Le serveur MCP est un outil d'assistance — pas un remplacement du jugement humain pendant un engagement.*

#mcp #claude #cybersecurity #homelab #docker-swarm #pentest #build-in-public #french-tech #osint #faraday #selfhosted
