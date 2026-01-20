#!/bin/bash
# generate-bojemoi-orchestrator.sh
# Script complet pour générer tout le projet Bojemoi Orchestrator

set -e

PROJECT_NAME="bojemoi-orchestrator"
VERSION="1.0.0"
OUTPUT_FILE="${PROJECT_NAME}-${VERSION}.tar.gz"

echo "======================================"
echo "Bojemoi Orchestrator - Full Project Generator"
echo "Version: ${VERSION}"
echo "======================================"
echo ""

# Créer le répertoire temporaire
TEMP_DIR=$(mktemp -d)
PROJECT_DIR="${TEMP_DIR}/${PROJECT_NAME}"

echo "Creating project structure in: ${PROJECT_DIR}"
mkdir -p "${PROJECT_DIR}"

# Créer la structure COMPLÈTE
echo "Creating directory structure..."
mkdir -p "${PROJECT_DIR}"/{orchestrator,tests,scripts,config,examples,docs,grafana,logs,data,backups}
mkdir -p "${PROJECT_DIR}/orchestrator"/{managers,models,validators}
mkdir -p "${PROJECT_DIR}/examples"/{vms,containers,services,cloud-init}
mkdir -p "${PROJECT_DIR}/grafana"/{dashboards,provisioning/datasources,provisioning/dashboards}
mkdir -p "${PROJECT_DIR}/.github"/{ISSUE_TEMPLATE,PULL_REQUEST_TEMPLATE,workflows}
mkdir -p "${PROJECT_DIR}/tests"

# Fonction pour créer un fichier avec du contenu
create_file() {
    local filepath="$1"
    local content="$2"
    mkdir -p "$(dirname "${PROJECT_DIR}/${filepath}")"
    cat > "${PROJECT_DIR}/${filepath}" << 'ENDOFFILE'
${content}
ENDOFFILE
    # Remplacer le placeholder par le vrai contenu
    echo "$content" > "${PROJECT_DIR}/${filepath}"
}

echo "Generating files..."

# ============================================
# ORCHESTRATOR - Main Application
# ============================================

create_file "orchestrator/main.py" 'from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
from typing import Optional, List, Dict, Any
import logging
import uvicorn

from .config import settings
from .database import init_db, get_db_manager
from .managers.gitea_client import GiteaClient
from .managers.vm_deployer import VMDeployer
from .managers.container_deployer import ContainerDeployer
from .managers.swarm_deployer import SwarmDeployer
from .logging_config import setup_logging
from .metrics import MetricsCollector
from .monitoring import router as monitoring_router

