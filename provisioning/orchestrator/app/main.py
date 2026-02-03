"""Main FastAPI application"""
import time
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import Optional, List
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from app.config import settings
from app.models.schemas import (
    VMDeployRequest, ContainerDeployRequest,
    DeploymentResponse, HealthResponse, DeploymentListResponse,
    BlockchainBlock, BlockchainVerifyResponse, BlockListResponse,
    BlockchainStatsResponse
)
from app.services.gitea_client import GiteaClient
from app.services.xenserver_client_real import XenServerClient
from app.services.docker_client import DockerSwarmClient
from app.services.cloudinit_gen import CloudInitGenerator
from app.services.database import Database
from app.services.ip2location_client import IP2LocationClient
from app.services.blockchain import BlockchainService
from app.middleware.ip_validation import IPValidationMiddleware, get_request_ip_info
from app.middleware.metrics import MetricsMiddleware
from app.metrics import (
    set_app_info,
    get_metrics,
    get_metrics_content_type,
    record_deployment,
    record_deployment_error,
    update_service_health,
    update_blockchain_metrics,
    track_duration,
    deployment_duration,
)

# XenServer template mapping (os_type -> actual template name)
XENSERVER_TEMPLATES = {
    "alpine": "alpine-meta",
    "ubuntu": "ubuntu cloud",
    "ubuntu-20": "Ubuntu Focal Fossa 20.04",
    "ubuntu-22": "Ubuntu Jammy Jellyfish 22.04",
    "ubuntu-24": "ubuntu 24.x",
    "debian": "Debian Bullseye 11",
    "debian-12": "Debian Bookworm 12",
    "debian-11": "Debian Bullseye 11",
    "centos": "CentOS 7",
    "rocky": "Rocky Linux 8",
}

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
ip2location_client: Optional[IP2LocationClient] = None
blockchain_service: Optional[BlockchainService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup and shutdown)"""
    global gitea_client, xenserver_client, docker_client, cloudinit_gen, db
    global ip2location_client, blockchain_service

    # Startup
    logger.info("Initializing Bojemoi Orchestrator...")

    try:
        # Initialize Gitea client
        gitea_client = GiteaClient(
            base_url=settings.GITEA_URL,
            token=settings.GITEA_TOKEN,
            repo=settings.GITEA_REPO,
            owner=settings.GITEA_REPO_OWNER,
            cache_ttl=300  # 5 minute cache for templates
        )
        logger.info(f"Gitea client initialized (repo: {settings.GITEA_REPO_OWNER}/{settings.GITEA_REPO})")

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

        # Initialize IP2Location client
        ip2location_client = IP2LocationClient(settings.IP2LOCATION_DB_URL)
        await ip2location_client.init()
        logger.info("IP2Location client initialized")

        # Initialize Blockchain service
        blockchain_service = BlockchainService(settings.KARACHO_DB_URL)
        await blockchain_service.init()
        logger.info("Blockchain service initialized")

        # Set Prometheus app info
        set_app_info(
            version=settings.API_VERSION,
            environment="production" if not settings.DEBUG else "development"
        )
        logger.info("Prometheus metrics initialized")

        # Add IP validation middleware
        app.add_middleware(
            IPValidationMiddleware,
            ip2location_client=ip2location_client,
            allowed_countries=settings.ALLOWED_COUNTRIES,
            enabled=settings.IP_VALIDATION_ENABLED
        )
        logger.info(f"IP validation middleware added (enabled={settings.IP_VALIDATION_ENABLED})")

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

    if ip2location_client:
        await ip2location_client.close()

    if blockchain_service:
        await blockchain_service.close()

    logger.info("Shutdown complete")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan
)

# Add CORS middleware with restricted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)


@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "service": "Bojemoi Orchestrator",
        "version": settings.API_VERSION,
        "status": "running"
    }


@app.get("/metrics", tags=["Monitoring"], include_in_schema=False)
async def metrics():
    """Prometheus metrics endpoint.

    Returns metrics in Prometheus text format for scraping.
    This endpoint is excluded from OpenAPI schema.
    """
    return Response(
        content=get_metrics(),
        media_type=get_metrics_content_type()
    )


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
        update_service_health("gitea", gitea_ok)
    except Exception as e:
        health_status["services"]["gitea"] = "down"
        update_service_health("gitea", False)
        logger.error(f"Gitea health check failed: {e}")

    # Check XenServer
    try:
        xenserver_ok = await xenserver_client.ping()
        health_status["services"]["xenserver"] = "up" if xenserver_ok else "down"
        update_service_health("xenserver", xenserver_ok)
    except Exception as e:
        health_status["services"]["xenserver"] = "down"
        update_service_health("xenserver", False)
        logger.error(f"XenServer health check failed: {e}")

    # Check Docker Swarm
    try:
        docker_ok = await docker_client.ping()
        health_status["services"]["docker_swarm"] = "up" if docker_ok else "down"
        update_service_health("docker_swarm", docker_ok)
    except Exception as e:
        health_status["services"]["docker_swarm"] = "down"
        update_service_health("docker_swarm", False)
        logger.error(f"Docker Swarm health check failed: {e}")

    # Check Database
    try:
        db_ok = await db.ping()
        health_status["services"]["database"] = "up" if db_ok else "down"
        update_service_health("database", db_ok)
    except Exception as e:
        health_status["services"]["database"] = "down"
        update_service_health("database", False)
        logger.error(f"Database health check failed: {e}")

    # Check IP2Location database
    try:
        ip2loc_ok = await ip2location_client.ping()
        health_status["services"]["ip2location"] = "up" if ip2loc_ok else "down"
        update_service_health("ip2location", ip2loc_ok)
    except Exception as e:
        health_status["services"]["ip2location"] = "down"
        update_service_health("ip2location", False)
        logger.error(f"IP2Location health check failed: {e}")

    # Check Blockchain database
    try:
        blockchain_ok = await blockchain_service.ping()
        health_status["services"]["blockchain"] = "up" if blockchain_ok else "down"
        update_service_health("blockchain", blockchain_ok)

        # Update blockchain metrics
        if blockchain_ok:
            block_count = await blockchain_service.count_blocks()
            update_blockchain_metrics(block_count, True)
    except Exception as e:
        health_status["services"]["blockchain"] = "down"
        update_service_health("blockchain", False)
        logger.error(f"Blockchain health check failed: {e}")

    # Overall status
    all_up = all(
        status == "up"
        for status in health_status["services"].values()
    )
    health_status["status"] = "healthy" if all_up else "degraded"

    return health_status


@app.post("/api/v1/vm/deploy", response_model=DeploymentResponse, tags=["VMs"])
async def deploy_vm(request: VMDeployRequest, req: Request):
    """Deploy a new VM on XenServer"""
    # Get IP info from middleware
    ip_info = get_request_ip_info(req)
    source_ip = ip_info.get("source_ip")
    source_country = ip_info.get("source_country")

    start_time = time.time()

    try:
        logger.info(f"Deploying VM: {request.name} (from IP: {source_ip}, country: {source_country})")

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
        # Get template name from mapping
        template_name = XENSERVER_TEMPLATES.get(request.os_type)
        if not template_name:
            raise ValueError(f"Unknown os_type: {request.os_type}. Available: {list(XENSERVER_TEMPLATES.keys())}")

        logger.info(f"Creating VM on XenServer: {request.name} (template: {template_name})")
        vm_ref = await xenserver_client.create_vm(
            name=request.name,
            template=template_name,
            cpu=request.cpu,
            memory=request.memory,
            disk=request.disk,
            network=request.network,
            cloudinit_data=cloudinit_config
        )

        # 4. Log deployment in blockchain
        block = await blockchain_service.create_block(
            deployment_type="vm",
            name=request.name,
            config=request.dict(),
            resource_ref=vm_ref,
            status="success",
            source_ip=source_ip,
            source_country=source_country
        )

        # Also log in legacy database for backwards compatibility
        deployment_id = await db.log_deployment(
            deployment_type="vm",
            name=request.name,
            config=request.dict(),
            resource_ref=vm_ref,
            status="success"
        )

        # Record success metrics
        duration = time.time() - start_time
        record_deployment("vm", "success", request.environment.value, duration)

        logger.info(f"VM deployed successfully: {request.name} (block: #{block['block_number']}, hash: {block['current_hash'][:16]}...)")

        return DeploymentResponse(
            success=True,
            deployment_id=deployment_id,
            resource_id=vm_ref,
            message=f"VM {request.name} deployed successfully (block #{block['block_number']})"
        )

    except Exception as e:
        # Record failure metrics
        duration = time.time() - start_time
        record_deployment("vm", "failed", request.environment.value, duration)
        record_deployment_error("vm", type(e).__name__)

        logger.error(f"Failed to deploy VM {request.name}: {e}")

        # Log failed deployment in blockchain
        try:
            await blockchain_service.create_block(
                deployment_type="vm",
                name=request.name,
                config=request.dict(),
                status="failed",
                error=str(e),
                source_ip=source_ip,
                source_country=source_country
            )
        except Exception as blockchain_err:
            logger.error(f"Failed to log VM deployment failure to blockchain: {blockchain_err}")

        # Also log in legacy database
        try:
            await db.log_deployment(
                deployment_type="vm",
                name=request.name,
                config=request.dict(),
                status="failed",
                error=str(e)
            )
        except Exception as db_err:
            logger.error(f"Failed to log VM deployment failure to database: {db_err}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy VM: {str(e)}"
        )


@app.post("/api/v1/container/deploy", response_model=DeploymentResponse, tags=["Containers"])
async def deploy_container(request: ContainerDeployRequest, req: Request):
    """Deploy a new container/service on Docker Swarm"""
    # Get IP info from middleware
    ip_info = get_request_ip_info(req)
    source_ip = ip_info.get("source_ip")
    source_country = ip_info.get("source_country")

    start_time = time.time()

    try:
        logger.info(f"Deploying container: {request.name} (from IP: {source_ip}, country: {source_country})")

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

        # Log deployment in blockchain
        block = await blockchain_service.create_block(
            deployment_type="container",
            name=request.name,
            config=request.dict(),
            resource_ref=service_id,
            status="success",
            source_ip=source_ip,
            source_country=source_country
        )

        # Also log in legacy database for backwards compatibility
        deployment_id = await db.log_deployment(
            deployment_type="container",
            name=request.name,
            config=request.dict(),
            resource_ref=service_id,
            status="success"
        )

        # Record success metrics
        duration = time.time() - start_time
        record_deployment("container", "success", "production", duration)

        logger.info(f"Container deployed successfully: {request.name} (block: #{block['block_number']}, hash: {block['current_hash'][:16]}...)")

        return DeploymentResponse(
            success=True,
            deployment_id=deployment_id,
            resource_id=service_id,
            message=f"Container {request.name} deployed successfully (block #{block['block_number']})"
        )

    except Exception as e:
        # Record failure metrics
        duration = time.time() - start_time
        record_deployment("container", "failed", "production", duration)
        record_deployment_error("container", type(e).__name__)

        logger.error(f"Failed to deploy container {request.name}: {e}")

        # Log failed deployment in blockchain
        try:
            await blockchain_service.create_block(
                deployment_type="container",
                name=request.name,
                config=request.dict(),
                status="failed",
                error=str(e),
                source_ip=source_ip,
                source_country=source_country
            )
        except Exception as blockchain_err:
            logger.error(f"Failed to log container deployment failure to blockchain: {blockchain_err}")

        # Also log in legacy database
        try:
            await db.log_deployment(
                deployment_type="container",
                name=request.name,
                config=request.dict(),
                status="failed",
                error=str(e)
            )
        except Exception as db_err:
            logger.error(f"Failed to log container deployment failure to database: {db_err}")

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


# Blockchain endpoints

@app.get("/api/v1/blockchain/blocks", response_model=BlockListResponse, tags=["Blockchain"])
async def list_blocks(
    deployment_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List blockchain blocks with optional filtering"""
    try:
        blocks = await blockchain_service.get_blocks(
            deployment_type=deployment_type,
            status_filter=status_filter,
            limit=limit,
            offset=offset
        )

        return BlockListResponse(
            success=True,
            count=len(blocks),
            blocks=blocks
        )

    except Exception as e:
        logger.error(f"Failed to list blocks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list blocks: {str(e)}"
        )


