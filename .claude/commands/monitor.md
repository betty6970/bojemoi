# Monitor System Status

Check the current system status including CPU, memory, alerts, and service health.

## Instructions

1. **Check system load and resources:**
   ```bash
   uptime && free -h
   ```

2. **Check Docker container resource usage (top 15 by CPU):**
   ```bash
   docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | sort -k2 -t'%' -rn | head -15
   ```

3. **Check active Prometheus alerts:**
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
   print(f'Firing: {len(firing)}, Pending: {len(pending)}')
   for a in firing:
       print(f'  [FIRING] {a[\"labels\"][\"alertname\"]}: {a[\"annotations\"].get(\"summary\",\"\")}')
   for a in pending:
       print(f'  [PENDING] {a[\"labels\"][\"alertname\"]}')
   "
   ```

4. **Check critical Docker Swarm services:**
   ```bash
   docker service ls --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}" | grep -E "0/|prometheus|alertmanager|grafana|loki"
   ```

5. **Present a summary** of the system health with any issues highlighted.

## Output Format

Provide a concise status report with:
- System load (1/5/15 min averages)
- Memory usage percentage
- Top CPU-consuming containers
- Active alerts (firing/pending)
- Any services with missing replicas
