# Borodino C2 Stack Operations

Check and launch the borodino stack + C2 redirectors (VPN tunnel, msf-teamserver, workers, redirectors).

## Arguments

- `status` - Full status: VPN tunnel, msf-teamserver, workers (ak47/bm12/uzi), redirectors
- `start` - Start missing components (VPN client, borodino stack)
- `stop` - Stop borodino stack cleanly (waits for shutdown)
- `redirectors` - List known redirectors and check HTTP reachability
- `logs <service>` - Tail logs for a borodino service (e.g., `logs uzi-service`)

## Instructions

### For `status`:

```bash
echo "=== VPN Tunnel ==="
docker inspect lab-manager-vpn --format 'Container: {{.Name}} | State: {{.State.Status}}' 2>/dev/null || echo "lab-manager-vpn: NOT running"
ping -c 1 -W 2 10.8.0.1 >/dev/null 2>&1 && echo "VPN tunnel: UP (10.8.0.1 reachable)" || echo "VPN tunnel: DOWN"

echo -e "\n=== MSF Teamserver ==="
docker service ps borodino_msf-teamserver --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}\t{{.Error}}" 2>/dev/null | head -5

echo -e "\n=== Borodino Workers ==="
docker service ls --filter name=borodino --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}" 2>/dev/null

echo -e "\n=== MSF Teamserver Logs (last 5) ==="
docker service logs --tail 5 borodino_msf-teamserver 2>&1 | grep -v "^$"

echo -e "\n=== Redirectors ==="
for f in /opt/bojemoi/volumes/c2-vpn/redirectors/*.json; do
  [ -f "$f" ] || { echo "No redirectors registered."; break; }
  name=$(basename "$f" .json)
  ip=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('ip','?'))" 2>/dev/null)
  provider=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('provider','?'))" 2>/dev/null)
  status=$(curl -4 -s -o /dev/null -w "%{http_code}" --max-time 5 "http://$ip/" 2>/dev/null)
  echo "  $name ($provider) — $ip — HTTP $status"
done
```

### For `start`:

1. Check and start VPN client if not running:
```bash
VPN_RUNNING=$(docker inspect lab-manager-vpn --format '{{.State.Status}}' 2>/dev/null)
if [ "$VPN_RUNNING" != "running" ]; then
  echo "[INFO] Starting lab-manager-vpn..."
  docker rm -f lab-manager-vpn 2>/dev/null || true
  docker run -d --name lab-manager-vpn \
    --privileged --network host --restart unless-stopped \
    -v /opt/bojemoi/volumes/c2-vpn/clients/lab-manager.ovpn:/etc/openvpn/client.ovpn:ro \
    --entrypoint sh kylemanna/openvpn \
    -c "mkdir -p /dev/net && mknod /dev/net/tun c 10 200 2>/dev/null || true && chmod 666 /dev/net/tun && openvpn --config /etc/openvpn/client.ovpn"
  sleep 5
else
  echo "[OK] lab-manager-vpn already running"
fi
```

2. Check VPN tunnel:
```bash
ping -c 2 -W 3 10.8.0.1 >/dev/null 2>&1 && echo "[OK] VPN tunnel UP" || echo "[WARN] VPN tunnel not responding yet"
```

3. Check and deploy borodino stack:
```bash
TEAMSERVER=$(docker service ls --filter name=borodino_msf-teamserver --format "{{.Replicas}}" 2>/dev/null)
if [ -z "$TEAMSERVER" ]; then
  echo "[INFO] Deploying borodino stack..."
  docker stack deploy -c /opt/bojemoi/stack/40-service-borodino.yml borodino --prune --resolve-image always
else
  echo "[OK] borodino stack running (msf-teamserver: $TEAMSERVER)"
fi
```

4. Show final status:
```bash
docker service ls --filter name=borodino --format "table {{.Name}}\t{{.Replicas}}" 2>/dev/null
```

### For `stop`:

**IMPORTANT: Create Alertmanager silence first.**
```bash
ALERTMANAGER_URL="http://alertmanager.bojemoi.lab:9093"
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")
END_TIME=$(date -u -d "+15 minutes" +"%Y-%m-%dT%H:%M:%S.000Z")
curl -s -X POST "${ALERTMANAGER_URL}/api/v2/silences" \
  -H "Content-Type: application/json" \
  -d "{\"matchers\":[{\"name\":\"alertname\",\"value\":\".*\",\"isRegex\":true,\"isEqual\":true}],\"startsAt\":\"${START_TIME}\",\"endsAt\":\"${END_TIME}\",\"createdBy\":\"claude-borodino\",\"comment\":\"borodino stack stop\"}" \
  >/dev/null
```

Stop borodino stack and wait for services to go down:
```bash
echo "[INFO] Removing borodino stack..."
docker stack rm borodino

echo "[INFO] Waiting for services to stop..."
i=0
while [ $i -lt 60 ]; do
  COUNT=$(docker service ls --filter name=borodino --format "{{.Name}}" 2>/dev/null | wc -l)
  [ "$COUNT" -eq 0 ] && echo "[OK] All borodino services stopped." && break
  echo "  Waiting... ($COUNT services remaining)"
  sleep 5
  i=$((i+5))
done
```

Note: VPN client (lab-manager-vpn) is kept running intentionally.

### For `redirectors`:

```bash
echo "=== Redirectors Registry ==="
COUNT=0
for f in /opt/bojemoi/volumes/c2-vpn/redirectors/*.json; do
  [ -f "$f" ] || continue
  COUNT=$((COUNT+1))
  name=$(basename "$f" .json)
  ip=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('ip','?'))")
  provider=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('provider','?'))")
  region=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('region','?'))")
  created=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('created','?'))")
  http_code=$(curl -4 -s -o /dev/null -w "%{http_code}" --max-time 5 "http://$ip/" 2>/dev/null || echo "ERR")
  https_code=$(curl -4 -sk -o /dev/null -w "%{http_code}" --max-time 5 "https://$ip/api/update" 2>/dev/null || echo "ERR")
  echo ""
  echo "  Name     : $name"
  echo "  IP       : $ip"
  echo "  Provider : $provider ($region)"
  echo "  Created  : $created"
  echo "  HTTP     : $http_code | HTTPS C2 path: $https_code"
done
[ $COUNT -eq 0 ] && echo "No redirectors registered in /opt/bojemoi/volumes/c2-vpn/redirectors/"

echo -e "\nC2_REDIRECTORS in stack:"
grep "C2_REDIRECTORS" /opt/bojemoi/stack/40-service-borodino.yml
```

### For `logs <service>`:

```bash
docker service logs borodino_<service> --tail 50 --timestamps 2>&1
```

Common services: `msf-teamserver`, `uzi-service`, `ak47-service`, `bm12-service`

### If no argument or `help`:

Show available commands:
- `/borodino status` — Full C2 stack health check
- `/borodino start` — Start VPN + borodino stack (idempotent)
- `/borodino stop` — Stop borodino stack cleanly
- `/borodino redirectors` — List redirectors + HTTP reachability check
- `/borodino logs <service>` — Tail service logs
