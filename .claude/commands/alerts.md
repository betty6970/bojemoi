# Prometheus Alerts Management

Check, silence, and manage Prometheus/Alertmanager alerts.

## Arguments

- `list` or no args - List all active alerts
- `rules` - List all configured alert rules
- `cpu` - Show CPU-related alerts and current values
- `silence <alertname> <duration>` - Silence an alert (e.g., `silence HostHighCPU 2h`)
- `test` - Send a test alert to verify email notifications

## Instructions

### For `list` or no argument:
```bash
docker exec $(docker ps -q -f name=prometheus | head -1) sh -c 'cd /tmp && wget -q http://127.0.0.1:9090/api/v1/alerts -O alerts.json' 2>/dev/null
docker cp $(docker ps -q -f name=prometheus | head -1):/tmp/alerts.json /tmp/prom_alerts.json 2>/dev/null
python3 -c "
import json
with open('/tmp/prom_alerts.json') as f:
    d=json.load(f)
alerts = d.get('data',{}).get('alerts',[])
firing = [a for a in alerts if a.get('state')=='firing']
pending = [a for a in alerts if a.get('state')=='pending']
inactive_count = len([a for a in alerts if a.get('state')=='inactive'])
print(f'FIRING: {len(firing)} | PENDING: {len(pending)} | INACTIVE: {inactive_count}')
print()
if firing:
    print('=== FIRING ALERTS ===')
    for a in firing:
        print(f\"  [{a['labels'].get('severity','?')}] {a['labels']['alertname']}\")
        print(f\"      {a['annotations'].get('summary','')}\")
if pending:
    print('\\n=== PENDING ALERTS ===')
    for a in pending:
        print(f\"  {a['labels']['alertname']} - {a['annotations'].get('summary','')}\")
if not firing and not pending:
    print('No active alerts.')
"
```

### For `rules`:
```bash
docker exec $(docker ps -q -f name=prometheus | head -1) sh -c 'cd /tmp && wget -q http://127.0.0.1:9090/api/v1/rules -O rules.json' 2>/dev/null
docker cp $(docker ps -q -f name=prometheus | head -1):/tmp/rules.json /tmp/prom_rules.json 2>/dev/null
python3 -c "
import json
with open('/tmp/prom_rules.json') as f:
    d=json.load(f)
groups = d.get('data',{}).get('groups',[])
print(f'Total rule groups: {len(groups)}')
for g in groups:
    alerts = [r for r in g.get('rules',[]) if r.get('type')=='alerting']
    if alerts:
        print(f\"\\n[{g.get('name')}] - {len(alerts)} alerts\")
        for r in alerts[:5]:
            state = r.get('state','?')
            icon = '🔴' if state=='firing' else '🟡' if state=='pending' else '⚪'
            print(f\"  {icon} {r.get('name')}\")
        if len(alerts) > 5:
            print(f\"  ... and {len(alerts)-5} more\")
"
```

### For `cpu`:
```bash
echo "=== Current CPU Usage ==="
docker exec $(docker ps -q -f name=prometheus | head -1) sh -c 'cd /tmp && wget -q "http://127.0.0.1:9090/api/v1/query?query=100%20-%20(avg%20by(instance)%20(rate(node_cpu_seconds_total{mode=%22idle%22}[5m]))%20*%20100)" -O cpu.json' 2>/dev/null
docker cp $(docker ps -q -f name=prometheus | head -1):/tmp/cpu.json /tmp/cpu.json 2>/dev/null
python3 -c "
import json
with open('/tmp/cpu.json') as f:
    d=json.load(f)
results = d.get('data',{}).get('result',[])
for r in results:
    instance = r['metric'].get('instance','?')
    value = float(r['value'][1])
    bar = '█' * int(value/5) + '░' * (20-int(value/5))
    status = '⚠️' if value > 85 else '🔴' if value > 95 else '✓'
    print(f\"{status} {instance}: {value:.1f}% [{bar}]\")
"
echo -e "\n=== CPU Alert Thresholds ==="
echo "  HostHighCPU:     > 85% for 10m → warning"
echo "  HostCriticalCPU: > 95% for 5m  → critical"
```

### For `silence`:
Provide instructions to silence via Alertmanager API or UI at https://alertmanager.bojemoi.lab

### For `test`:
```bash
# This will temporarily raise CPU to trigger an alert
echo "To test alerts, you can check current firing alerts in Alertmanager:"
echo "  URL: https://alertmanager.bojemoi.lab"
echo ""
echo "Or force a test notification via API (requires firing alert)"
```

## Output Format

Use visual indicators:
- 🔴 Firing/Critical
- 🟡 Pending/Warning
- ⚪ Inactive
- ✓ Healthy
