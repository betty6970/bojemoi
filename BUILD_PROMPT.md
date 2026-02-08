# BUILD PROMPT: BOJEMOI LAB - Infrastructure-as-Code Platform

## Project Overview

Build a hybrid Infrastructure-as-Code platform called **Bojemoi Lab** that manages:
- VM deployment on XenServer/XCP-ng with cloud-init
- Container orchestration via Docker Swarm
- Security scanning with unified pentest orchestration
- Blockchain-based immutable deployment audit trail
- Enterprise monitoring stack (Prometheus, Grafana, Loki)

---

## Core Components to Build

### 1. Provisioning Orchestrator (FastAPI)

```
provisioning/orchestrator/app/
├── main.py              # FastAPI app with lifespan management
├── config.py            # Pydantic BaseSettings configuration
├── models/
│   └── schemas.py       # Request/response models with Enums
├── services/
│   ├── gitea_client.py      # Fetch configs from Git repository
│   ├── xenserver_client.py  # XenAPI VM deployment
│   ├── docker_client.py     # Docker Swarm service management
│   ├── cloudinit_gen.py     # Jinja2 cloud-init templating
│   ├── database.py          # PostgreSQL async (asyncpg)
│   ├── blockchain.py        # SHA-256 hash chain audit log
│   └── ip2location_client.py # Geolocation validation
└── middleware/
    └── ip_validation.py     # Country-based access control
```

**API Endpoints:**
- `POST /api/v1/vm/deploy` - Deploy VM to XenServer
- `POST /api/v1/container/deploy` - Deploy Docker Swarm service
- `GET /api/v1/deployments` - List deployments (paginated)
- `GET /api/v1/blockchain/verify` - Verify audit chain integrity
- `GET /health` - Service health check

### 2. Pentest Orchestrator (Plugin Architecture)

```
samsonov/pentest_orchestrator/
├── main.py              # PluginManager + PentestOrchestrator
├── import_results.py    # Faraday result importer
└── plugins/
    ├── plugin_nuclei.py     # Template-based vuln scanner
    ├── plugin_masscan.py    # Fast port scanner
    ├── plugin_zap.py        # OWASP ZAP integration
    ├── plugin_burp.py       # Burp Suite API
    ├── plugin_vulnx.py      # CMS vulnerability scanner
    ├── plugin_metasploit.py # Metasploit RPC
    └── plugin_faraday.py    # Result aggregation platform
```

**Scan Types:** full, web, network, vuln, cms

**Features:** Redis daemon mode, Faraday import, session management

### 3. Docker Swarm Stacks

