# Red Team OPSEC Check

Vérifie l'étanchéité de la plateforme C2 : redirecteurs, VPN, exit IP scan, headers, ports exposés, certificats.

## Arguments

- (none) / `all` — Audit complet (toutes les couches)
- `redirector` — Filtrage UA + isolation C2 sur Fly.io
- `vpn` — Tunnel OpenVPN C2 + routing
- `scan` — Exit IP via ProtonVPN (wg-gateway)
- `headers` — Headers serveur / fuite d'infra
- `ports` — Surface d'attaque publique
- `tls` — Fingerprinting certificats

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

echo "  IP de sortie via borodino_scan_net :"
docker run --rm --network borodino_scan_net \
  curlimages/curl:latest \
  curl -4 -s --max-time 10 https://ipinfo.io/json 2>/dev/null | python3 -c "
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
  if '149.102' in ip or 'Proton' in org or 'proton' in org.lower():
    print('  Résultat : ✅ ProtonVPN confirmé')
  else:
    print('  Résultat : ⚠️  IP inattendue — vérifier wg-gateway')
except:
  print('  ❌ Impossible de récupérer l IP (wg-gateway down ?)')
" 2>/dev/null || echo "  ❌ Réseau borodino_scan_net non joignable"

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

### Pour `all` (défaut) : exécuter les 6 phases dans l'ordre.

## Output Format

Présenter les résultats en sections :
1. **Redirecteur** — Filtrage UA + isolation MSF
2. **VPN C2** — Tunnel tun0 + routing
3. **Exit IP Scan** — ProtonVPN confirmé / IP inattendue
4. **Headers** — Fuites d'infra interne
5. **Ports publics** — Surface d'attaque
6. **TLS** — Fingerprinting certificats

Conclure avec un **bilan OPSEC** : `✅ OK` / `⚠️ avertissements` / `❌ fuites détectées` avec priorités de correction.
