# Architecture Détaillée - Deployment Orchestrator

## Vue d'Ensemble du Système

```
┌─────────────────────────────────────────────────────────────────┐
│                        BOJEMOI LAB                               │
│                                                                  │
│  ┌────────────────┐                                             │
│  │  AWS Lightsail │                                             │
│  │                │                                             │
│  │  ┌──────────┐  │                                             │
│  │  │  Gitea   │  │  HTTP Webhook                               │
│  │  │ Server   │──┼────────────────────┐                        │
│  │  └──────────┘  │                    │                        │
│  │                │                    │                        │
│  │  - Git Repos   │                    │                        │
│  │  - Webhooks    │                    │                        │
│  │  - API         │                    │                        │
│  └────────────────┘                    │                        │
│                                        │                        │
│                                        ▼                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │         Deployment Orchestrator Container               │   │
│  │                                                          │   │
│  │  ┌────────────────────────────────────────────────┐     │   │
│  │  │           FastAPI Application                   │     │   │
│  │  │                                                 │     │   │
│  │  │  ┌──────────────┐   ┌──────────────┐           │     │   │
│  │  │  │   Webhook    │   │   REST API   │           │     │   │
│  │  │  │   Endpoint   │   │   Endpoints  │           │     │   │
│  │  │  └──────┬───────┘   └──────┬───────┘           │     │   │
│  │  │         │                   │                   │     │   │
│  │  │         └───────────┬───────┘                   │     │   │
│  │  │                     │                           │     │   │
│  │  │         ┌───────────▼────────────┐              │     │   │
│  │  │         │  Orchestration Engine  │              │     │   │
│  │  │         │                        │              │     │   │
│  │  │         │  - Manifest Parser     │              │     │   │
│  │  │         │  - Deployment Logic    │              │     │   │
│  │  │         │  - State Management    │              │     │   │
│  │  │         └───────────┬────────────┘              │     │   │
│  │  │                     │                           │     │   │
│  │  │         ┌───────────┴────────────┐              │     │   │
│  │  │         │                        │              │     │   │
│  │  │    ┌────▼─────┐           ┌─────▼──────┐       │     │   │
│  │  │    │  Gitea   │           │  Database  │       │     │   │
│  │  │    │ Manager  │           │  Manager   │       │     │   │
│  │  │    └────┬─────┘           └─────┬──────┘       │     │   │
│  │  │         │                       │              │     │   │
│  │  └─────────┼───────────────────────┼──────────────┘     │   │
│  │            │                       │                    │   │
│  │       ┌────▼─────┐           ┌─────▼──────┐            │   │
│  │       │ XenServer│           │ Docker     │            │   │
│  │       │ Manager  │           │ Manager    │            │   │
│  │       └────┬─────┘           └─────┬──────┘            │   │
│  │            │                       │                    │   │
│  └────────────┼───────────────────────┼────────────────────┘   │
│               │                       │                        │
│      XML-RPC  │                       │  Docker Socket         │
│               │                       │                        │
│  ┌────────────▼──────────┐   ┌────────▼─────────────┐         │
│  │   XenServer Host      │   │  Docker/Swarm Nodes  │         │
│  │                       │   │                      │         │
│  │  ┌────────────────┐   │   │  ┌────────────────┐ │         │
│  │  │  VM Templates  │   │   │  │  Containers    │ │         │
│  │  ├────────────────┤   │   │  ├────────────────┤ │         │
│  │  │  Deployed VMs  │   │   │  │  Swarm Services│ │         │
│  │  │  - Production  │   │   │  │                │ │         │
│  │  │  - Staging     │   │   │  │  - Production  │ │         │
│  │  │  - Development │   │   │  │  - Staging     │ │         │
│  │  └────────────────┘   │   │  │  - Development │ │         │
│  │                       │   │  └────────────────┘ │         │
│  │  Cloud-init Bootstrap │   │                      │         │
│  └───────────────────────┘   └──────────────────────┘         │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              PostgreSQL Database                          │  │
│  │                                                           │  │
│  │  Tables:                                                  │  │
│  │  - deployments        (état des déploiements)            │  │
│  │  - deployment_logs    (logs détaillés)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         Monitoring & Observability                        │  │
│  │                                                           │  │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │  │
│  │  │  Prometheus  │   │   Grafana    │   │     Loki     │ │  │
│  │  │   Metrics    │   │  Dashboards  │   │     Logs     │ │  │
│  │  └──────────────┘   └──────────────┘   └──────────────┘ │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Flux de Déploiement Détaillé

### 1. Déclenchement via Git Push

```
Developer Machine
    │
    │ git push
    ▼
