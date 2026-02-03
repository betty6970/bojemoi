# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bojemoi Lab is an Infrastructure-as-Code project for managing a Docker Swarm-based lab environment with hybrid infrastructure support (VMs on XenServer + Docker containers). The project includes a Python-based orchestrator for unified deployment management.

## Build and Development Commands

### Docker Stack Operations
```bash
# Validate stack syntax
docker-compose -f stack/<stack-name>.yml config --quiet

# Deploy a stack
docker stack deploy -c stack/<stack-name>.yml <stack-name> --prune --resolve-image always

aa# View service logs
docker service logs -f <service-name>
```

### Orchestrator Development
```bash
cd provisioning
pip install -r requirements.txt

# Run the API server
uvicorn orchestrator.main:app --reload --host 0.0.0.0 --port 8000

# Or with Docker Compose
docker-compose up --build
```

### Orchestrator Makefile Commands
```bash
cd provisioning1
make install    # Install dependencies
make start      # Start services
make stop       # Stop services
make logs       # View logs
make health     # Health check
```

## Architecture

### Core Components

**Orchestrator API** (`provisioning1/orchestrator/`)
- FastAPI application at `main.py` (port 8000, exposed as 28080 in Swarm)
- PostgreSQL database with SQLAlchemy ORM for deployment tracking
- Background task processing with APScheduler
- Pydantic schemas for request validation

**Manager Clients** (`provisioning1/orchestrator/managers/`)
- `gitea_client.py` - Fetches configs from Gitea (GitOps config source)
- `vm_deployer.py` - XenServer VM deployment with cloud-init
- `container_deployer.py` - Docker container deployment
- `swarm_deployer.py` - Docker Swarm service deployment

**Docker Stacks** (`stack/`)
- 19 numbered stack files (00-70) for Docker Swarm services
- Includes: Traefik, Prometheus, Grafana, Loki, CrowdSec, Suricata, Faraday
- GitLab CI/CD pipeline at `stack/.gitlab-ci.yml`

### Key API Endpoints
```
POST /deploy/vm/{vm_name}              - Deploy VM to XenServer
POST /deploy/container/{container_name} - Deploy container
POST /deploy/service/{service_name}    - Deploy Swarm service
POST /deploy/all                       - Full infrastructure deployment
GET  /deployments                      - List all deployments
GET  /status                           - Connection health check
GET  /health                           - Liveness probe
```

### Deployment Workflow
1. Request to `/deploy/vm/{name}` triggers background task
2. Config fetched from Gitea (`vms/{name}.yaml`)
3. Cloud-init template fetched from Gitea (`cloud-init/{template}.yaml`)
4. XenServer API called to deploy
5. Database updated with deployment status
6. Prometheus metrics recorded

### Network Architecture
- Overlay networks: monitoring, backend, frontend, rsync_network, proxy, mail
- Internal Docker registry at localhost:5000
- Swarm manager: manager.bojemoi.lab.local

## Tech Stack

- **API**: Python 3.11, FastAPI, Uvicorn
- **Database**: PostgreSQL 15, SQLAlchemy 2.0
- **Async**: httpx, APScheduler
- **Docker**: docker-py 7.0, Docker Swarm
- **Config**: Pydantic BaseSettings, .env files
- **CLI**: Click + Rich
- **Monitoring**: Prometheus client
- **CI/CD**: GitLab CI with SSH deployments

## Configuration

Environment variables in `provisioning1/.env`:
- `POSTGRES_PASSWORD` - Database credentials
- `GITEA_URL`, `GITEA_TOKEN` - Gitea config source
- `XENSERVER_HOST`, `XENSERVER_USER`, `XENSERVER_PASSWORD` - VM deployment
- `DOCKER_HOST`, `DOCKER_SWARM_MANAGER` - Container deployment
- `CHECK_INTERVAL_MINUTES`, `ENABLE_SCHEDULER` - Background job settings

## Directory Structure

```
stack/              # Docker Swarm stack YAML files (main deployment configs)
provisioning1/      # Current orchestrator (FastAPI + PostgreSQL)
provisioning/       # Legacy orchestrator
scripts/            # Utility scripts (Python & Bash)
samsonov/           # Faraday security scanning
oblast/, oblast-1/  # OWASP ZAP scanning services
volumes/            # Persistent data (gitignored)
```
