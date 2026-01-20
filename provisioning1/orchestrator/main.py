from fastapi import FastAPI, BackgroundTasks, HTTPException
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
        workers=1
#        workers=settings.API_WORKERS
    )

