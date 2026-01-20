# GitLab Setup for bojemoi.lab.local

Complete GitLab CE deployment for Docker Swarm with integrated CI/CD, container registry, and monitoring.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Traefik (Reverse Proxy)               │
│  gitlab.bojemoi.lab.local | registry.bojemoi.lab.local      │
└─────────────────┬───────────────────────┬───────────────────┘
                  │                       │
        ┌─────────▼─────────┐   ┌────────▼─────────┐
        │   GitLab CE       │   │  Container        │
        │   (Web + API)     │   │  Registry         │
        │                   │   │                   │
        │  - Git repos      │   │  - Docker images  │
        │  - CI/CD engine   │   │  - Layer cache    │
        │  - Issue tracking │   └───────────────────┘
        │  - Wiki           │
        └─────────┬─────────┘
                  │
        ┌─────────▼─────────┐
        │  GitLab Runner    │
        │                   │
        │  - Build jobs     │
        │  - Deploy to      │
        │    Docker Swarm   │
        │  - Run pentests   │
        └───────────────────┘
```

## Features

### Core Capabilities
- **Source Control**: Full Git repository hosting
- **Container Registry**: Private Docker registry at registry.bojemoi.lab.local
- **CI/CD Pipelines**: Automated build, test, and deployment
- **Issue Tracking**: Integrated project management
- **Wiki**: Documentation hosting

### Integration Points
- **Docker Swarm**: Direct service deployment
- **Traefik**: Automatic reverse proxy and TLS
- **Faraday**: Pentest results management
- **Grafana**: Dashboard provisioning
- **Prometheus**: Alert rule deployment
- **Monitoring Stack**: Metrics collection from CI/CD

## Quick Start

### 1. Initial Deployment

```bash
# Update NFS server addresses in gitlab-stack.yml
vim gitlab-stack.yml  # Update YOUR_NFS_SERVER placeholders

# Make deployment script executable
chmod +x deploy-gitlab.sh

# Deploy the stack
./deploy-gitlab.sh
```

### 2. First Login

```bash
# The deployment script will display the initial root password
# Or retrieve it manually:
docker exec $(docker ps -qf "name=gitlab_gitlab") \
  cat /etc/gitlab/initial_root_password
```

Access GitLab at: https://gitlab.bojemoi.lab.local
- Username: `root`
- Password: (from above command)

**Important**: Change the root password immediately and save the new password securely.

### 3. Register GitLab Runner

```bash
# Get registration token from GitLab UI:
# Admin Area → CI/CD → Runners → Register an instance runner

# Register the runner
docker exec -it $(docker ps -qf "name=gitlab_gitlab-runner") \
  gitlab-runner register \
  --non-interactive \
  --url "https://gitlab.bojemoi.lab.local" \
  --registration-token "YOUR_TOKEN" \
  --executor "docker" \
  --docker-image "alpine:latest" \
  --description "swarm-runner" \
  --tag-list "docker,swarm" \
  --docker-privileged \
  --docker-volumes /var/run/docker.sock:/var/run/docker.sock \
  --docker-network-mode "gitlab_gitlab_internal"
```

### 4. Configure DNS

Add to your dnsmasq configuration (`/etc/dnsmasq.d/lab.conf`):

```
address=/gitlab.bojemoi.lab.local/YOUR_SWARM_IP
address=/registry.bojemoi.lab.local/YOUR_SWARM_IP
```

Restart dnsmasq:
```bash
systemctl restart dnsmasq
```

### 5. Docker Registry Authentication

Create a Personal Access Token in GitLab:
1. User Settings → Access Tokens
2. Name: `docker-registry`
3. Scopes: `read_registry`, `write_registry`
4. Create token

Login to registry:
```bash
docker login registry.bojemoi.lab.local
# Username: your_gitlab_username
# Password: your_personal_access_token
```

## Project Setup Examples

### Example 1: Pentest Orchestrator Project

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - deploy

build:
  stage: build
  tags:
    - docker
  script:
    - docker build -t registry.bojemoi.lab.local/pentest/orchestrator:$CI_COMMIT_SHORT_SHA .
    - docker push registry.bojemoi.lab.local/pentest/orchestrator:$CI_COMMIT_SHORT_SHA

deploy:
  stage: deploy
  tags:
    - swarm
  script:
    - docker service update --image registry.bojemoi.lab.local/pentest/orchestrator:$CI_COMMIT_SHORT_SHA pentest_orchestrator
  only:
    - main
```