Gitea Server (Lightsail)
    │
    │ Webhook Event
    ▼
Orchestrator Container
```

### 2. Traitement du Webhook

```
┌─────────────────────────────────────────────────────┐
│  Webhook Handler (FastAPI)                          │
│                                                      │
│  1. Receive POST /webhook/gitea                     │
│  2. Verify HMAC-SHA256 signature                    │
│  3. Parse JSON payload                              │
│  4. Extract:                                         │
│     - Repository info                               │
│     - Branch name                                   │
│     - Commit SHA                                    │
│     - Changed files                                 │
│  5. Queue for processing                            │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  Gitea Manager                                      │
│                                                      │
│  1. Fetch changed files via API                     │
│  2. Detect deployment manifests                     │
│  3. Download manifest content                       │
│  4. Parse YAML → Pydantic models                    │
│  5. Update commit status (pending)                  │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  Orchestration Engine                               │
│                                                      │
│  1. Create deployment record in DB                  │
│  2. Determine deployment type:                      │
│     - VM                                            │
│     - Container                                     │
│     - Swarm Service                                 │
│  3. Route to appropriate manager                    │
│  4. Execute deployment                              │
│  5. Log all steps to DB                             │
│  6. Update deployment status                        │
│  7. Update commit status in Gitea                   │
└─────────────────────────────────────────────────────┘
```

### 3A. Déploiement VM (XenServer)

```
┌─────────────────────────────────────────────────────┐
│  XenServer Manager                                  │
│                                                      │
│  Step 1: Connect to XenServer                       │
│  ├─ Establish XML-RPC session                       │
│  └─ Authenticate                                    │
│                                                      │
│  Step 2: Find Template                              │
│  ├─ Query VM records                                │
│  ├─ Filter: is_a_template == true                   │
│  └─ Match name_label                                │
│                                                      │
│  Step 3: Clone VM                                   │
│  ├─ VM.clone(template_ref, new_name)                │
│  └─ Get new VM reference                            │
│                                                      │
│  Step 4: Configure Resources                        │
│  ├─ Set VCPUs (max + startup)                       │
│  ├─ Set Memory (static + dynamic limits)            │
│  └─ Configure network                               │
│                                                      │
│  Step 5: Cloud-init Setup                           │
│  ├─ Build datasource URL                            │
│  ├─ Add to xenstore-data:                           │
│  │   - vm-data/cloud-init/datasource                │
│  │   - vm-data/cloud-init/role                      │
│  │   - vm-data/cloud-init/environment               │
│  └─ Add custom parameters                           │
│                                                      │
│  Step 6: Start VM                                   │
│  ├─ VM.start(vm_ref)                                │
│  └─ Wait for boot                                   │
│                                                      │
│  Step 7: Verify                                     │
│  ├─ Get VM info                                     │
│  ├─ Check power state                               │
│  └─ Return deployment result                        │
└─────────────────────────────────────────────────────┘
```

### 3B. Déploiement Container (Docker)

```
┌─────────────────────────────────────────────────────┐
│  Docker Manager                                     │
│                                                      │
│  Step 1: Connect to Docker                          │
│  ├─ Use socket or remote host                       │
│  └─ Ping to verify connection                       │
│                                                      │
│  Step 2: Pull Image                                 │
│  ├─ docker.images.pull(image:tag)                   │
│  └─ Log pull progress                               │
│                                                      │
│  Step 3: Prepare Configuration                      │
│  ├─ Parse port mappings                             │
│  ├─ Parse volume mounts                             │
│  ├─ Prepare environment variables                   │
│  └─ Set labels + metadata                           │
│                                                      │
│  Step 4: Remove Existing (if any)                   │
│  ├─ Try to get container by name                    │
│  ├─ If exists: stop + remove                        │
│  └─ Clean up                                        │
│                                                      │
│  Step 5: Create & Start                             │
│  ├─ docker.containers.run(...)                      │
│  ├─ detach=True                                     │
│  └─ Get container ID                                │
│                                                      │
│  Step 6: Verify                                     │
│  ├─ Check container status                          │
│  └─ Return deployment result                        │
└─────────────────────────────────────────────────────┘
```

### 3C. Déploiement Swarm Service

```
┌─────────────────────────────────────────────────────┐
│  Docker Manager (Swarm Mode)                        │
│                                                      │
│  Step 1: Verify Swarm                               │
│  ├─ Check swarm.attrs                               │
│  └─ Ensure cluster is active                        │
│                                                      │
│  Step 2: Pull Image                                 │
│  ├─ docker.images.pull(image:tag)                   │
│  └─ On all nodes (Swarm handles)                    │
│                                                      │
│  Step 3: Check Existing Service                     │
│  ├─ Try services.get(name)                          │
│  └─ Decide: create new or update                    │
│                                                      │
│  Step 4A: Update Service (if exists)                │
│  ├─ service.update(...)                             │
│  ├─ Rolling update config                           │
│  └─ Swarm orchestrates update                       │
│                                                      │
│  Step 4B: Create Service (if new)                   │
│  ├─ services.create(...)                            │
│  ├─ Set replicas                                    │
│  ├─ Configure placement constraints                 │
│  ├─ Set update policy                               │
│  └─ Configure endpoint (ports)                      │
│                                                      │
│  Step 5: Monitor Deployment                         │
│  ├─ service.tasks()                                 │
│  ├─ Check task states                               │
│  └─ Wait for desired state                          │
│                                                      │
│  Step 6: Verify                                     │
│  ├─ Count running replicas                          │
│  └─ Return deployment result                        │
└─────────────────────────────────────────────────────┘
```

## Modèle de Données

### Deployment Record (PostgreSQL)

```
┌─────────────────────────────────────────────────────┐
│  deployments table                                  │
├─────────────────────────────────────────────────────┤
│  id                 SERIAL PRIMARY KEY              │
│  deployment_type    VARCHAR(50)  (vm/container/...)│
│  name               VARCHAR(255)                    │
│  environment        VARCHAR(50)  (prod/staging/dev)│
│  status             VARCHAR(50)  (pending/completed)│
│  git_commit         VARCHAR(255)                    │
│  git_branch         VARCHAR(255)                    │
│  git_repository     VARCHAR(500)                    │
│  config             JSONB                           │
│  created_at         TIMESTAMP                       │
│  updated_at         TIMESTAMP                       │
│  completed_at       TIMESTAMP                       │
│  error_message      TEXT                            │
│  rollback_from      INTEGER (FK → deployments.id)  │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  deployment_logs table                              │
├─────────────────────────────────────────────────────┤
│  id                 SERIAL PRIMARY KEY              │
│  deployment_id      INTEGER (FK → deployments.id)  │
│  timestamp          TIMESTAMP                       │
│  level              VARCHAR(20) (info/error/warn)  │
│  message            TEXT                            │
│  metadata           JSONB                           │
└─────────────────────────────────────────────────────┘
```

## Sécurité et Authentification

```
┌─────────────────────────────────────────────────────┐
│  Security Layers                                    │
│                                                      │
│  1. Webhook Signature Verification                  │
│     ├─ HMAC-SHA256 signature                        │
│     ├─ Shared secret (GITEA_WEBHOOK_SECRET)         │
│     └─ Reject if signature invalid                  │
│                                                      │
│  2. Gitea API Authentication                        │
│     ├─ Personal Access Token                        │
│     ├─ Bearer token in headers                      │
│     └─ API rate limiting                            │
│                                                      │
│  3. XenServer Authentication                        │
│     ├─ Username/password                            │
│     ├─ XML-RPC session                              │
│     └─ Session timeout management                   │
│                                                      │
│  4. Docker Socket Access                            │
│     ├─ Unix socket permissions                      │
│     ├─ Container runs as non-root (future)          │
│     └─ Volume mount restrictions                    │
│                                                      │
│  5. Database Security                               │
│     ├─ Password authentication                      │
│     ├─ Network isolation                            │
│     └─ Connection pooling                           │
└─────────────────────────────────────────────────────┘
```

## Monitoring et Observabilité

```
┌─────────────────────────────────────────────────────┐
│  Metrics (Prometheus)                               │
│                                                      │
│  - webhook_received_total                           │
│  - deployments_total{type, status}                  │
│  - deployment_duration_seconds                      │
│  - api_request_duration_seconds                     │
│  - database_connection_pool_size                    │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Logs (Structured JSON)                             │
│                                                      │
│  - Application logs (structlog)                     │
│  - Deployment logs (per deployment)                 │
│  - Error tracking                                   │
│  - Audit trail                                      │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Health Checks                                      │
│                                                      │
│  - /health endpoint                                 │
│  - Database connectivity                            │
│  - Gitea API reachability                           │
│  - Docker daemon status                             │
└─────────────────────────────────────────────────────┘
```

## Évolutivité

Le système est conçu pour évoluer :

1. **Horizontal Scaling** : Plusieurs instances d'orchestrateurs peuvent partager la même base de données
2. **Queue System** : Possibilité d'ajouter Redis/RabbitMQ pour traitement asynchrone
3. **Multi-cluster** : Support de plusieurs clusters XenServer et Docker
4. **Multi-région** : Déploiements géographiquement distribués