@app.get("/api/v1/blockchain/blocks/{block_number}", response_model=BlockchainBlock, tags=["Blockchain"])
async def get_block(block_number: int):
    """Get a specific block by number"""
    try:
        block = await blockchain_service.get_block_by_number(block_number)

        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Block #{block_number} not found"
            )

        return block

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get block #{block_number}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get block: {str(e)}"
        )


@app.get("/api/v1/blockchain/verify", response_model=BlockchainVerifyResponse, tags=["Blockchain"])
async def verify_blockchain():
    """Verify blockchain integrity"""
    try:
        result = await blockchain_service.verify_chain_integrity()
        return BlockchainVerifyResponse(**result)

    except Exception as e:
        logger.error(f"Failed to verify blockchain: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify blockchain: {str(e)}"
        )


@app.get("/api/v1/blockchain/latest", response_model=BlockchainBlock, tags=["Blockchain"])
async def get_latest_block():
    """Get the latest block in the chain"""
    try:
        block = await blockchain_service.get_last_block()

        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blockchain is empty"
            )

        return block

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get latest block: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get latest block: {str(e)}"
        )


@app.get("/api/v1/blockchain/stats", response_model=BlockchainStatsResponse, tags=["Blockchain"])
async def get_blockchain_stats():
    """Get blockchain statistics including deployment counts and chain health"""
    try:
        stats = await blockchain_service.get_chain_stats()

        if "error" in stats:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=stats["error"]
            )

        return BlockchainStatsResponse(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get blockchain stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get blockchain stats: {str(e)}"
        )


