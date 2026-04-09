# Service Topology & Dependency Check

Audits all Docker Swarm services: health, network relations, dependency graph, and live inter-service connectivity probes.

## Arguments

- (none) / `all` — Full report: inventory + networks + known deps + connectivity probes
- `services` — Service inventory only (replicas, node, image)
- `networks` — Network topology (which services share each overlay network)
- `deps` — Known dependency graph with live connectivity probes
- `secrets` — Secret/volume sharing between services

## Instructions

### For `services` or phase 1 of `all`:

```bash
echo "=== SERVICE INVENTORY ==="
docker service ls --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}" | sed 's|localhost:5000/||g'

echo -e "\n=== SERVICES WITH PROBLEMS ==="
docker service ls --format "{{.Name}} {{.Replicas}}" | while read name replicas; do
  desired=$(echo $replicas | cut -d'/' -f2)
  running=$(echo $replicas | cut -d'/' -f1)
  [ "$running" != "$desired" ] && echo "  ⚠️  $name: $replicas"
done
echo "  (none)" 2>/dev/null || true

echo -e "\n=== PLACEMENT (services per node) ==="
for node in meta-76 meta-68 meta-69 meta-70; do
  count=$(docker service ps $(docker service ls -q) 2>/dev/null | grep -c "$node" 2>/dev/null || echo 0)
  echo "  $node: $count tasks"
done
```

### For `networks` or phase 2 of `all`:

```bash
python3 << 'PYEOF'
import subprocess, json
from collections import defaultdict

svc_ids = subprocess.run(['docker','service','ls','-q'], capture_output=True, text=True).stdout.strip().split()
net_to_svcs = defaultdict(list)
svc_to_nets = {}

for sid in svc_ids:
    data = json.loads(subprocess.run(['docker','service','inspect', sid], capture_output=True, text=True).stdout)[0]
    name = data['Spec']['Name']
    nets = [n.get('Target','?') for n in data['Spec'].get('TaskTemplate',{}).get('Networks',[])]
    svc_to_nets[name] = nets
    for n in nets:
        net_to_svcs[n].append(name)

print("=== NETWORK TOPOLOGY ===")
for net, svcs in sorted(net_to_svcs.items()):
    print(f"\n🔗  {net}  ({len(svcs)} members)")
    for s in sorted(svcs):
        print(f"     • {s}")

print("\n=== ISOLATED SERVICES (no overlay network) ===")
isolated = [s for s,nets in svc_to_nets.items() if not nets]
if isolated:
    for s in sorted(isolated): print(f"  ⚠️  {s}")
else:
    print("  none")

print("\n=== SERVICES SHARING MULTIPLE NETWORKS (potential hubs) ===")
for s, nets in sorted(svc_to_nets.items()):
    if len(nets) >= 2:
        print(f"  {s}: {', '.join(nets)}")
PYEOF
```

### For `deps` or phase 3 of `all`:

Known dependency graph — probe each endpoint from a temporary container on the correct network:

```bash
# Probes via temporary alpine containers — DNS resolves correctly from within overlay networks
for net in backend pentest; do
  echo "--- Probing from $net ---"
  docker run --rm --network $net localhost:5000/alpine:latest sh -c "
    for target in postgres:5432 redis:6379 faraday:5985 zaproxy:8090 ollama:11434 loki:3100 grafana:3000 msf-teamserver:55553; do
      host=\$(echo \$target | cut -d: -f1)
      port=\$(echo \$target | cut -d: -f2)
      nc -z -w2 \$host \$port 2>/dev/null && echo '  ✅ '\$target || echo '  ❌ '\$target
    done
  " 2>/dev/null
done

echo ""
echo "=== KNOWN DEPENDENCY MAP ==="
echo "Consumer                               Provider              Network"
echo "──────────────────────────────────────────────────────────────────"
echo "  borodino_ak47/bm12/uzi/zap/nuclei → postgres:5432         backend"
echo "  borodino_ak47/bm12/nuclei/zap      → redis:6379            backend+pentest"
echo "  borodino_zap-scanner               → zaproxy:8090          pentest"
echo "  borodino_zap/nuclei-api/uzi        → faraday:5985          backend+pentest"
echo "  borodino_nuclei-api/nuclei         → ollama:11434          backend (nuclei-api on scan_net too)"
echo "  borodino_uzi                       → msf-teamserver:55553  pentest"
echo "  borodino_ak47/bm12                 → wg-gateway (VPN)      borodino_scan_net"
echo "  mcp_mcp-server                     → postgres+faraday      backend+pentest"
echo "  base_alertmanager                  → postfix/protonmail     mail"
echo "  base_alloy                         → loki:3100             backend"
```

### For `secrets`:

```bash
python3 << 'PYEOF'
import subprocess, json
from collections import defaultdict

svc_ids = subprocess.run(['docker','service','ls','-q'], capture_output=True, text=True).stdout.strip().split()
secret_to_svcs = defaultdict(list)
volume_to_svcs = defaultdict(list)

for sid in svc_ids:
    data = json.loads(subprocess.run(['docker','service','inspect', sid], capture_output=True, text=True).stdout)[0]
    name = data['Spec']['Name']
    for sec in data['Spec'].get('TaskTemplate',{}).get('ContainerSpec',{}).get('Secrets',[]):
        secret_to_svcs[sec.get('SecretName','?')].append(name)
    for mnt in data['Spec'].get('TaskTemplate',{}).get('ContainerSpec',{}).get('Mounts',[]):
        if mnt.get('Type') == 'volume':
            volume_to_svcs[mnt.get('Source','?')].append(name)

print("=== SECRETS (shared between services) ===")
for sec, svcs in sorted(secret_to_svcs.items()):
    marker = "🔑" if len(svcs) > 1 else "  "
    print(f"{marker} {sec} → {', '.join(sorted(svcs))}")

print("\n=== NAMED VOLUMES (shared between services) ===")
for vol, svcs in sorted(volume_to_svcs.items()):
    marker = "📦" if len(svcs) > 1 else "  "
    print(f"{marker} {vol} → {', '.join(sorted(svcs))}")
PYEOF
```

### For `all` (default): run all 4 phases in order.

## Output Format

Present results in sections:
1. **Service Health** — table with replicas, flag broken services
2. **Network Topology** — networks grouped with member services, highlight hubs (services on 2+ networks)
3. **Dependency Graph** — table: consumer → provider | host:port | ✅/❌
4. **Secrets & Volumes** — shared resources highlighted with 🔑/📦

Conclude with a **health summary**: number of services OK, dependencies unreachable, services with replica mismatches.
