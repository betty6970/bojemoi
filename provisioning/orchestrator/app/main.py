"""Main FastAPI application"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from app.config import settings
from app.models.schemas import (
    VMDeployRequest, ContainerDeployRequest,
    DeploymentResponse, HealthResponse, DeploymentListResponse
)
from app.services.gitea_client import GiteaClient
from app.services.xenserver_client import XenServerClient
from app.services.docker_client import DockerSwarmClient
from app.services.cloudinit_gen import CloudInitGenerator
from app.services.database import Database

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize clients (will be initialized on startup)
gitea_client: Optional[GiteaClient] = None
xenserver_client: Optional[XenServerClient] = None
docker_client: Optional[DockerSwarmClient] = None
cloudinit_gen: Optional[CloudInitGenerator] = None
db: Optional[Database] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup and shutdown)"""
    global gitea_client, xenserver_client, docker_client, cloudinit_gen, db
    
    # Startup
    logger.info("Initializing Bojemoi Orchestrator...")
    
    try:
        # Initialize Gitea client
        gitea_client = GiteaClient(
            base_url=settings.GITEA_URL,
            token=settings.GITEA_TOKEN,
            repo=settings.GITEA_REPO
        )
        logger.info("Gitea client initialized")
        
        # Initialize XenServer client
        xenserver_client = XenServerClient(
            url=settings.XENSERVER_URL,
            username=settings.XENSERVER_USER,
            password=settings.XENSERVER_PASS
        )
        logger.info("XenServer client initialized")
        
        # Initialize Docker Swarm client
        docker_client = DockerSwarmClient(
            base_url=settings.DOCKER_SWARM_URL
        )
        logger.info("Docker Swarm client initialized")
        
        # Initialize CloudInit generator
        cloudinit_gen = CloudInitGenerator(gitea_client)
        logger.info("CloudInit generator initialized")
        
        # Initialize Database
        db = Database(settings.DATABASE_URL)
        await db.init_db()
        logger.info("Database initialized")
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down Bojemoi Orchestrator...")
    
    if xenserver_client:
        await xenserver_client.close()
    
    if docker_client:
        await docker_client.close()
    
    if db:
        await db.close()
    
    logger.info("Shutdown complete")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "service": "Bojemoi Orchestrator",
        "version": settings.API_VERSION,
        "status": "running"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check Gitea
    try:
        gitea_ok = await gitea_client.ping()
        health_status["services"]["gitea"] = "up" if gitea_ok else "down"
    except Exception as e:
        health_status["services"]["gitea"] = "down"
        logger.error(f"Gitea health check failed: {e}")
    
    # Check XenServer
    try:
        xenserver_ok = await xenserver_client.ping()
        health_status["services"]["xenserver"] = "up" if xenserver_ok else "down"
    except Exception as e:
        health_status["services"]["xenserver"] = "down"
        logger.error(f"XenServer health check failed: {e}")
    
    # Check Docker Swarm
    try:
        docker_ok = await docker_client.ping()
        health_status["services"]["docker_swarm"] = "up" if docker_ok else "down"
    except Exception as e:
        health_status["services"]["docker_swarm"] = "down"
        logger.error(f"Docker Swarm health check failed: {e}")
    
    # Check Database
    try:
        db_ok = await db.ping()
        health_status["services"]["database"] = "up" if db_ok else "down"
    except Exception as e:
        health_status["services"]["database"] = "down"
        logger.error(f"Database health check failed: {e}")
    
    # Overall status
    all_up = all(
        status == "up" 
        for status in health_status["services"].values()
    )
    health_status["status"] = "healthy" if all_up else "degraded"
    
    return health_status


