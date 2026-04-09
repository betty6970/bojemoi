# Red Team OPSEC Check

Vérifie l'étanchéité de la plateforme C2 : redirecteurs, VPN, exit IP scan, headers, ports exposés, certificats, empreinte DNS/CT, segmentation réseau, iptables.

## Arguments

- (none) / `all` — Audit complet (toutes les couches)
- `redirector` — Filtrage UA + isolation C2 sur Fly.io
- `vpn` — Tunnel OpenVPN C2 + routing
- `scan` — Exit IP via ProtonVPN (wg-gateway)
- `headers` — Headers serveur / fuite d'infra
- `ports` — Surface d'attaque publique
- `tls` — Fingerprinting certificats
- `dns` — Empreinte DNS : PTR inverse, crt.sh Certificate Transparency, WHOIS privacy
- `segmentation` — Pivot latéral depuis un conteneur Swarm compromis
- `iptables` — Règles FORWARD/DOCKER-USER sur les nœuds Swarm

## Variables de référence

```
REDIR_IP="37.16.12.4"        # redirector-1 Fly.io (cdg/Paris)
REDIR_HOST="bojemoi.me"      # VPN hub / Lightsail
MSF_PORT=4444
MSFRPC_PORT=55553
PROTONVPN_EXIT_PREFIX="149.102"   # plage ProtonVPN FR attendue
C2_VPN_SERVER="10.8.0.1"
```

## Instructions

### Pour `redirector` ou phase 1 de `all` :

Tester le filtrage UA et l'isolation du C2 depuis le redirecteur Fly.io :

```bash
REDIR_IP="37.16.12.4"

echo "=== REDIRECTEUR — UA FILTERING ==="

echo -n "  Browser normal (Mozilla) → attendu 302 : "
STATUS=$(curl -4 -so /dev/null -w "%{http_code}" -L --max-redirs 0 http://$REDIR_IP/ -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
LOC=$(curl -4 -sI http://$REDIR_IP/ -A "Mozilla/5.0" | grep -i location | tr -d '\r')
[ "$STATUS" = "302" ] && echo "✅ 302 ($LOC)" || echo "❌ reçu $STATUS"

echo -n "  UA Nmap → attendu 302 : "
STATUS=$(curl -4 -so /dev/null -w "%{http_code}" --max-redirs 0 http://$REDIR_IP/ -A "Nmap Scripting Engine")
[ "$STATUS" = "302" ] && echo "✅ 302" || echo "❌ reçu $STATUS"

echo -n "  UA masscan → attendu 302 : "
STATUS=$(curl -4 -so /dev/null -w "%{http_code}" --max-redirs 0 http://$REDIR_IP/ -A "masscan")
[ "$STATUS" = "302" ] && echo "✅ 302" || echo "❌ reçu $STATUS"

echo ""
echo "=== REDIRECTEUR — PATHS C2 ==="

for path in /api/update /assets/payload /cdn/drop /upload/data /download/file /v1/beacon; do
  RESULT=$(curl -4 -so /dev/null -w "%{http_code}" --max-time 5 http://$REDIR_IP$path -A "Mozilla/5.0")
  [ "$RESULT" != "302" ] && echo "  ✅ $path → $RESULT (non-302 = proxy actif)" || echo "  ❌ $path → 302 (devrait proxifier)"
done

echo ""
echo "=== MSF PORT DIRECT — doit être inaccessible ==="
for target in "$REDIR_IP:4444" "bojemoi.me:4444"; do
  nc -zv -w3 $(echo $target | tr ':' ' ') 2>&1 | grep -q "succeeded" \
    && echo "  ❌ $target : OUVERT (fuite !)" \
    || echo "  ✅ $target : fermé/refusé"
done
```

### Pour `vpn` ou phase 2 de `all` :

Vérifier le tunnel OpenVPN C2 sur meta-76 :

```bash
echo "=== VPN C2 — TUNNEL lab-manager ==="

echo -n "  Conteneur lab-manager-vpn : "
STATE=$(docker inspect lab-manager-vpn --format '{{.State.Status}}' 2>/dev/null || echo "absent")
[ "$STATE" = "running" ] && echo "✅ running" || echo "❌ $STATE"

echo -n "  Interface tun0 : "
docker exec lab-manager-vpn ip addr show tun0 2>/dev/null | grep -q "inet" \
  && docker exec lab-manager-vpn ip addr show tun0 | grep inet | awk '{print "✅ " $2}' \
  || echo "❌ absente"

echo ""
echo "=== ROUTING VPN C2 ==="
echo "  Routes 10.8.x via tun0 :"
docker exec lab-manager-vpn ip route | grep 10.8 | while read r; do echo "    $r"; done

echo ""
echo "=== PING VPN SERVER ==="
docker exec lab-manager-vpn ping -c2 -W2 10.8.0.1 2>/dev/null | tail -2

echo ""
echo "=== MSFRPC — accessible via VPN seulement ==="
echo -n "  55553 depuis overlay (ne doit PAS répondre publiquement) : "
nc -zv -w3 bojemoi.me 55553 2>&1 | grep -q "succeeded" \
  && echo "❌ OUVERT publiquement !" \
  || echo "✅ non joignable"
```