### Example 2: Monitoring Configuration Project

```yaml
# .gitlab-ci.yml for Grafana dashboards
stages:
  - validate
  - deploy

validate:dashboards:
  stage: validate
  script:
    - python scripts/validate_dashboards.py dashboards/*.json

deploy:grafana:
  stage: deploy
  script:
    - docker run --rm -v grafana_dashboards:/dashboards alpine sh -c "cp dashboards/*.json /dashboards/"
    - docker service update --force monitoring_grafana
  only:
    - main
```

### Example 3: Docker Image Build Project

```yaml
# .gitlab-ci.yml for custom tool images
build:zap:
  stage: build
  script:
    - cd tools/zap
    - docker build -t registry.bojemoi.lab.local/pentest/zap-custom:latest .
    - docker push registry.bojemoi.lab.local/pentest/zap-custom:latest

build:metasploit:
  stage: build
  script:
    - cd tools/metasploit
    - docker build -t registry.bojemoi.lab.local/pentest/msf-custom:latest .
    - docker push registry.bojemoi.lab.local/pentest/msf-custom:latest
```

## Integration with Existing Infrastructure

### Faraday Integration

```yaml
# Pipeline job to upload pentest results to Faraday
pentest:run-and-upload:
  stage: test
  script:
    - docker run --rm 
        -e FARADAY_URL=http://faraday.bojemoi.lab.local 
        -e FARADAY_TOKEN=$FARADAY_API_TOKEN 
        registry.bojemoi.lab.local/pentest/orchestrator:latest 
        python run_scan.py --target $TARGET --upload-to-faraday
  only:
    - schedules
```

### Prometheus Metrics

GitLab exposes metrics at `/-/metrics` endpoint. Add to your Prometheus config:

```yaml
# Add to prometheus.yml
scrape_configs:
  - job_name: 'gitlab'
    static_configs:
      - targets: ['gitlab.bojemoi.lab.local']
    metrics_path: '/-/metrics'
```

### Grafana Dashboards

GitLab provides official Grafana dashboards:
- GitLab Omnibus: Dashboard ID 3805
- GitLab CI: Dashboard ID 11930

Import via: Grafana UI → Dashboards → Import

## Maintenance

### Daily Operations

```bash
# Check service status
docker stack ps gitlab

# View logs
docker service logs -f gitlab_gitlab
docker service logs -f gitlab_gitlab-runner

# Monitor resources
docker stats $(docker ps -qf "name=gitlab")
```

### Backup

```bash
# Manual backup
./gitlab-maintenance.sh backup

# Automated backup (add to crontab)
0 2 * * * /path/to/gitlab-maintenance.sh backup
```

### Restore

```bash
# List available backups
docker exec $(docker ps -qf "name=gitlab_gitlab") ls -lh /var/opt/gitlab/backups/

# Restore from backup
./gitlab-maintenance.sh restore 1638360000_2024_11_26
```

### Health Check

```bash
./gitlab-maintenance.sh health
```

### Database Optimization

```bash
# Run monthly
./gitlab-maintenance.sh optimize
```

## Security Considerations

### Registry Access Control

1. Enable two-factor authentication for all users
2. Use deploy tokens for CI/CD pipelines (not personal tokens)
3. Configure registry cleanup policies to remove old images

### Runner Security

1. Limit runner tags to specific projects
2. Use separate runners for different security levels
3. Never use privileged mode unless absolutely necessary
4. Regularly update runner images

### Network Isolation

- GitLab and runner communicate via internal overlay network
- Registry accessible only through Traefik
- Pentest tools isolated in separate network segments

## Troubleshooting

### GitLab Won't Start

