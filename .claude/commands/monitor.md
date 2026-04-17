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

5. **Check eve.json size and deleted-but-open log files on all worker nodes:**
   For each worker node (meta-68, meta-69, meta-70), SSH in and check:
   - Actual eve.json file size on disk
   - Deleted-but-open file sizes held by suricata processes (the real disk hog)
   - Per-node disk usage
   ```bash
   for node in meta-68 meta-69 meta-70; do
     IP=$(docker node inspect $node --format '{{.Status.Addr}}' 2>/dev/null)
     [ -z "$IP" ] && continue
     ssh -p 4422 -i /home/docker/.ssh/meta76_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=5 docker@$IP "
       echo \"=== $node ($IP) ===\"
       # Disk usage
       df -h / | awk 'NR==2 {printf \"  Disk: %s used / %s total (%s)\n\", \$3, \$2, \$5}'
       # Actual eve.json on disk
       size=\$(find /var/lib/docker/volumes -name 'eve.json' 2>/dev/null | xargs -I{} du -sh {} 2>/dev/null | sort -rh | head -1)
       [ -n \"\$size\" ] && echo \"  eve.json on disk: \$size\" || echo \"  eve.json on disk: not found\"
       # Deleted-but-open files held by suricata PIDs
       docker run --rm --pid=host -v /proc:/proc alpine sh -c '
         total=0
         found=0
         for pid in \$(ls /proc | grep -E \"^[0-9]+\$\"); do
           comm=\$(cat /proc/\$pid/comm 2>/dev/null)
           case \"\$comm\" in Suricata-Main|suricata)
             for fd in /proc/\$pid/fd/*; do
               target=\$(readlink \"\$fd\" 2>/dev/null)
               case \"\$target\" in *deleted*)
                 pos=\$(awk \"/^pos:/{print \\\$2}\" /proc/\$pid/fdinfo/\$(basename \$fd) 2>/dev/null)
                 [ -n \"\$pos\" ] && total=\$((total + pos)) && found=1
                 fname=\$(basename \"\${target% (deleted)}\")
                 echo \"  [deleted-open] PID \$pid \$fname: \$(echo \$pos | awk \"{printf \\\"%.1f GB\\\", \\\$1/1073741824}\")\"
               ;; esac
             done
           ;; esac
         done
         [ \$found -eq 1 ] && echo \"  Total held by suricata: \$(echo \$total | awk \"{printf \\\"%.1f GB\\\", \\\$1/1073741824}\")\" || echo \"  No deleted-open suricata files\"
       ' 2>/dev/null
     " 2>/dev/null
   done
   ```

   **If any node shows >5GB in deleted-open files**, restart suricata on that node:
   ```bash
   docker service update --force suricata_suricata
   ```

6. **Present a summary** of the system health with any issues highlighted.

## Output Format

Provide a concise status report with:
- System load (1/5/15 min averages)
- Memory usage percentage
- Top CPU-consuming containers
- Active alerts (firing/pending)
- Any services with missing replicas
- Per-node disk usage + eve.json / deleted-open file sizes (warn if >5GB held)