### Pour `scan` ou phase 3 de `all` :

Vérifier que le trafic de scan sort via ProtonVPN et non via l'IP hôte :

```bash
echo "=== EXIT IP — SCAN (wg-gateway ProtonVPN) ==="

echo -n "  IP hôte meta-76 (référence) : "
HOST_IP=$(curl -4 -s --max-time 5 https://ipinfo.io/ip 2>/dev/null || echo "N/A")
echo "$HOST_IP"

echo "  IP de sortie via ak47 (scan_net — borodino_scan_net non attachable directement) :"
AK47_NODE=$(docker service ps borodino_ak47-service --filter desired-state=running --format "{{.Node}}" 2>/dev/null | head -1)
AK47_NODE_IP=$(docker node inspect "$AK47_NODE" --format '{{.Status.Addr}}' 2>/dev/null)
ssh -p 4422 -i /home/docker/.ssh/meta76_ed25519 -o StrictHostKeyChecking=no docker@"$AK47_NODE_IP" \
  "CNAME=\$(docker ps --format '{{.Names}}' | grep ak47 | head -1); docker exec \$CNAME curl -4 -s --max-time 8 http://ipinfo.io/json" 2>/dev/null | python3 -c "
import sys, json
try:
  d = json.load(sys.stdin)
  ip = d.get('ip','N/A')
  org = d.get('org','N/A')
  country = d.get('country','N/A')
  city = d.get('city','N/A')
  print(f'  IP     : {ip}')
  print(f'  Org    : {org}')
  print(f'  Loc    : {city}, {country}')
  if 'proton' in org.lower() or 'anapaya' in org.lower() or '10.96' in ip:
    print('  Résultat : ✅ ProtonVPN confirmé')
  else:
    print('  Résultat : ⚠️  IP inattendue — vérifier wg-gateway (exit IP actuelle)')
except Exception as e:
  print(f'  ❌ Impossible de récupérer l IP ({e})')
" 2>/dev/null || echo "  ❌ Container ak47 non joignable"

echo ""
echo -n "  Service wg-gateway : "
docker service ls --filter name=borodino_wg-gateway --format "{{.Replicas}}" 2>/dev/null | \
  grep -q "^1/1" && echo "✅ 1/1" || echo "❌ down/absent"
```

### Pour `headers` ou phase 4 de `all` :

Vérifier que les headers ne révèlent pas l'infra interne :

```bash
REDIR_IP="37.16.12.4"
echo "=== HEADERS — FUITE D'INFRA ==="

HEADERS=$(curl -4 -sI http://$REDIR_IP/ -A "Mozilla/5.0")

echo "  Headers reçus :"
echo "$HEADERS" | while read line; do echo "    $line"; done

echo ""
echo "  Analyse :"

echo "$HEADERS" | grep -qi "^Server:" && {
  SRV=$(echo "$HEADERS" | grep -i "^Server:" | tr -d '\r')
  echo "  ⚠️  Server header présent : $SRV (envisager server_tokens off)"
} || echo "  ✅ Pas de Server header"

echo "$HEADERS" | grep -qi "^X-Powered-By:" \
  && echo "  ❌ X-Powered-By exposé !" \
  || echo "  ✅ Pas de X-Powered-By"

echo "$HEADERS" | grep -qE "192\.168\.|10\.[0-9]+\.|172\.(1[6-9]|2[0-9]|3[01])\." \
  && echo "  ❌ IP privée détectée dans les headers !" \
  || echo "  ✅ Pas d'IP RFC1918 dans les headers"

echo "$HEADERS" | grep -qi "^Via:" \
  && echo "  ⚠️  Header Via présent (révèle proxy)" \
  || echo "  ✅ Pas de Via"

echo "$HEADERS" | grep -qi "^X-Request-Id:\|^X-Forwarded-For:\|^X-Real-IP:" \
  && echo "  ⚠️  Header de debug/proxy exposé" \
  || echo "  ✅ Pas de header de debug"
```

### Pour `ports` ou phase 5 de `all` :

Scanner la surface d'attaque publique :