```bash
# Check logs
docker service logs gitlab_gitlab

# Common issues:
# 1. Insufficient memory (needs 4GB minimum)
# 2. PostgreSQL initialization timeout
# 3. NFS mount issues

# Force recreation
docker service update --force gitlab_gitlab
```

### Runner Not Executing Jobs

```bash
# Check runner logs
docker service logs gitlab_gitlab-runner

# Verify registration
docker exec $(docker ps -qf "name=gitlab_gitlab-runner") gitlab-runner verify

# Re-register if needed
docker exec -it $(docker ps -qf "name=gitlab_gitlab-runner") gitlab-runner register
```

### Registry Push Failures

```bash
# Verify authentication
docker login registry.bojemoi.lab.local

# Check registry logs in GitLab
docker exec $(docker ps -qf "name=gitlab_gitlab") tail -f /var/log/gitlab/registry/current

# Verify network connectivity
docker run --rm alpine ping -c 3 registry.bojemoi.lab.local
```

### Slow Performance

```bash
# Check resource usage
./gitlab-maintenance.sh disk

# Optimize database
./gitlab-maintenance.sh optimize

# Consider increasing resources in gitlab-stack.yml:
#   limits:
#     cpus: '6'
#     memory: 12G
```

## Advanced Configuration

### Enable LDAP Authentication

Edit `/etc/gitlab/gitlab.rb` in container:

```ruby
gitlab_rails['ldap_enabled'] = true
gitlab_rails['ldap_servers'] = YAML.load <<-EOS
  main:
    label: 'LDAP'
    host: 'ldap.bojemoi.lab.local'
    port: 389
    uid: 'uid'
    bind_dn: 'cn=admin,dc=bojemoi,dc=lab,dc=local'
    password: 'password'
    encryption: 'plain'
    base: 'ou=users,dc=bojemoi,dc=lab,dc=local'
EOS
```

### Email Notifications

```ruby
gitlab_rails['smtp_enable'] = true
gitlab_rails['smtp_address'] = "smtp.bojemoi.lab.local"
gitlab_rails['smtp_port'] = 587
gitlab_rails['smtp_domain'] = "bojemoi.lab.local"
gitlab_rails['smtp_authentication'] = "login"
gitlab_rails['smtp_enable_starttls_auto'] = true
gitlab_rails['smtp_user_name'] = "gitlab@bojemoi.lab.local"
gitlab_rails['smtp_password'] = "password"
```

### Object Storage for Large Files

For artifacts and LFS, configure S3-compatible storage (MinIO, etc.):

```ruby
gitlab_rails['object_store']['enabled'] = true
gitlab_rails['object_store']['connection'] = {
  'provider' => 'AWS',
  'region' => 'us-east-1',
  'aws_access_key_id' => 'ACCESS_KEY',
  'aws_secret_access_key' => 'SECRET_KEY',
  'endpoint' => 'http://minio.bojemoi.lab.local:9000',
  'path_style' => true
}
```

## Resource Requirements

### Minimum Requirements
- CPU: 2 cores
- RAM: 4GB
- Storage: 50GB

### Recommended for Production
- CPU: 4 cores
- RAM: 8GB
- Storage: 100GB+ (depends on repository size)

### Storage Breakdown
- GitLab data: 20-50GB (varies with usage)
- Container registry: 10-100GB (depends on image count)
- Backups: 2x GitLab data size
- PostgreSQL: 5-10GB

## Related Documentation

- GitLab Official Docs: https://docs.gitlab.com
- Docker Swarm Docs: https://docs.docker.com/engine/swarm/
- Traefik Docs: https://doc.traefik.io/traefik/

## Support

For issues specific to this deployment:
1. Check logs: `docker service logs gitlab_gitlab`
2. Run health check: `./gitlab-maintenance.sh health`
3. Review GitLab status: https://gitlab.bojemoi.lab.local/admin/health_check

For GitLab bugs or features:
- GitLab Community Forum: https://forum.gitlab.com
- GitLab Issue Tracker: https://gitlab.com/gitlab-org/gitlab/-/issues