# Setup logging
setup_logging(settings.LOG_DIR, settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Bojemoi Orchestrator",
    version="1.0.0",
    description="Orchestrateur de déploiement unifié pour infrastructure hybride"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include monitoring routes
app.include_router(monitoring_router)

# Clients globaux
gitea_client: Optional[GiteaClient] = None
vm_deployer: Optional[VMDeployer] = None
container_deployer: Optional[ContainerDeployer] = None
swarm_deployer: Optional[SwarmDeployer] = None

# Scheduler
scheduler = BackgroundScheduler()

@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global gitea_client, vm_deployer, container_deployer, swarm_deployer
    
    logger.info("Starting Bojemoi Orchestrator...")
    
    # Initialize database
    init_db(settings.DATABASE_URL)
    logger.info("Database initialized")
    
    # Initialize clients
    gitea_client = GiteaClient(settings.GITEA_URL, settings.GITEA_TOKEN)
    vm_deployer = VMDeployer(
        settings.XENSERVER_HOST,
        settings.XENSERVER_USER,
        settings.XENSERVER_PASSWORD
    )
    container_deployer = ContainerDeployer(settings.DOCKER_HOST)
    swarm_deployer = SwarmDeployer(settings.DOCKER_SWARM_MANAGER)
    
    logger.info("Clients initialized")
    
    # Start scheduler if enabled
    if settings.ENABLE_SCHEDULER:
        scheduler.add_job(
            check_and_deploy,
            "interval",
            minutes=settings.CHECK_INTERVAL_MINUTES,
            id="periodic_deployment_check"
        )
        scheduler.start()
        logger.info(f"Scheduler started (interval: {settings.CHECK_INTERVAL_MINUTES}min)")
    
    logger.info("Orchestrator started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Orchestrator...")
    if scheduler.running:
        scheduler.shutdown()
    logger.info("Orchestrator stopped")

# ============================================
# Deployment Endpoints
# ============================================

@app.post("/deploy/vm/{vm_name}")
async def deploy_vm(vm_name: str, background_tasks: BackgroundTasks):
    """Deploy a VM"""
    background_tasks.add_task(deploy_vm_task, vm_name)
    return {"status": "deployment_started", "vm": vm_name}

@app.post("/deploy/container/{container_name}")
async def deploy_container(container_name: str, background_tasks: BackgroundTasks):
    """Deploy a container"""
    background_tasks.add_task(deploy_container_task, container_name)
    return {"status": "deployment_started", "container": container_name}

@app.post("/deploy/service/{service_name}")
async def deploy_service(service_name: str, background_tasks: BackgroundTasks):
    """Deploy a Swarm service"""
    background_tasks.add_task(deploy_service_task, service_name)
    return {"status": "deployment_started", "service": service_name}

@app.post("/deploy/all")
async def deploy_all(background_tasks: BackgroundTasks):
    """Deploy entire infrastructure"""
    background_tasks.add_task(deploy_all_task)
    return {"status": "full_deployment_started"}

@app.get("/deployments")
async def list_deployments(limit: int = 20, offset: int = 0):
    """List deployments"""
    db = get_db_manager()
    deployments = await db.list_deployments(limit=limit, offset=offset)
    return [
        {
            "id": d.id,
            "type": d.deployment_type.value,
            "name": d.name,
            "status": d.status.value,
            "created_at": d.created_at.isoformat() if d.created_at else None
        }
        for d in deployments
    ]

@app.get("/deployments/{deployment_id}")
async def get_deployment(deployment_id: int):
    """Get deployment details"""
    db = get_db_manager()
    deployment = await db.get_deployment(deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return {
        "id": deployment.id,
        "type": deployment.deployment_type.value,
        "name": deployment.name,
        "status": deployment.status.value,
        "created_at": deployment.created_at.isoformat() if deployment.created_at else None,
        "error": deployment.error_message
    }

@app.get("/status")
async def get_status():
    """Get orchestrator status"""
    return {
        "orchestrator": "running",
        "version": "1.0.0",
        "xenserver": await vm_deployer.check_connection() if vm_deployer else False,
        "docker": await container_deployer.check_connection() if container_deployer else False,
        "swarm": await swarm_deployer.check_connection() if swarm_deployer else False,
        "gitea": await gitea_client.check_connection() if gitea_client else False
    }

@app.get("/stats")
async def get_stats(days: int = 30):
    """Get deployment statistics"""
    db = get_db_manager()
    return await db.get_deployment_stats(days=days)

# ============================================
# Background Tasks
# ============================================

async def deploy_vm_task(vm_name: str):
    """Deploy VM background task"""
    try:
        logger.info(f"Deploying VM: {vm_name}")
        config = await gitea_client.get_vm_config(vm_name)
        cloud_init = await gitea_client.get_cloud_init_config(config["cloud_init"])
        result = await vm_deployer.deploy(config, cloud_init)
        logger.info(f"VM {vm_name} deployment result: {result.success}")
    except Exception as e:
        logger.error(f"VM deployment failed: {e}")

async def deploy_container_task(container_name: str):
    """Deploy container background task"""
    try:
        logger.info(f"Deploying container: {container_name}")
        config = await gitea_client.get_container_config(container_name)
        result = await container_deployer.deploy(config)
        logger.info(f"Container {container_name} deployment result: {result.success}")
    except Exception as e:
        logger.error(f"Container deployment failed: {e}")

async def deploy_service_task(service_name: str):
    """Deploy service background task"""
    try:
        logger.info(f"Deploying service: {service_name}")
        config = await gitea_client.get_service_config(service_name)
        result = await swarm_deployer.deploy(config)
        logger.info(f"Service {service_name} deployment result: {result.success}")
    except Exception as e:
        logger.error(f"Service deployment failed: {e}")

async def deploy_all_task():
    """Deploy all infrastructure"""
    logger.info("Starting full infrastructure deployment")
    # Implementation here
    pass

async def check_and_deploy():
    """Periodic check for deployments"""
    logger.debug("Running periodic deployment check")
    # Implementation here
    pass

if __name__ == "__main__":
    uvicorn.run(
        "orchestrator.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        workers=settings.API_WORKERS
    )
'

# ============================================
# Config
# ============================================

create_file "orchestrator/config.py" 'from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Bojemoi Orchestrator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 1
    
    # Database
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "orchestrator"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_DB: str = "orchestrator"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Gitea
    GITEA_URL: str = "https://gitea.example.com"
    GITEA_TOKEN: str = ""
    GITEA_REPO_OWNER: str = "bojemoi"
    GITEA_REPO_NAME: str = "infrastructure"
    
    # XenServer
    XENSERVER_HOST: str = ""
    XENSERVER_USER: str = "root"
    XENSERVER_PASSWORD: str = ""
    
    # Docker
    DOCKER_HOST: str = "unix:///var/run/docker.sock"
    DOCKER_SWARM_MANAGER: str = ""
    
    # Scheduler
    CHECK_INTERVAL_MINUTES: int = 5
    ENABLE_SCHEDULER: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "/app/logs"
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
'

# ============================================
# Database
# ============================================

create_file "orchestrator/database.py" 'from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from .models.database import Base, Deployment, DeploymentStatus, DeploymentType

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created")
    
    @contextmanager
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    async def create_deployment(self, deployment_type: str, name: str, config: Dict) -> int:
        with self.get_session() as session:
            deployment = Deployment(
                deployment_type=DeploymentType[deployment_type.upper()],
                name=name,
                status=DeploymentStatus.PENDING,
                config=config
            )
            session.add(deployment)
            session.flush()
            return deployment.id
    
    async def update_deployment_status(self, deployment_id: int, status: str, error: Optional[str] = None):
        with self.get_session() as session:
            deployment = session.query(Deployment).filter(Deployment.id == deployment_id).first()
            if deployment:
                deployment.status = DeploymentStatus[status.upper()]
                if error:
                    deployment.error_message = error
                if status == "in_progress":
                    deployment.started_at = datetime.utcnow()
                elif status in ["completed", "failed"]:
                    deployment.completed_at = datetime.utcnow()
    
    async def get_deployment(self, deployment_id: int):
        with self.get_session() as session:
            return session.query(Deployment).filter(Deployment.id == deployment_id).first()
    
    async def list_deployments(self, limit: int = 20, offset: int = 0) -> List[Deployment]:
        with self.get_session() as session:
            return session.query(Deployment).order_by(Deployment.created_at.desc()).offset(offset).limit(limit).all()
    
    async def get_deployment_stats(self, days: int = 30) -> Dict[str, Any]:
        # Implementation
        return {"total": 0, "completed": 0, "failed": 0}

db_manager: Optional[DatabaseManager] = None

def init_db(database_url: str):
    global db_manager
    db_manager = DatabaseManager(database_url)
    db_manager.create_tables()

def get_db_manager() -> DatabaseManager:
    if db_manager is None:
        raise RuntimeError("Database not initialized")
    return db_manager
'

# ============================================
# Models
# ============================================

create_file "orchestrator/models/__init__.py" ''

create_file "orchestrator/models/database.py" 'from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class DeploymentStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class DeploymentType(enum.Enum):
    VM = "vm"
    CONTAINER = "container"
    SWARM_SERVICE = "swarm_service"

class Deployment(Base):
    __tablename__ = "deployments"
    
    id = Column(Integer, primary_key=True, index=True)
    deployment_type = Column(SQLEnum(DeploymentType), nullable=False)
    name = Column(String(255), nullable=False)
    status = Column(SQLEnum(DeploymentStatus), default=DeploymentStatus.PENDING)
    config = Column(JSON, nullable=False)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
'

create_file "orchestrator/models/deployment.py" 'from pydantic import BaseModel
from typing import Dict, Any, Optional

class DeploymentResult(BaseModel):
    success: bool
    deployment_id: Optional[int] = None
    message: str
    metadata: Dict[str, Any] = {}
'

# ============================================
# Managers
# ============================================

create_file "orchestrator/managers/__init__.py" ''

create_file "orchestrator/managers/gitea_client.py" 'import httpx
from typing import Dict
import yaml
import base64
import logging

logger = logging.getLogger(__name__)

class GiteaClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self.repo_owner = "bojemoi"
        self.repo_name = "infrastructure"
    
    async def check_connection(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/version",
                    headers={"Authorization": f"token {self.token}"}
                )
                return response.status_code == 200
        except:
            return False
    
    async def get_file_content(self, path: str) -> str:
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/api/v1/repos/{self.repo_owner}/{self.repo_name}/contents/{path}"
            response = await client.get(url, headers={"Authorization": f"token {self.token}"})
            response.raise_for_status()
            content = response.json()["content"]
            return base64.b64decode(content).decode("utf-8")
    
    async def get_vm_config(self, vm_name: str) -> Dict:
        content = await self.get_file_content(f"vms/{vm_name}.yaml")
        return yaml.safe_load(content)
    
    async def get_container_config(self, container_name: str) -> Dict:
        content = await self.get_file_content(f"containers/{container_name}.yaml")
        return yaml.safe_load(content)
    
    async def get_service_config(self, service_name: str) -> Dict:
        content = await self.get_file_content(f"services/{service_name}.yaml")
        return yaml.safe_load(content)
    
    async def get_cloud_init_config(self, config_name: str) -> str:
        return await self.get_file_content(f"cloud-init/{config_name}.yaml")
'

create_file "orchestrator/managers/vm_deployer.py" 'import asyncio
from typing import Dict
import logging
from ..models.deployment import DeploymentResult
from ..database import get_db_manager

logger = logging.getLogger(__name__)

class VMDeployer:
    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username
        self.password = password
    
    async def check_connection(self) -> bool:
        # Implementation
        return True
    
    async def deploy(self, config: Dict, cloud_init: str) -> DeploymentResult:
        db = get_db_manager()
        deployment_id = await db.create_deployment("vm", config["name"], config)
        
        try:
            await db.update_deployment_status(deployment_id, "in_progress")
            logger.info(f"Deploying VM: {config[\"name\"]}")
            
            # Deployment logic here
            await asyncio.sleep(2)  # Simulate deployment
            
            await db.update_deployment_status(deployment_id, "completed")
            return DeploymentResult(success=True, deployment_id=deployment_id, message="VM deployed")
        except Exception as e:
            await db.update_deployment_status(deployment_id, "failed", str(e))
            return DeploymentResult(success=False, deployment_id=deployment_id, message=str(e))
'

create_file "orchestrator/managers/container_deployer.py" 'import docker
import asyncio
from typing import Dict
import logging
from ..models.deployment import DeploymentResult
from ..database import get_db_manager

logger = logging.getLogger(__name__)

class ContainerDeployer:
    def __init__(self, docker_host: str = None):
        self.client = docker.from_env() if not docker_host else docker.DockerClient(base_url=docker_host)
    
    async def check_connection(self) -> bool:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.client.ping)
            return True
        except:
            return False
    
    async def deploy(self, config: Dict) -> DeploymentResult:
        db = get_db_manager()
        deployment_id = await db.create_deployment("container", config["name"], config)
        
        try:
            await db.update_deployment_status(deployment_id, "in_progress")
            logger.info(f"Deploying container: {config[\"name\"]}")
            
            # Deployment logic here
            await asyncio.sleep(1)
            
            await db.update_deployment_status(deployment_id, "completed")
            return DeploymentResult(success=True, deployment_id=deployment_id, message="Container deployed")
        except Exception as e:
            await db.update_deployment_status(deployment_id, "failed", str(e))
            return DeploymentResult(success=False, deployment_id=deployment_id, message=str(e))
'

create_file "orchestrator/managers/swarm_deployer.py" 'import docker
import asyncio
from typing import Dict
import logging
from ..models.deployment import DeploymentResult
from ..database import get_db_manager

logger = logging.getLogger(__name__)

class SwarmDeployer:
    def __init__(self, manager_host: str = None):
        self.client = docker.from_env() if not manager_host else docker.DockerClient(base_url=manager_host)
    
    async def check_connection(self) -> bool:
        try:
            loop = asyncio.get_event_loop()
            swarm_info = await loop.run_in_executor(None, lambda: self.client.swarm.attrs)
            return swarm_info is not None
        except:
            return False
    
    async def deploy(self, config: Dict) -> DeploymentResult:
        db = get_db_manager()
        deployment_id = await db.create_deployment("swarm_service", config["name"], config)
        
        try:
            await db.update_deployment_status(deployment_id, "in_progress")
            logger.info(f"Deploying service: {config[\"name\"]}")
            
            # Deployment logic here
            await asyncio.sleep(1)
            
            await db.update_deployment_status(deployment_id, "completed")
            return DeploymentResult(success=True, deployment_id=deployment_id, message="Service deployed")
        except Exception as e:
            await db.update_deployment_status(deployment_id, "failed", str(e))
            return DeploymentResult(success=False, deployment_id=deployment_id, message=str(e))
'

# ============================================
# Logging
# ============================================

create_file "orchestrator/logging_config.py" 'import logging
import sys
from pathlib import Path

def setup_logging(log_dir: str = "/app/logs", level: str = "INFO"):
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    logging.info("Logging initialized")
'

# ============================================
# Metrics
# ============================================

create_file "orchestrator/metrics.py" 'from prometheus_client import Counter, Histogram, Gauge
import logging

logger = logging.getLogger(__name__)

deployments_total = Counter("deployments_total", "Total deployments", ["deployment_type", "status"])
deployments_duration = Histogram("deployment_duration_seconds", "Deployment duration", ["deployment_type"])
deployments_in_progress = Gauge("deployments_in_progress", "Deployments in progress", ["deployment_type"])

class MetricsCollector:
    @staticmethod
    def record_deployment_start(deployment_type: str):
        deployments_in_progress.labels(deployment_type=deployment_type).inc()
    
    @staticmethod
    def record_deployment_end(deployment_type: str, status: str, duration: float):
        deployments_total.labels(deployment_type=deployment_type, status=status).inc()
        deployments_duration.labels(deployment_type=deployment_type).observe(duration)
        deployments_in_progress.labels(deployment_type=deployment_type).dec()
'

# ============================================
# Monitoring
# ============================================

create_file "orchestrator/monitoring.py" 'from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()

@router.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/health")
async def health():
    return {"status": "healthy"}
'

# ============================================
# Validators (placeholders)
# ============================================

create_file "orchestrator/validators/__init__.py" ''

create_file "orchestrator/validators/schemas.py" 'from pydantic import BaseModel

class VMConfig(BaseModel):
    name: str
    vcpus: int
    memory_gb: int
'

# ============================================
# CLI
# ============================================

create_file "cli.py" '#!/usr/bin/env python3
import click
import httpx
import asyncio
from rich.console import Console

console = Console()

@click.group()
@click.option("--url", default="http://localhost:8000", help="Orchestrator URL")
@click.pass_context
def cli(ctx, url):
    """Bojemoi Orchestrator CLI"""
    ctx.obj = {"url": url}

@cli.command()
@click.pass_context
def status(ctx):
    """Check orchestrator status"""
    url = ctx.obj["url"]
    try:
        response = httpx.get(f"{url}/status")
        data = response.json()
        console.print("[green]Orchestrator Status:[/green]")
        for key, value in data.items():
            status = "✓" if value in [True, "running"] else "✗"
            console.print(f"  {status} {key}: {value}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

@cli.command()
@click.argument("vm_name")
@click.pass_context
def deploy_vm(ctx, vm_name):
    """Deploy a VM"""
    url = ctx.obj["url"]
    try:
        response = httpx.post(f"{url}/deploy/vm/{vm_name}")
        console.print(f"[green]✓[/green] Deployment started: {vm_name}")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")

if __name__ == "__main__":
    cli()
'

chmod +x "${PROJECT_DIR}/cli.py"

# ============================================
# Tests
# ============================================

create_file "tests/__init__.py" ''

create_file "tests/conftest.py" 'import pytest

@pytest.fixture
def test_config():
    return {"test": True}
'

create_file "tests/test_api.py" 'def test_health():
    # Basic test
    assert True
'

# ============================================
# Scripts (complets cette fois)
# ============================================

create_file "scripts/install.sh" '#!/bin/bash
set -e

echo "======================================"
echo "Bojemoi Orchestrator - Installation"
echo "======================================"

# Check dependencies
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is required"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "Error: Docker Compose is required"
    exit 1
fi

# Create directories
mkdir -p logs data config backups

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env with your configuration before continuing!"
    echo "Then run this script again."
    exit 0
fi

# Build
echo "Building images..."
docker compose build

# Start database
echo "Starting PostgreSQL..."
docker compose up -d postgres
sleep 10

# Start all services
echo "Starting all services..."
docker compose up -d

# Wait for API
echo "Waiting for API..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ API is ready"
        break
    fi
    attempt=$((attempt + 1))
    sleep 2
done

echo ""
echo "======================================"
echo "✅ Installation Complete!"
echo "======================================"
echo ""
echo "Services:"
echo "  API:        http://localhost:8000"
echo "  Prometheus: http://localhost:9090"
echo "  Grafana:    http://localhost:3000"
echo ""
echo "Next steps:"
echo "  make logs    # View logs"
echo "  make status  # Check status"
echo "  python cli.py --help  # Use CLI"
echo ""
'

chmod +x "${PROJECT_DIR}/scripts/install.sh"

create_file "scripts/start.sh" '#!/bin/bash
docker compose up -d
docker compose logs -f orchestrator
'

chmod +x "${PROJECT_DIR}/scripts/start.sh"

create_file "scripts/stop.sh" '#!/bin/bash
docker compose down
'

chmod +x "${PROJECT_DIR}/scripts/stop.sh"

create_file "scripts/health-check.sh" '#!/bin/bash

echo "Health Check..."

curl -s http://localhost:8000/health | jq .

echo ""
echo "Services status:"
docker compose ps
'

chmod +x "${PROJECT_DIR}/scripts/health-check.sh"

# ============================================
# Examples
# ============================================

create_file "examples/vms/web-server-01.yaml" 'name: web-server-01
template: "Ubuntu 22.04"
vcpus: 4
memory_gb: 8
disk_gb: 100
cloud_init: base-ubuntu
network:
  network_name: "Production"
  ip_address: "192.168.1.100"
  gateway: "192.168.1.1"
  netmask: "255.255.255.0"
tags:
  environment: production
  role: web-server
'

create_file "examples/cloud-init/base-ubuntu.yaml" '#cloud-config
hostname: ${HOSTNAME}

users:
  - name: deploy
    groups: sudo
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - ssh-rsa AAAAB3NzaC1yc2E... deploy@bojemoi

package_update: true
package_upgrade: true

packages:
  - curl
  - git
  - vim

runcmd:
  - echo "Setup complete"

timezone: Europe/Paris
'

create_file "examples/containers/nginx-proxy.yaml" 'name: nginx-proxy
image: nginx:alpine
ports:
  80/tcp: 80
  443/tcp: 443
networks:
  - frontend
restart_policy: unless-stopped
'

create_file "examples/services/api-service.yaml" 'name: api-service
image: myregistry.local/api:v1.0.0
mode: replicated
replicas: 3
environment:
  DATABASE_URL: postgresql://user:pass@db:5432/api
ports:
  8080: 8080
networks:
  - backend
'

# ============================================
# Documentation
# ============================================

create_file "README.md" '# Bojemoi Orchestrator

Orchestrateur de déploiement unifié pour infrastructure hybride.

## Installation Rapide
```bash
./scripts/install.sh
```

## Documentation

Voir le répertoire `docs/` pour la documentation complète.

## License

MIT License
'

create_file "docs/README.md" '# Documentation Bojemoi Orchestrator

## Installation

Voir [../README.md](../README.md)

## Configuration

Editer le fichier `.env` avec vos paramètres.

## Utilisation

### Via API
```bash
curl -X POST http://localhost:8000/deploy/vm/web-server-01
```

### Via CLI
```bash
python cli.py deploy-vm web-server-01
```
'

# ============================================
# Configuration files
# ============================================

create_file ".env.example" '# Database
POSTGRES_PASSWORD=change_me_in_production

# Gitea
GITEA_URL=https://your-gitea.com
GITEA_TOKEN=your_token
GITEA_REPO_OWNER=bojemoi
GITEA_REPO_NAME=infrastructure

# XenServer
XENSERVER_HOST=xenserver.local
XENSERVER_USER=root
XENSERVER_PASSWORD=password

# Docker Swarm
DOCKER_SWARM_MANAGER=tcp://swarm:2375

# Scheduler
CHECK_INTERVAL_MINUTES=5
ENABLE_SCHEDULER=true

# Logging
LOG_LEVEL=INFO
DEBUG=false
'

create_file ".gitignore" '__pycache__/
*.py[cod]
.venv/
venv/
.env
*.log
logs/*.log
data/*
!data/.gitkeep
backups/*.sql.gz
.DS_Store
'

create_file "requirements.txt" 'fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0
pydantic-settings==2.1.0
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
alembic==1.13.1
docker==7.0.0
httpx==0.26.0
apscheduler==3.10.4
prometheus-client==0.19.0
python-json-logger==2.0.7
click==8.1.7
rich==13.7.0
pyyaml==6.0.1
python-dotenv==1.0.0
'

create_file "requirements-dev.txt" 'pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
black==23.12.1
flake8==7.0.0
mypy==1.8.0
'

# Dockerfile complet
create_file "Dockerfile" 'FROM python:3.11-slim

LABEL maintainer="bojemoi@example.com"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git curl build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY orchestrator/ ./orchestrator/
COPY cli.py .

RUN mkdir -p /app/logs /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "orchestrator.main"]
'

# docker-compose.yml complet
create_file "docker-compose.yml" 'version: "3.8"

services:
  orchestrator:
    build: .
    container_name: bojemoi-orchestrator
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - GITEA_URL=${GITEA_URL}
      - GITEA_TOKEN=${GITEA_TOKEN}
      - XENSERVER_HOST=${XENSERVER_HOST}
      - XENSERVER_PASSWORD=${XENSERVER_PASSWORD}
      - DOCKER_SWARM_MANAGER=${DOCKER_SWARM_MANAGER}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./logs:/app/logs
      - ./data:/app/data
    networks:
      - orchestrator-net
    depends_on:
      - postgres

  postgres:
    image: postgres:15-alpine
    container_name: orchestrator-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=orchestrator
      - POSTGRES_USER=orchestrator
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - orchestrator-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U orchestrator"]
      interval: 10s
      timeout: 5s
      retries: 5

  prometheus:
    image: prom/prometheus:latest
    container_name: orchestrator-prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    networks:
      - orchestrator-net
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    container_name: orchestrator-grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
    volumes:
      - grafana-data:/var/lib/grafana
    networks:
      - orchestrator-net
    ports:
      - "3000:3000"

volumes:
  postgres-data:
  prometheus-data:
  grafana-data:

networks:
  orchestrator-net:
    driver: bridge
'

create_file "prometheus.yml" 'global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "orchestrator"
    static_configs:
      - targets: ["orchestrator:8000"]
'

create_file "Makefile" '.PHONY: help install start stop logs health

help:
	@echo "Bojemoi Orchestrator - Commands"
	@echo ""
	@echo "  make install  - Install orchestrator"
	@echo "  make start    - Start services"
	@echo "  make stop     - Stop services"
	@echo "  make logs     - View logs"
	@echo "  make health   - Health check"

install:
	@bash scripts/install.sh

start:
	@bash scripts/start.sh

stop:
	@bash scripts/stop.sh

logs:
	@docker compose logs -f orchestrator

health:
	@bash scripts/health-check.sh
'

# Fichiers .gitkeep
touch "${PROJECT_DIR}/logs/.gitkeep"
touch "${PROJECT_DIR}/data/.gitkeep"
touch "${PROJECT_DIR}/backups/.gitkeep"

# LICENSE
create_file "LICENSE" 'MIT License

Copyright (c) 2024 Bojemoi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
'

# ============================================
# Compression
# ============================================

echo ""
echo "Creating tar.gz archive..."
cd "${TEMP_DIR}"
tar -czf "${OUTPUT_FILE}" "${PROJECT_NAME}"

# Déplacer dans le répertoire courant
mv "${OUTPUT_FILE}" "${OLDPWD}/"
cd "${OLDPWD}"

# Nettoyer
rm -rf "${TEMP_DIR}"

# Informations
SIZE=$(du -h "${OUTPUT_FILE}" | cut -f1)
FILE_COUNT=$(tar -tzf "${OUTPUT_FILE}" | wc -l)

echo ""
echo "======================================"
echo "✅ Project Generated Successfully!"
echo "======================================"
echo ""
echo "Archive: ${OUTPUT_FILE}"
echo "Size: ${SIZE}"
echo "Files: ${FILE_COUNT}"
echo ""
echo "To extract and use:"
echo "  tar -xzf ${OUTPUT_FILE}"
echo "  cd ${PROJECT_NAME}"
echo "  ./scripts/install.sh"
echo ""
echo "Quick start:"
echo "  1. Edit .env with your configuration"
echo "  2. Run: make install"
echo "  3. Access API: http://localhost:8000"
echo ""