@app.post("/api/v1/vm/deploy", response_model=DeploymentResponse, tags=["VMs"])
async def deploy_vm(request: VMDeployRequest):
    """Deploy a new VM on XenServer"""
    try:
        logger.info(f"Deploying VM: {request.name}")
        
        # 1. Fetch cloud-init template from Gitea
        template_path = f"cloud-init/{request.os_type}/{request.template}.yaml"
        logger.debug(f"Fetching template: {template_path}")
        
        template_content = await gitea_client.get_file_content(template_path)
        
        # 2. Generate final cloud-init configuration
        cloudinit_config = cloudinit_gen.generate(
            template=template_content,
            vm_name=request.name,
            environment=request.environment,
            additional_vars=request.variables or {}
        )
        
        # 3. Create VM on XenServer
        logger.info(f"Creating VM on XenServer: {request.name}")
        vm_ref = await xenserver_client.create_vm(
            name=request.name,
            template=f"{request.os_type}-template",
            cpu=request.cpu,
            memory=request.memory,
            disk=request.disk,
            network=request.network,
            cloudinit_data=cloudinit_config
        )
        
        # 4. Log deployment in database
        deployment_id = await db.log_deployment(
            deployment_type="vm",
            name=request.name,
            config=request.dict(),
            resource_ref=vm_ref,
            status="success"
        )
        
        logger.info(f"VM deployed successfully: {request.name} (ID: {deployment_id})")
        
        return DeploymentResponse(
            success=True,
            deployment_id=deployment_id,
            resource_id=vm_ref,
            message=f"VM {request.name} deployed successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to deploy VM {request.name}: {e}")
        
        # Log failed deployment
        try:
            await db.log_deployment(
                deployment_type="vm",
                name=request.name,
                config=request.dict(),
                status="failed",
                error=str(e)
            )
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy VM: {str(e)}"
        )


@app.post("/api/v1/container/deploy", response_model=DeploymentResponse, tags=["Containers"])
async def deploy_container(request: ContainerDeployRequest):
    """Deploy a new container/service on Docker Swarm"""
    try:
        logger.info(f"Deploying container: {request.name}")
        
        # Deploy service on Docker Swarm
        service_id = await docker_client.create_service(
            name=request.name,
            image=request.image,
            replicas=request.replicas,
            environment=request.environment,
            ports=request.ports,
            networks=request.networks,
            labels=request.labels
        )
        
        # Log deployment in database
        deployment_id = await db.log_deployment(
            deployment_type="container",
            name=request.name,
            config=request.dict(),
            resource_ref=service_id,
            status="success"
        )
        
        logger.info(f"Container deployed successfully: {request.name} (ID: {deployment_id})")
        
        return DeploymentResponse(
            success=True,
            deployment_id=deployment_id,
            resource_id=service_id,
            message=f"Container {request.name} deployed successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to deploy container {request.name}: {e}")
        
        # Log failed deployment
        try:
            await db.log_deployment(
                deployment_type="container",
                name=request.name,
                config=request.dict(),
                status="failed",
                error=str(e)
            )
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy container: {str(e)}"
        )


@app.get("/api/v1/deployments", response_model=DeploymentListResponse, tags=["Deployments"])
async def list_deployments(
    deployment_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50
):
    """List all deployments"""
    try:
        deployments = await db.get_deployments(
            deployment_type=deployment_type,
            status_filter=status_filter,
            limit=limit
        )
        
        return DeploymentListResponse(
            success=True,
            count=len(deployments),
            deployments=deployments
        )
        
    except Exception as e:
        logger.error(f"Failed to list deployments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list deployments: {str(e)}"
        )


@app.get("/api/v1/deployments/{deployment_id}", tags=["Deployments"])
async def get_deployment(deployment_id: int):
    """Get details of a specific deployment"""
    try:
        deployment = await db.get_deployment(deployment_id)
        
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment {deployment_id} not found"
            )
        
        return deployment
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get deployment {deployment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get deployment: {str(e)}"
        )


@app.delete("/api/v1/deployments/{deployment_id}", tags=["Deployments"])
async def delete_deployment(deployment_id: int):
    """Delete a deployment (VM or container)"""
    try:
        # Get deployment info
        deployment = await db.get_deployment(deployment_id)
        
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment {deployment_id} not found"
            )
        
        # Delete resource based on type
        if deployment["type"] == "vm":
            await xenserver_client.delete_vm(deployment["resource_ref"])
        elif deployment["type"] == "container":
            await docker_client.delete_service(deployment["resource_ref"])
        
        # Update database
        await db.update_deployment_status(deployment_id, "deleted")
        
        logger.info(f"Deployment {deployment_id} deleted successfully")
        
        return {
            "success": True,
            "message": f"Deployment {deployment_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete deployment {deployment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete deployment: {str(e)}"
        )