@app.get("/api/v1/blockchain/history/{name}", tags=["Blockchain"])
async def get_deployment_history(name: str):
    """Get all blockchain records for a specific deployment name"""
    try:
        blocks = await blockchain_service.get_blocks_by_name(name)

        return {
            "success": True,
            "name": name,
            "count": len(blocks),
            "blocks": blocks
        }

    except Exception as e:
        logger.error(f"Failed to get deployment history for {name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get deployment history: {str(e)}"
        )


# Template endpoints

@app.get("/api/v1/templates", tags=["Templates"])
async def list_templates(os_type: Optional[str] = None):
    """List available cloud-init templates.

    Args:
        os_type: Filter by OS type (alpine, ubuntu, debian), or omit for all
    """
    try:
        templates = await gitea_client.list_templates(os_type)

        return {
            "success": True,
            "templates": templates,
            "total": sum(len(t) for t in templates.values())
        }

    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list templates: {str(e)}"
        )


@app.get("/api/v1/templates/{os_type}/{template_name}", tags=["Templates"])
async def get_template(os_type: str, template_name: str):
    """Get a specific cloud-init template.

    Args:
        os_type: Operating system type (alpine, ubuntu, debian)
        template_name: Template name (without .yaml extension)
    """
    try:
        content = await gitea_client.get_template(os_type, template_name)

        return {
            "success": True,
            "os_type": os_type,
            "template_name": template_name,
            "content": content
        }

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template not found: {os_type}/{template_name}"
        )
    except Exception as e:
        logger.error(f"Failed to get template {os_type}/{template_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get template: {str(e)}"
        )


@app.get("/api/v1/templates/scripts", tags=["Templates"])
async def list_common_scripts():
    """List available common scripts for cloud-init."""
    try:
        scripts = await gitea_client.list_common_scripts()

        return {
            "success": True,
            "scripts": scripts,
            "total": len(scripts)
        }

    except Exception as e:
        logger.error(f"Failed to list common scripts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list scripts: {str(e)}"
        )


@app.get("/api/v1/templates/scripts/{script_name}", tags=["Templates"])
async def get_common_script(script_name: str):
    """Get a common script by name.

    Args:
        script_name: Script name (with or without .sh extension)
    """
    try:
        content = await gitea_client.get_common_script(script_name)

        return {
            "success": True,
            "script_name": script_name,
            "content": content
        }

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Script not found: {script_name}"
        )
    except Exception as e:
        logger.error(f"Failed to get script {script_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get script: {str(e)}"
        )


@app.post("/api/v1/templates/cache/clear", tags=["Templates"])
async def clear_template_cache():
    """Clear the template cache to force fresh fetches from Gitea."""
    try:
        gitea_client.clear_cache()

        return {
            "success": True,
            "message": "Template cache cleared"
        }

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )
