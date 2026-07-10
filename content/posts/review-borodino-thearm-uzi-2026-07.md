---
title: "Thearm Uzi : l'agent d'exploitation automatisé au cœur du lab red-team Bojemoi"
date: 2026-07-10
draft: false
tags: ["homelab", "docker", "cybersecurity", "build-in-public", "french-tech", "infosec"]
summary: "Plongée dans le code de thearm_uzi, le composant d'exploitation automatisée de Bojemoi Lab qui orchestre Metasploit, un LLM local et Sliver pour pwner des cibles de manière autonome."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

## C'est quoi thearm_uzi ?

Si Bojemoi Lab était une équipe red team, `thearm_uzi` serait l'opérateur qui dort jamais. C'est le worker Python qui tourne dans Docker Swarm, qui écoute une queue Valkey (le fork Redis open source), et qui pour chaque cible qui arrive décide quoi faire, comment l'attaquer, et où envoyer les résultats.

Le nom est explicite : c'est une arme automatique. Pas très subtil, mais dans un lab red-team, on assume.

Ce composant vit dans le service `borodino` — un conteneur basé sur Metasploit Framework avec pymetasploit3, paramiko, psycopg2 et un client Ollama. Il est le pendant offensif du composant de scan (`bm12_v3`) : là où bm12 découvre et cartographie, uzi exploite.

## Architecture : comment ça s'intègre dans le lab

Le flux global ressemble à ça :

```
bm12_v3 (scan)
    │
    └─► hosts table (PostgreSQL MSF DB)
              │
              └─► pentest:uzi_queue (Valkey)
                        │
                        └─► thearm_uzi (exploitation)
                                  │
                                  ├─► sessions MSF (meterpreter/shell)
                                  ├─► pentest:dojo_queue → DefectDojo
                                  ├─► pentest:nuclei_queue → Nuclei
                                  ├─► zap:targets → OWASP ZAP
                                  └─► pentest:sliver_queue → Sliver C2
```

Uzi ne scanne pas. Il reçoit une cible déjà profilée, avec ses services ouverts, ses produits identifiés, son OS détecté, son `attack_surface` (indicateurs de vulnérabilités), et il décide de la séquence d'attaque.

## Les choix techniques intéressants

### 1. La sélection de cible par queue plutôt que polling DB

Au lieu d'aller chercher des cibles en base à intervalle fixe, uzi consomme une queue `pentest:uzi_queue` via `brpop` (blocking pop). C'est propre : plusieurs workers peuvent tourner en parallèle sans se marcher dessus, et le lock optimiste dans `uzi_scan_log` (INSERT ON CONFLICT DO NOTHING) évite le double-traitement.

```python
item = r_queue.brpop('pentest:uzi_queue', timeout=30)
```

Le lock stale est nettoyé automatiquement au boot :

```python
DELETE FROM uzi_scan_log
WHERE status = 'running'
AND locked_at < NOW() - INTERVAL '2 hours'
```

C'est du distributed locking minimaliste mais efficace pour un lab.

### 2. La séquence d'attaque en deux phases

Uzi suit une logique séquentielle claire :

**Phase 1 — Brute force** : on tente d'abord de craquer les credentials sur tous les services détectés. SSH en priorité, avec une sélection intelligente des wordlists. En mode debug (lab local), si des credentials sont connus, on passe directement à la connexion Paramiko.

**Phase 2 — Exploitation de vulnérabilités** : si le brute force échoue, on construit une liste d'exploits ciblés via `build_targeted_exploits` et on les joue un par un.

C'est une philosophie red team réaliste : les credentials faibles sont beaucoup plus courants que les 0-days.

### 3. Le filtrage d'exploits LLM-assisté

C'est là que ça devient intéressant. La fonction `extract_search_terms_via_ai` envoie à Ollama/Mistral 7b-instruct les services non couverts par le mapping statique et lui demande des termes de recherche Metasploit.

```python
payload = {
    'model': OLLAMA_MODEL,
    'messages': [{
        'role': 'system',
        'content': 'Extract Metasploit module search terms... Return JSON only: {"search_terms": [...]}',
    }, {'role': 'user', 'content': json.dumps(unmapped)}],
    'temperature': 0.1,
}
```

La température à 0.1 est délibérée : on veut de la reproductibilité, pas de la créativité. Le LLM est utilisé comme un dictionnaire intelligent, pas comme un raisonneur.

Le fallback est gracieux : si Ollama ne répond pas, on continue avec le mapping statique. Le LLM enrichit, il ne bloque pas.

### 4. La sélection de payload par profil cible

La fonction `_rank` est un petit bijou de pragmatisme. Elle trie les payloads disponibles selon l'architecture de la cible et la disponibilité d'un redirecteur C2 (LHOST) :

- Si LHOST est défini → reverse payloads prioritaires (le firewall de la cible bloque probablement les connexions entrantes)
- Si pas de LHOST → bind payloads
- Adaptation ARM/MIPS pour les cibles IoT

```python
_prefer_reverse = bool(LHOST)
```

### 5. La gestion des redirecteurs C2

```python
def _pick_redirector() -> str:
    redirectors_env = os.getenv("C2_REDIRECTORS", "")
    if redirectors_env:
        candidates = [ip.strip() for ip in redirectors_env.split(",") if ip.strip()]
        if candidates:
            chosen = random.choice(candidates)
            return chosen
```

On peut configurer un pool de redirecteurs (séparés par virgules) et uzi en choisit un aléatoirement. C'est une infrastructure C2 basique mais fonctionnelle pour un lab.

### 6. La vue SQL `target_profile`

La vue `target_profile` est une agrégation multidimensionnelle qui croise les résultats de tous les workers :

```sql
CREATE OR REPLACE VIEW target_profile AS
SELECT h.address::text, h.os_name, h.purpose,
       u.status AS uzi_status, u.winning_module,
       z.alerts AS zap_alerts, z.critical AS zap_critical,
       n.findings AS nuclei_findings,
       s.session_id AS sliver_session, ...
FROM hosts h
LEFT JOIN uzi_scan_log u ...
LEFT JOIN zap_scan_log z ...
LEFT JOIN nuclei_scan_log n ...
LEFT JOIN sliver_session_log s ...
```

D'un `SELECT * FROM target_profile` on a l'état complet d'une cible : ce qu'uzi a fait, ce que ZAP a trouvé, ce que Nuclei a remonté, si Sliver a un implant actif. C'est le tableau de bord opérationnel du lab.

## Ce que j'aurais fait différemment

### La gestion des wordlists country-specific est fragile

`_build_country_pass_file` génère un fichier de passwords combiné dans `/tmp`. C'est pratique, mais en mode multi-workers Docker Swarm, plusieurs workers peuvent tenter de créer le même fichier simultanément. Il manque un lock fichier ou une génération dans le build de l'image.

### Le parsing des credentials MS
