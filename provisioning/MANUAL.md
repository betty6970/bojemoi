# Orchestrator — User Manual

`base_orchestrator` is the Bojemoi Lab deployment API. It provisions XenServer VMs
and Docker Swarm services, manages cloud-init templates locally, and keeps an
immutable blockchain audit trail of every deployment.

---

## Contents

1. [Access](#access)
2. [Health check](#health-check)
3. [Deploy a VM](#deploy-a-vm)
4. [Deploy a container / Swarm service](#deploy-a-container--swarm-service)
5. [Rapid7 debug VM](#rapid7-debug-vm)
6. [VulnHub VMs](#vulnhub-vms)
7. [Hosts (host\_debug)](#hosts-host_debug)
8. [Cloud-init templates](#cloud-init-templates)
9. [Blockchain audit trail](#blockchain-audit-trail)
10. [Prometheus metrics](#prometheus-metrics)
11. [IP validation](#ip-validation)
12. [Ops — rebuild & redeploy](#ops--rebuild--redeploy)
13. [Ops — adding or updating templates](#ops--adding-or-updating-templates)

---

## Access

The API runs on port 8000 inside the container. There is no published port on the host — all external access goes through Traefik.

| Route | URL |
|-------|-----|
| Internal (LAN) | `https://provisioning.bojemoi.lab` |
| From manager host | `http://localhost:8000` (via `docker exec`) |

**From the manager host:**
```bash
CID=$(docker ps -qf name=base_orchestrator)

# One-liner HTTP call
docker exec "$CID" python3 -c "
import urllib.request, json
r = urllib.request.urlopen('http://localhost:8000/health', timeout=10)
print(json.dumps(json.loads(r.read()), indent=2))
"

# Or use curl inside the container
docker exec "$CID" curl -s http://localhost:8000/health | python3 -m json.tool
```

**Interactive API docs** (Swagger): `https://provisioning.bojemoi.lab/docs`

---

## Health check

```
GET /health
```

Returns the status of every dependent service.

```json
{
  "status": "healthy",
  "timestamp": "2026-04-24T12:00:00Z",
  "services": {
    "gitea":       "up",
    "xenserver":   "up",
    "docker_swarm":"up",
    "database":    "up",
    "ip2location": "up",
    "blockchain":  "up"
  }
}
```

`status` is `healthy` when all services are `up`, `degraded` otherwise.

> **Note:** `gitea` being `down` no longer affects VM deployments — templates are
> served locally since 2026-04-24. Gitea is health-checked for awareness only.

---

## Deploy a VM

```
POST /api/v1/vm/deploy
```

Clones a XenServer template, injects a rendered cloud-init config, and boots the VM.
On success, the VM UUID is registered in `host_debug` and a blockchain block is written.

### Request body

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | yes | — | VM name (`[a-zA-Z][a-zA-Z0-9_-]{0,62}`) |
| `template` | string | yes | — | Cloud-init template name (see [Templates](#cloud-init-templates)) |
| `os_type` | enum | yes | — | `alpine` \| `ubuntu` \| `debian` |
| `cpu` | int | no | `2` | vCPUs (1–32) |
| `memory` | int | no | `2048` | RAM in MB (512–131072) |
| `disk` | int | no | `20` | Disk in GB (10–2048) |
| `network` | string | no | `default` | XenServer network name |
| `environment` | enum | no | `production` | `production` \| `staging` \| `dev` |
| `variables` | object | no | `null` | Extra Jinja2 variables injected into the template |

### XenServer template mapping

| `os_type` | XenServer template used |
|-----------|------------------------|
| `alpine` | `alpine-meta` |
| `ubuntu` | `ubuntu cloud` |
| `ubuntu-20` | `Ubuntu Focal Fossa 20.04` |
| `ubuntu-22` | `Ubuntu Jammy Jellyfish 22.04` |
| `ubuntu-24` | `ubuntu 24.x` |
| `debian` | `Debian Bullseye 11` |
| `debian-12` | `Debian Bookworm 12` |

### Example

```bash
curl -s -X POST https://provisioning.bojemoi.lab/api/v1/vm/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "name": "web-prod-01",
    "template": "webserver",
    "os_type": "alpine",
    "cpu": 4,
    "memory": 4096,
    "disk": 20,
    "environment": "production",
    "variables": {"app_port": 8080}
  }'
```

```json
{
  "success": true,
  "deployment_id": 42,
  "resource_id": "vm-uuid-abc123",
  "message": "VM web-prod-01 deployed successfully (block #17)"
}
```

### What happens internally

1. Cloud-init template read from `/app/cloud-init/{os_type}/{template}.yaml`
2. Jinja2 rendering with `vm_name`, `hostname`, `fqdn`, `environment` + any `variables`
3. Rendered YAML validated
4. VM cloned from XenServer template and started
5. `host_debug` row inserted (used by `bm12`/`uzi` for scanning)
6. Blockchain block written

---

## Deploy a container / Swarm service

```
POST /api/v1/container/deploy
```

Creates a Docker Swarm service via the docker-socket-proxy.

### Request body

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | yes | — | Service name |
| `image` | string | yes | — | Docker image (`registry/image:tag` or `image:tag@sha256:...`) |
| `replicas` | int | no | `1` | Replica count (1–100) |
| `environment` | object | no | `{}` | Environment variables |
| `ports` | array | no | `[]` | Port mappings, e.g. `["80:80", "443:443/tcp"]` |
| `networks` | array | no | `["backend"]` | Overlay networks to attach |
| `labels` | object | no | `null` | Service labels |

### Example

```bash
curl -s -X POST https://provisioning.bojemoi.lab/api/v1/container/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nginx-proxy",
    "image": "localhost:5000/nginx:latest",
    "replicas": 2,
    "environment": {"NGINX_HOST": "lab.local"},
    "networks": ["backend", "proxy"]
  }'
```

---

## Rapid7 debug VM

These endpoints manage a **single** dedicated debug VM (Metasploitable / Rapid7).
Its IP is stored as the sole entry in `host_debug`, which makes `bm12` and `uzi`
target it when they run in `DEBUG_MODE=1`.

### Deploy

```
POST /api/v1/vm/rapid7
```

Clones a XenServer template (no cloud-init), waits for the guest IP via XenTools,
then writes it to `host_debug`.

| Field | Default | Description |
|-------|---------|-------------|
| `vm_name` | `rapid7-test` | VM name on XenServer |
| `xen_template` | `Metasploitable3` | Exact XenServer template name |
| `network` | `lab-internal` | Isolated XenServer network |
| `cpu` | `2` | vCPUs (1–8) |
| `memory_mb` | `2048` | RAM (512–8192 MB) |
| `disk_gb` | `40` | Disk (10–500 GB) |
| `ip_poll_timeout` | `120` | Seconds to wait for guest IP (10–300) |

If the IP is not detected within `ip_poll_timeout`, the VM is still created — use
`/api/v1/vm/rapid7/register` to register it manually.

### Register IP manually

```
POST /api/v1/vm/rapid7/register
```

```json
{"ip_address": "192.168.1.55", "vm_name": "rapid7-test"}
```

### Get status

```
GET /api/v1/vm/rapid7/status
```

Returns current `host_debug` row + XenServer power state.

---

## VulnHub VMs

Manage vulnerable VMs from the built-in catalogue. Each VM is cloned from a
pre-imported XenServer template, started, and its IP is added to `host_debug`
so `bm12`/`uzi` can target it (up to one per `address`).

### Built-in catalogue

| vm\_id | Name | Key vulns |
|--------|------|-----------|
| `metasploitable2` | Metasploitable 2 | vsftpd backdoor, ProFTPD, Tomcat, NFS |
| `metasploitable3-ubuntu` | Metasploitable 3 (Ubuntu) | Jenkins, Struts, ElasticSearch |
| `dvwa` | DVWA | SQLi, XSS, LFI, command injection |
| `dc-1` | DC: 1 | Drupalgeddon CVE-2018-7600 |
| `kioptrix-1` | Kioptrix Level 1 | Apache mod\_ssl, Samba 2.2 |
| `basic-pentesting-1` | Basic Pentesting 1 | WordPress, FTP anon, ProFTPD |
| `lampiao` | Lampião | Drupal 7 + dirty cow |
| `pwnlab-init` | PwnLab: init | PHP LFI → file upload → RCE |

### List catalogue

```
GET /api/v1/vm/vulnhub/catalog
```

### List active targets (host\_debug)

```
GET /api/v1/vm/vulnhub/targets
```

### Deploy

```
POST /api/v1/vm/vulnhub/{vm_id}
```

```json
{
  "network": "lab-internal",
  "ip_poll_timeout": 120
}
```

Optional overrides: `cpu_override`, `memory_mb_override`.

### Delete

```
DELETE /api/v1/vm/vulnhub/{vm_id}
```

Stops and deletes the XenServer VM, removes the `host_debug` entry.

> **Prerequisite**: the XenServer template must be pre-imported.
> Use `scripts/import_vulnhub_ova.sh` on the XenServer host.

---

## Hosts (host\_debug)

`host_debug` is the table in the `msf` PostgreSQL database that `bm12` and `uzi`
read when `DEBUG_MODE=1` to get their target IP(s).

### List all hosts

```
GET /api/v1/hosts?limit=50
```

### Delete a host

```
DELETE /api/v1/hosts/{address}
```

Example: `DELETE /api/v1/hosts/192.168.1.55`

---

## Cloud-init templates

Templates live on the manager at `/opt/bojemoi/provisioning/cloud-init/` and are
mounted read-only into the container at `/app/cloud-init`. **No Gitea connection
is required at runtime.**

### Current templates

```
alpine/    database, minimal, webserver
ubuntu/    database, default, webserver
debian/    default, webserver
common/    hardening.sh, setup_docker.sh, setup_monitoring.sh
```

### List templates

```
GET /api/v1/templates
GET /api/v1/templates?os_type=alpine
```

### Get a template

```
GET /api/v1/templates/{os_type}/{template_name}
```

Example: `GET /api/v1/templates/alpine/minimal`

### List common scripts

```
GET /api/v1/templates/scripts
```

### Get a common script

```
GET /api/v1/templates/scripts/{script_name}
```

Example: `GET /api/v1/templates/scripts/hardening`

### Clear cache (no-op)

```
POST /api/v1/templates/cache/clear
```

Kept for API compatibility. Local templates have no in-memory cache.

---

## Blockchain audit trail

Every deployment (success or failure) writes an immutable block.
Each block's SHA-256 hash is chained to the previous one.

### List blocks

```
GET /api/v1/blockchain/blocks?deployment_type=vm&status_filter=success&limit=50&offset=0
```

Filters:
- `deployment_type`: `vm` or `container`
- `status_filter`: `success`, `failed`, `pending`, `running`

### Get a specific block

```
GET /api/v1/blockchain/blocks/{block_number}
```

### Latest block

```
GET /api/v1/blockchain/latest
```

### Verify chain integrity

```
GET /api/v1/blockchain/verify
```

Recomputes all hashes and checks the chain is unbroken.

```json
{
  "valid": true,
  "blocks_checked": 42,
  "message": "Chain integrity verified"
}
```

### Statistics

```
GET /api/v1/blockchain/stats
```

```json
{
  "total_blocks": 42,
  "deployments_by_type": {"vm": 30, "container": 12},
  "deployments_by_status": {"success": 38, "failed": 4},
  "chain_continuous": true
}
```

### Deployment history for a name

```
GET /api/v1/blockchain/history/{name}
```

Example: `GET /api/v1/blockchain/history/web-prod-01`

---

## Prometheus metrics

```
GET /metrics
```

Returns standard Prometheus text format. Scraped automatically by Prometheus
(configured via `prometheus_config_v4` Docker config).

Metrics exposed:
- `bojemoi_deployments_total{type, status, environment}` — counter
- `bojemoi_deployment_errors_total{type, error_type}` — counter
- `bojemoi_deployment_duration_seconds{type, environment}` — histogram
- `bojemoi_service_health{service}` — gauge (1 = up, 0 = down)
- `bojemoi_blockchain_blocks_total` — gauge
- `bojemoi_blockchain_chain_valid` — gauge
- Standard HTTP request metrics via `MetricsMiddleware`

---

## IP validation

Requests are filtered by country based on the source IP.

**Allowed countries** (default): `FR`, `DE`, `CH`, `BE`, `LU`, `NL`, `AT`

Requests from outside these countries receive `403 Forbidden`.

Controlled by `IP_VALIDATION_ENABLED` in the `.env` config (`provisioning_env_v5`
Docker config). Set to `false` to disable during local testing.

---

## Ops — rebuild & redeploy

Use `docker service update` (not full stack redeploy) to avoid disrupting
postgres, grafana, etc.

```bash
cd /opt/bojemoi

# 1. Build
docker build -f provisioning/Dockerfile.provisioning \
  -t localhost:5000/provisioning:latest provisioning/

# 2. Push
docker push localhost:5000/provisioning:latest

# 3. Get the new digest
DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' \
  localhost:5000/provisioning:latest | cut -d@ -f2)

# 4. Update service
docker service update \
  --image localhost:5000/provisioning:latest@${DIGEST} \
  --force \
  base_orchestrator

# 5. Verify
docker service ps base_orchestrator
```

Full stack redeploy (only if stack YAML changed):

```bash
POSTGRES_PASSWORD=$(docker service inspect base_postgres \
  --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{.}}{{"\n"}}{{end}}' \
  | grep POSTGRES_PASSWORD | cut -d= -f2)

docker stack deploy -c stack/01-service-hl.yml base --prune --resolve-image always
```

---

## Ops — adding or updating templates

Templates are stored on the manager at `/opt/bojemoi/provisioning/cloud-init/`
and mounted read-only into the container. **The container does not need to be
restarted** — file changes are visible immediately (bind-mount, not a copy).

### Sync from Gitea (Gitea accessible)

```bash
GIT_SSH_COMMAND="ssh -i /home/docker/.ssh/gitea_key_new -p 2222 -o StrictHostKeyChecking=no" \
  git clone ssh://git@bojemoi.me:2222/bojemoi/bojemoi-configs.git /tmp/bojemoi-configs

cp -r /tmp/bojemoi-configs/cloud-init/* /opt/bojemoi/provisioning/cloud-init/
rm -rf /tmp/bojemoi-configs
```

### Edit directly (Gitea down)

```bash
# Edit in place — change is live immediately
vi /opt/bojemoi/provisioning/cloud-init/alpine/minimal.yaml

# Verify the API sees it
curl -s https://provisioning.bojemoi.lab/api/v1/templates | python3 -m json.tool
```

### Add a new OS type

```bash
mkdir -p /opt/bojemoi/provisioning/cloud-init/rocky
cat > /opt/bojemoi/provisioning/cloud-init/rocky/base.yaml <<'EOF'
#cloud-config
hostname: {{ hostname }}
fqdn: {{ fqdn }}
EOF
```

The new OS type appears immediately in `GET /api/v1/templates`.

### Template variables

Every template is rendered with Jinja2. Built-in variables:

| Variable | Value |
|----------|-------|
| `vm_name` | VM name from the deploy request |
| `hostname` | Same as `vm_name` |
| `fqdn` | `{vm_name}.bojemoi.local` |
| `environment` | `production` \| `staging` \| `dev` |

Additional variables are passed via the `variables` field of the deploy request
and merged on top.

**Example template snippet:**
```yaml
#cloud-config
hostname: {{ hostname }}
fqdn: {{ fqdn }}

runcmd:
  - echo "Deployed by orchestrator — env={{ environment }}" > /etc/motd
  {% if app_port is defined %}
  - echo "APP_PORT={{ app_port }}" >> /etc/environment
  {% endif %}
```
