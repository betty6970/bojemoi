# Docker Swarm Operations

Manage Docker Swarm - deploy stacks, scale services, view logs, check status.

## Arguments

- `status` - Show cluster and service status
- `deploy <stack>` - Deploy a stack (e.g., `deploy base`)
- `scale <service> <replicas>` - Scale a service (e.g., `scale borodino_ak47-service 3`)
- `logs <service>` - View recent logs for a service
- `nodes` - Show node status across the cluster

## Instructions

### For `status`:
```bash
echo "=== Cluster Nodes ===" && docker node ls
echo -e "\n=== Services with Issues ===" && docker service ls --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}" | grep -E "0/|NAME"
echo -e "\n=== Recent Failed Tasks ===" && docker service ls -q | xargs -I {} docker service ps {} --filter "desired-state=shutdown" --format "{{.Name}}: {{.Error}}" 2>/dev/null | grep -v "^$" | head -10
```

### For `deploy <stack>`:
The stack file should be at `/opt/bojemoi/stack/*.yml`. Run:
```bash
docker stack deploy -c /opt/bojemoi/stack/<stack-file>.yml <stack-name> --prune
```

Common stacks:
- `base` → `01-service-hl.yml`
- `borodino` → `40-service-borodino.yml`

### For `scale <service> <replicas>`:
```bash
docker service scale <service>=<replicas>
```

### For `logs <service>`:
```bash
docker service logs <service> --tail 50 --timestamps
```

### For `nodes`:
```bash
docker node ls --format "table {{.Hostname}}\t{{.Status}}\t{{.Availability}}\t{{.ManagerStatus}}"
echo -e "\n=== Node Resources ==="
for node in $(docker node ls -q); do
  name=$(docker node inspect $node --format '{{.Description.Hostname}}')
  echo "$name:"
  docker node inspect $node --format '  CPUs: {{.Description.Resources.NanoCPUs}} | Memory: {{.Description.Resources.MemoryBytes}}'
done
```

### If no argument or `help`:
Show available commands:
- `/swarm status` - Cluster and service overview
- `/swarm deploy <stack>` - Deploy stack (base, borodino)
- `/swarm scale <service> <n>` - Scale service replicas
- `/swarm logs <service>` - View service logs
- `/swarm nodes` - Node status and resources

## Safety Notes

- Always confirm before scaling to 0 replicas
- Warn if deploying to production stacks
- Check for pending config changes before deploy