```bash
echo "=== SURFACE D'ATTAQUE — PORTS PUBLICS ==="

echo "  Redirector Fly.io ($REDIR_IP) :"
for port in 80 443 1194 4444 8080 55553 8443; do
  nc -zv -w2 37.16.12.4 $port 2>&1 | grep -q "succeeded" \
    && { [ $port -eq 80 ] || [ $port -eq 443 ] \
         && echo "    ✅ $port ouvert (attendu)" \
         || echo "    ❌ $port ouvert (inattendu !)"; } \
    || echo "    ✅ $port fermé"
done

echo ""
echo "  VPN Hub bojemoi.me :"
for port in 80 443 1194 4444 8080 3000 55553; do
  nc -zv -w2 bojemoi.me $port 2>&1 | grep -q "succeeded" \
    && { [ $port -eq 80 ] || [ $port -eq 443 ] || [ $port -eq 1194 ] \
         && echo "    ✅ $port ouvert (attendu)" \
         || echo "    ❌ $port ouvert (inattendu !)"; } \
    || echo "    ✅ $port fermé"
done
```

### Pour `tls` ou phase 6 de `all` :

Vérifier les certificats TLS pour détecter un fingerprinting suspect :

```bash
echo "=== TLS — FINGERPRINTING CERTIFICATS ==="

for target in "37.16.12.4:443" "bojemoi.me:443"; do
  host=$(echo $target | cut -d: -f1)
  port=$(echo $target | cut -d: -f2)
  echo "  $target :"
  CERT=$(echo | openssl s_client -connect $target -servername $host 2>/dev/null | openssl x509 -noout -subject -issuer -dates 2>/dev/null)
  if [ -n "$CERT" ]; then
    echo "$CERT" | while read line; do echo "    $line"; done
    echo "$CERT" | grep -qi "Let's Encrypt\|ZeroSSL\|Buypass" \
      && echo "    ✅ CA publique légitime" \
      || { echo "$CERT" | grep -qi "self.signed\|localhost\|Unknown" \
           && echo "    ❌ Self-signed ou suspect !" \
           || echo "    ⚠️  CA non reconnue — vérifier"; }
  else
    echo "    ❌ Pas de TLS ou timeout"
  fi
  echo ""
done
```

### Pour `dns` ou phase 7 de `all` :

Vérifier l'empreinte DNS : PTR inverse, Certificate Transparency (crt.sh), WHOIS privacy :

```bash
echo "=== DNS — EMPREINTE DOMAINE ==="

REDIR_IP="37.16.12.4"

echo "--- PTR (DNS inverse) ---"
echo -n "  $REDIR_IP PTR : "
PTR=$(dig -x $REDIR_IP +short 2>/dev/null | head -1)
[ -n "$PTR" ] && echo "$PTR (attendu: Fly.io infra)" || echo "(aucun enregistrement)"

echo -n "  bojemoi.me A   : "
dig A bojemoi.me +short 2>/dev/null

echo ""
echo "--- Certificate Transparency (crt.sh) ---"
echo "  Certs CT pour *.bojemoi.me :"
curl -4 -s --max-time 15 "https://crt.sh/?q=%.bojemoi.me&output=json" 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    seen = {}
    for c in data:
        name = c.get('name_value','').replace('\n', ' | ')
        date = c.get('not_after','?')[:10]
        issuer = c.get('issuer_ca_id','?')
        key = name
        if key not in seen:
            seen[key] = (date, issuer)
    for name, (date, ca) in sorted(seen.items(), key=lambda x: x[1][0], reverse=True)[:10]:
        marker = '⚠️ ' if 'bojemoi' in name.lower() and 'fly' not in name.lower() and 'gitea' not in name.lower() else '  '
        print(f'{marker} {date} : {name}')
    print(f'  Total : {len(seen)} SAN(s) dans CT logs')
    print('  ⚠️  Vérifier que aucun cert ne relie C2 et infra labo' if len(seen) > 0 else '')
except Exception as e:
    print(f'  ❌ crt.sh non joignable ({e})')
" 2>/dev/null || echo "  ❌ crt.sh timeout"

echo ""
echo "--- WHOIS privacy ---"
echo "  bojemoi.me :"
whois bojemoi.me 2>/dev/null | grep -iE "registrant|privacy|redacted|protect|organi|email|name" \
  | grep -v "^%" | head -5 | while read l; do echo "    $l"; done \
  || echo "    (whois indisponible)"
```

### Pour `segmentation` ou phase 8 de `all` :

Tester le pivot latéral depuis un conteneur Swarm compromis (borodino/ak47 sur réseau backend) :