**Core Services (01-service-hl.yml):**
- Traefik (reverse proxy + Let's Encrypt)
- Prometheus + Grafana + Loki + Alertmanager
- PostgreSQL + PgAdmin
- CrowdSec + Suricata (security)
- Postfix + ProtonMail Bridge (mail)
- Docker Registry (local)

**Security Stack (40-service-borodino.yml):**
- OWASP ZAP, Nuclei, VulnX, Metasploit
- Faraday vulnerability management
- Redis for job queuing

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| API | FastAPI 0.109, Uvicorn, Pydantic 2.5 |
| Async | httpx, asyncpg, APScheduler |
| Database | PostgreSQL 15, SQLAlchemy 2.0 |
| VM | XenAPI (XenServer/XCP-ng) |
| Containers | docker-py 7.0, Docker Swarm |
| Templates | Jinja2, PyYAML |
| Security | IP2Location, SHA-256 blockchain |

---

## Integration Points

1. **Gitea** - Git-based config repository (cloud-init templates)
2. **XenServer** - VM lifecycle via XenAPI
3. **Docker Swarm** - Container orchestration
4. **Faraday** - Vulnerability aggregation
5. **Prometheus** - Metrics collection
6. **Loki** - Log aggregation

---

## Key Features

- **Blockchain Audit Trail**: Every deployment logged with SHA-256 hash chain
- **Geo-Validation**: Block requests from non-allowed countries
- **Plugin Architecture**: Dynamic loading of pentest tools
- **Cloud-Init**: Jinja2 templates for VM provisioning
- **Multi-DB**: Separate databases for deployments, geolocation, blockchain

---

## Environment Variables

```env
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=deployments
POSTGRES_USER=orchestrator
POSTGRES_PASSWORD=secret

# Gitea
GITEA_URL=https://gitea.example.com
GITEA_TOKEN=xxx
GITEA_REPO=bojemoi-configs

# XenServer
XENSERVER_URL=https://xenserver.local
XENSERVER_USER=root
XENSERVER_PASSWORD=xxx

# IP Validation
IP_VALIDATION_ENABLED=true
ALLOWED_COUNTRIES=FR,DE,CH,BE,LU,NL,AT
```

---

## Data Models

### Enums

```python
class OSType(str, Enum):
    ALPINE = "alpine"
    UBUNTU = "ubuntu"
    DEBIAN = "debian"

class Environment(str, Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEV = "dev"

class DeploymentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
```

### VM Deploy Request

```python
class VMDeployRequest(BaseModel):
    name: str                    # VM name
    template: str                # Cloud-init template name
    os_type: OSType              # alpine, ubuntu, debian
    cpu: int = 2                 # 1-32 CPUs
    memory: int = 2048           # Memory in MB (min 512)
    disk: int = 20               # Disk in GB (min 10)
    network: str = "default"     # Network name
    environment: Environment     # production, staging, dev
    variables: Dict[str, Any]    # Additional cloud-init vars
```

### Container Deploy Request

```python
class ContainerDeployRequest(BaseModel):
    name: str                    # Service name
    image: str                   # Docker image
    replicas: int = 1            # Number of replicas
    environment: Dict[str, str]  # Environment variables
    ports: List[str]             # Port mappings (e.g., "80:80")
    networks: List[str]          # Networks to attach
    labels: Dict[str, str]       # Service labels (Traefik, etc.)
```

### Blockchain Block

```python
class BlockchainBlock(BaseModel):
    id: int
    block_number: int
    previous_hash: Optional[str]
    current_hash: str            # SHA-256 hash
    deployment_type: str         # vm, container
    name: str
    config: Dict[str, Any]
    resource_ref: Optional[str]
    status: DeploymentStatus
    source_ip: Optional[str]
    source_country: Optional[str]
    created_at: datetime
```

---

## Database Schema

### deployments table

```sql
CREATE TABLE deployments (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,
    resource_ref VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_deployments_type ON deployments(type);
CREATE INDEX idx_deployments_status ON deployments(status);
```

### deployment_blocks table (Blockchain)

```sql
CREATE TABLE deployment_blocks (
    id SERIAL PRIMARY KEY,
    block_number INTEGER UNIQUE NOT NULL,
    previous_hash VARCHAR(64),
    current_hash VARCHAR(64) NOT NULL,
    deployment_type VARCHAR(50) NOT NULL,
    name VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,
    resource_ref VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    error TEXT,
    source_ip VARCHAR(45),
    source_country VARCHAR(2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_blocks_number ON deployment_blocks(block_number);
```

---

## Deployment Workflow

### VM Deployment Flow

1. `POST /api/v1/vm/deploy` with VMDeployRequest
2. IP validation middleware checks source country
3. Fetch cloud-init template from Gitea
4. Render Jinja2 template with variables
5. Create VM on XenServer with rendered cloud-init
6. Log to blockchain with SHA-256 hash chain
7. Log to PostgreSQL deployments table
8. Return deployment_id and VM reference

### Container Deployment Flow

1. `POST /api/v1/container/deploy` with ContainerDeployRequest
2. IP validation checks country
3. Create Docker Swarm service
4. Log to blockchain
5. Log to PostgreSQL
6. Return deployment_id and service ID

### Pentest Scan Flow

1. Configure scan target and type
2. PluginManager loads all plugins dynamically
3. Execute scan sequence (e.g., Masscan → ZAP → Nuclei)
4. Aggregate results with severity breakdown
5. Save results locally as JSON
6. Import to Faraday workspace
7. Store in Redis for async processing

---

## Running the Project

### Start Orchestrator

```bash
cd provisioning
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Pentest Daemon

```bash
cd samsonov/pentest_orchestrator
python main.py --daemon --workspace default
```

### Deploy Docker Stack

```bash
docker stack deploy -c stack/01-service-hl.yml base --prune --resolve-image always
```

### Test API

```bash
# Deploy VM
curl -X POST http://localhost:8000/api/v1/vm/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-vm",
    "template": "webserver",
    "os_type": "alpine",
    "cpu": 2,
    "memory": 2048
  }'

# Check health
curl http://localhost:8000/health

# Verify blockchain
curl http://localhost:8000/api/v1/blockchain/verify
```

---

## Security Considerations

1. **IP Validation**: Whitelist by country (default: Western Europe)
2. **Private IP Bypass**: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 skip geolocation
3. **CORS**: Configure allowed origins for production
4. **Database Credentials**: Environment-based, never hardcoded
5. **XenServer SSL**: Support for self-signed certificates
6. **Docker Socket**: Requires direct access for service management
7. **Blockchain Immutability**: SHA-256 hash chain prevents tampering

---

## Network Architecture

**Overlay Networks:**
- `monitoring` - Prometheus, Grafana, Loki, exporters
- `backend` - Internal services, databases
- `frontend` - Public-facing services
- `proxy` - Traefik routing
- `mail` - Postfix, ProtonMail Bridge

**Key Ports:**
- 80/443 - Traefik (HTTP/HTTPS)
- 8000/28080 - Orchestrator API
- 9090 - Prometheus
- 3000 - Grafana
- 3100 - Loki
- 5432 - PostgreSQL