```bash
echo "=== SEGMENTATION — PIVOT LATÉRAL DEPUIS SWARM ==="

AK47_NODE=$(docker service ps borodino_ak47-service --filter desired-state=running --format "{{.Node}}" 2>/dev/null | head -1)
AK47_NODE_IP=$(docker node inspect "$AK47_NODE" --format '{{.Status.Addr}}' 2>/dev/null)

if [ -z "$AK47_NODE_IP" ]; then
    echo "  ❌ Container ak47 non trouvé"
else
    echo "  Test depuis borodino_ak47 (réseaux: backend + scan_net) :"
    ssh -p 4422 -i /home/docker/.ssh/meta76_ed25519 -o StrictHostKeyChecking=no docker@"$AK47_NODE_IP" "
CNAME=\$(docker ps --format '{{.Names}}' | grep ak47 | head -1)
echo '  Container: '\$CNAME
# Services qui ne devraient PAS être joignables depuis borodino
for target in 'grafana:3000' 'gitea:3000' 'traefik:8080' 'prometheus:9090' 'alertmanager:9093'; do
  host=\$(echo \$target | cut -d: -f1)
  port=\$(echo \$target | cut -d: -f2)
  docker exec \$CNAME nc -z -w2 \$host \$port 2>/dev/null \
    && echo '  ❌ '\$target' joignable ! (pivot possible)' \
    || echo '  ✅ '\$target' non joignable'
done
# Services qui DOIVENT être joignables (attendus)
echo '  --- Services attendus ---'
for target in 'postgres:5432' 'redis:6379' 'faraday:5985'; do
  host=\$(echo \$target | cut -d: -f1)
  port=\$(echo \$target | cut -d: -f2)
  docker exec \$CNAME nc -z -w2 \$host \$port 2>/dev/null \
    && echo '  ✅ '\$target' joignable (attendu)' \
    || echo '  ⚠️  '\$target' non joignable (dépendance KO)'
done
" 2>/dev/null
fi

echo ""
echo "  Réseaux overlay de borodino_ak47 :"
docker service inspect borodino_ak47-service \
  --format '{{range .Spec.TaskTemplate.Networks}}  • {{.Target}}{{"\n"}}{{end}}' 2>/dev/null
```

### Pour `iptables` ou phase 9 de `all` :

Vérifier les règles FORWARD et DOCKER-USER sur les nœuds Swarm :

```bash
echo "=== IPTABLES — RÈGLES PARE-FEU NŒUDS SWARM ==="

_check_node_iptables() {
    local node=$1
    local node_ip=$2
    local cmd

    if [ "$node" = "meta-76" ]; then
        cmd="iptables -L DOCKER-USER -n 2>/dev/null | head -8; echo '---'; iptables -L FORWARD -n --line-numbers 2>/dev/null | head -6"
        eval "$cmd" 2>/dev/null | while read l; do echo "    $l"; done
    else
        ssh -p 4422 -i /home/docker/.ssh/meta76_ed25519 -o StrictHostKeyChecking=no docker@"$node_ip" \
            "iptables -L DOCKER-USER -n 2>/dev/null | head -8; echo '---'; iptables -L FORWARD -n --line-numbers 2>/dev/null | head -6" 2>/dev/null \
            | while read l; do echo "    $l"; done
    fi
}

for node in meta-76 meta-68 meta-69 meta-70; do
    NODE_IP=$(docker node inspect "$node" --format '{{.Status.Addr}}' 2>/dev/null)
    [ -z "$NODE_IP" ] && continue
    echo ""
    echo "  $node ($NODE_IP) — DOCKER-USER + FORWARD :"
    _check_node_iptables "$node" "$NODE_IP"
done

echo ""
echo "  Analyse :"
echo "  ✅ attendu : DOCKER-USER avec DROP explicites inter-réseau"
echo "  ❌ risque  : DOCKER-USER vide = tous les conteneurs se voient"
```

### Pour `all` (défaut) : exécuter les 9 phases dans l'ordre.

## Output Format

Présenter les résultats en sections :
1. **Redirecteur** — Filtrage UA + isolation MSF
2. **VPN C2** — Tunnel tun0 + routing
3. **Exit IP Scan** — ProtonVPN confirmé / IP inattendue
4. **Headers** — Fuites d'infra interne
5. **Ports publics** — Surface d'attaque
6. **TLS** — Fingerprinting certificats
7. **DNS & empreinte** — PTR inverse, crt.sh CT logs, WHOIS privacy
8. **Segmentation** — Pivot latéral depuis container Swarm
9. **Iptables** — Règles FORWARD/DOCKER-USER sur nœuds

Conclure avec un **bilan OPSEC** : `✅ OK` / `⚠️ avertissements` / `❌ fuites détectées` avec priorités de correction.
