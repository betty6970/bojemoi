"""Main FastAPI application"""
import asyncio
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
    DeploymentResponse, HealthResponse,
    BlockchainBlock, BlockchainVerifyResponse, BlockListResponse,
    BlockchainStatsResponse,
    Rapid7DeployRequest, Rapid7RegisterRequest,
    Rapid7DeployResponse, Rapid7StatusResponse,
    VulnHubDeployRequest, VulnHubDeployResponse, VulnHubTargetsResponse,
)
from app.services.gitea_client import GiteaClient
from app.services.local_template_client import LocalTemplateClient
from app.services.xenserver_client_real import XenServerClient
from app.services.docker_client import DockerSwarmClient
from app.services.cloudinit_gen import CloudInitGenerator
from app.services.database import Database
from app.services.ip2location_client import IP2LocationClient
from app.services.blockchain import BlockchainService
from app.services.rapid7_manager import Rapid7Manager
from app.services.vulnhub_manager import VulnHubManager, VULNHUB_CATALOG
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
template_client: Optional[LocalTemplateClient] = None
xenserver_client: Optional[XenServerClient] = None
docker_client: Optional[DockerSwarmClient] = None
cloudinit_gen: Optional[CloudInitGenerator] = None
db: Optional[Database] = None
ip2location_client: Optional[IP2LocationClient] = None
blockchain_service: Optional[BlockchainService] = None
rapid7_manager: Optional[Rapid7Manager] = None
vulnhub_manager: Optional[VulnHubManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan (startup and shutdown)"""
    global gitea_client, template_client, xenserver_client, docker_client, cloudinit_gen, db
    global ip2location_client, blockchain_service, rapid7_manager, vulnhub_manager

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

        # Initialize local template client (no Gitea dependency at runtime)
        template_client = LocalTemplateClient(settings.TEMPLATES_DIR)
        logger.info(f"LocalTemplateClient initialized (dir: {settings.TEMPLATES_DIR})")

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

        # Initialize CloudInit generator (uses local templates)
        cloudinit_gen = CloudInitGenerator(template_client)
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

        # Initialize Rapid7 manager (host_debug table in msf DB)
        rapid7_manager = Rapid7Manager(settings.MSF_DB_URL)
        await rapid7_manager.init()
        logger.info("Rapid7Manager initialized (host_debug ready)")

        # Initialize VulnHub manager (same host_debug table, multi-target)
        vulnhub_manager = VulnHubManager(settings.MSF_DB_URL)
        await vulnhub_manager.init()
        logger.info(f"VulnHubManager initialized ({len(VULNHUB_CATALOG)} VMs in catalogue)")

        # Set Prometheus app info
        set_app_info(
            version=settings.API_VERSION,
            environment="production" if not settings.DEBUG else "development"
        )
        logger.info("Prometheus metrics initialized")

        # Make ip2location_client available to IPValidationMiddleware via app.state
        app.state.ip2location_client = ip2location_client
        logger.info(f"IP validation middleware ready (enabled={settings.IP_VALIDATION_ENABLED})")

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

    if rapid7_manager:
        await rapid7_manager.close()

    if vulnhub_manager:
        await vulnhub_manager.close()

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

# Add IP validation middleware at module level (client is set lazily via app.state)
app.add_middleware(
    IPValidationMiddleware,
    ip2location_client=None,
    allowed_countries=settings.ALLOWED_COUNTRIES,
    enabled=settings.IP_VALIDATION_ENABLED
)


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

    # Check XenServer (5s timeout to avoid hanging health check)
    try:
        xenserver_ok = await asyncio.wait_for(xenserver_client.ping(), timeout=5.0)
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

        # 1. Fetch cloud-init template from local filesystem
        template_path = f"cloud-init/{request.os_type.value}/{request.template}.yaml"
        logger.debug(f"Fetching template: {template_path}")

        template_content = await template_client.get_file_content(template_path)

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

        # For alpine, the template has no disk — pass the boot VDI to clone
        boot_vdi = settings.ALPINE_BOOT_VDI_UUID if request.os_type.value == "alpine" else None

        logger.info(f"Creating VM on XenServer: {request.name} (template: {template_name})")
        vm_ref = await xenserver_client.create_vm(
            name=request.name,
            template=template_name,
            cpu=request.cpu,
            memory=request.memory,
            disk=request.disk,
            network=request.network,
            cloudinit_data=cloudinit_config,
            boot_vdi_uuid=boot_vdi
        )

        # 4. Poll for guest IP via XenTools (requires xe-guest-utilities inside the VM)
        vm_ip = None
        if request.ip_poll_timeout > 0:
            logger.info(f"Polling for guest IP (timeout={request.ip_poll_timeout}s)...")
            vm_ip = await _poll_vm_ip(vm_ref, request.ip_poll_timeout)
            if vm_ip:
                logger.info(f"Guest IP detected: {vm_ip}")
            else:
                logger.warning(
                    f"Guest IP not detected after {request.ip_poll_timeout}s "
                    f"— host_debug will store UUID as address"
                )

        # 5. Log deployment in blockchain
        block = await blockchain_service.create_block(
            deployment_type="vm",
            name=request.name,
            config=request.dict(),
            resource_ref=vm_ref,
            status="success",
            source_ip=source_ip,
            source_country=source_country
        )

        # Register in host_debug — use real IP if available, fall back to UUID
        host_address = vm_ip or vm_ref
        host_id = await db.register_host(
            address=host_address,
            vm_name=request.name,
            vm_uuid=vm_ref,
        )

        # Record success metrics
        duration = time.time() - start_time
        record_deployment("vm", "success", request.environment.value, duration)

        ip_info_str = f", IP={vm_ip}" if vm_ip else ", IP=pending (XenTools not ready)"
        logger.info(f"VM deployed successfully: {request.name} (block: #{block['block_number']}{ip_info_str})")

        return DeploymentResponse(
            success=True,
            deployment_id=host_id,
            resource_id=vm_ref,
            ip_address=vm_ip,
            message=f"VM {request.name} deployed successfully (block #{block['block_number']}{ip_info_str})"
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

        # Record success metrics
        duration = time.time() - start_time
        record_deployment("container", "success", "production", duration)

        logger.info(f"Container deployed successfully: {request.name} (block: #{block['block_number']}, hash: {block['current_hash'][:16]}...)")

        return DeploymentResponse(
            success=True,
            deployment_id=0,
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

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy container: {str(e)}"
        )



# ---------------------------------------------------------------------------
# Rapid7 Debug VM
# ---------------------------------------------------------------------------

async def _poll_vm_ip(vm_uuid: str, timeout: int) -> Optional[str]:
    """Interroge XenServer jusqu'à obtenir une IP guest (via XenTools).

    Retourne l'IP ou None si le timeout est dépassé.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            info = await xenserver_client.get_vm_info(vm_uuid)
            networks = info.get("guest_metrics", {}).get("networks", {})
            # XenAPI retourne {"0/ip": "192.168.x.x", ...}
            ip = networks.get("0/ip") or networks.get("1/ip")
            if ip:
                return ip
        except Exception:
            pass
        await asyncio.sleep(5)
    return None


@app.post("/api/v1/vm/rapid7", response_model=Rapid7DeployResponse, tags=["Rapid7 Debug"])
async def deploy_rapid7_vm(request: Rapid7DeployRequest, req: Request):
    """Déploie la VM Rapid7 (Metasploitable) sur XenServer.

    - Clone le template XenServer indiqué (sans cloud-init)
    - Attend l'IP guest via XenTools (poll jusqu'à ip_poll_timeout secondes)
    - Si IP obtenue : enregistre dans host_debug (msf DB) et remplace toute entrée précédente
    - Si IP non obtenue : retourne le vm_uuid pour enregistrement manuel via /register
    """
    ip_info = get_request_ip_info(req)
    start_time = time.time()

    try:
        logger.info(f"Déploiement VM Rapid7 '{request.vm_name}' depuis template '{request.xen_template}'")

        vm_uuid = await xenserver_client.create_vm(
            name=request.vm_name,
            template=request.xen_template,
            cpu=request.cpu,
            memory=request.memory_mb,
            disk=request.disk_gb,
            network=request.network,
            cloudinit_data=None,
        )
        logger.info(f"VM Rapid7 créée : {vm_uuid}")

        # Attendre l'IP
        ip = await _poll_vm_ip(vm_uuid, request.ip_poll_timeout)

        registered = False
        if ip:
            await rapid7_manager.replace_host(
                address=ip,
                vm_name=request.vm_name,
                vm_uuid=vm_uuid,
            )
            registered = True
            logger.info(f"host_debug mis à jour : {ip} ({request.vm_name})")
        else:
            logger.warning(
                f"IP non détectée après {request.ip_poll_timeout}s "
                f"— appelez POST /api/v1/vm/rapid7/register avec vm_uuid={vm_uuid}"
            )

        # Audit blockchain
        await blockchain_service.create_block(
            deployment_type="vm",
            name=request.vm_name,
            config={**request.dict(), "xen_uuid": vm_uuid, "ip": ip},
            resource_ref=vm_uuid,
            status="success",
            source_ip=ip_info.get("source_ip"),
            source_country=ip_info.get("source_country"),
        )

        duration = time.time() - start_time
        record_deployment("vm", "success", "dev", duration)

        msg = (
            f"VM {request.vm_name} déployée ({vm_uuid}), IP={ip}, host_debug enregistré."
            if registered
            else f"VM {request.vm_name} déployée ({vm_uuid}), IP non encore disponible — enregistrement manuel requis."
        )
        return Rapid7DeployResponse(
            success=True,
            vm_uuid=vm_uuid,
            ip_address=ip,
            host_debug_registered=registered,
            message=msg,
        )

    except Exception as e:
        duration = time.time() - start_time
        record_deployment("vm", "failed", "dev", duration)
        record_deployment_error("vm", type(e).__name__)
        logger.error(f"Échec déploiement Rapid7 VM : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Échec déploiement VM Rapid7 : {e}",
        )


@app.post("/api/v1/vm/rapid7/register", response_model=Rapid7DeployResponse, tags=["Rapid7 Debug"])
async def register_rapid7_ip(request: Rapid7RegisterRequest):
    """Enregistre manuellement une IP dans host_debug.

    À utiliser si l'IP n'a pas été détectée automatiquement lors du déploiement,
    ou pour pointer uzi-debug vers une VM existante.
    """
    try:
        record = await rapid7_manager.replace_host(
            address=request.ip_address,
            vm_name=request.vm_name,
        )
        logger.info(f"host_debug mis à jour manuellement : {request.ip_address}")
        return Rapid7DeployResponse(
            success=True,
            ip_address=record["address"],
            host_debug_registered=True,
            message=f"IP {request.ip_address} enregistrée dans host_debug.",
        )
    except Exception as e:
        logger.error(f"Erreur register_rapid7_ip : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@app.get("/api/v1/vm/rapid7/status", response_model=Rapid7StatusResponse, tags=["Rapid7 Debug"])
async def rapid7_status():
    """Retourne l'état courant de la VM Rapid7 de debug.

    - Contenu de host_debug (IP cible pour uzi en mode DEBUG_MODE=1)
    - Info XenServer sur la VM si vm_uuid connu
    """
    host = await rapid7_manager.get_host()
    vm_uuid = host.get("vm_uuid") if host else None
    vm_power_state = None

    if vm_uuid:
        try:
            info = await xenserver_client.get_vm_info(vm_uuid)
            vm_power_state = info.get("power_state")
        except Exception:
            vm_power_state = "unknown"

    if host:
        # Convertir datetime en str pour la sérialisation
        host = {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in host.items()}

    return Rapid7StatusResponse(
        host_debug=host,
        vm_uuid=vm_uuid,
        vm_power_state=vm_power_state,
        message="OK" if host else "Aucun hôte debug enregistré (host_debug vide).",
    )


# ─── VulnHub VM Deployment ────────────────────────────────────────────────────

@app.get("/api/v1/vm/vulnhub/catalog", tags=["VulnHub"])
async def vulnhub_catalog():
    """Retourne le catalogue des VMs VulnHub disponibles.

    Les VMs doivent être pré-importées comme templates XenServer.
    Utiliser scripts/import_vulnhub_ova.sh sur l'hôte XenServer pour l'import initial.
    """
    return {
        "catalog": [
            {"vm_id": vm_id, **entry}
            for vm_id, entry in VULNHUB_CATALOG.items()
        ],
        "total": len(VULNHUB_CATALOG),
        "note": "Chaque VM nécessite un template XenServer pré-importé (champ xen_template).",
    }


@app.get("/api/v1/vm/vulnhub/targets", response_model=VulnHubTargetsResponse, tags=["VulnHub"])
async def vulnhub_targets():
    """Retourne les VMs VulnHub actives dans host_debug (cibles bm12/uzi)."""
    targets = await vulnhub_manager.list_targets()
    serialized = [
        {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in t.items()}
        for t in targets
    ]
    return VulnHubTargetsResponse(targets=serialized, total=len(serialized))


@app.post("/api/v1/vm/vulnhub/{vm_id}", response_model=VulnHubDeployResponse, tags=["VulnHub"])
async def deploy_vulnhub_vm(vm_id: str, request: VulnHubDeployRequest, req: Request):
    """Déploie une VM VulnHub depuis le catalogue.

    - Vérifie la présence du vm_id dans le catalogue
    - Clone le template XenServer correspondant (sans cloud-init)
    - Démarre la VM, détecte l'IP via XenTools
    - Ajoute à host_debug pour ciblage par bm12/uzi (DEBUG_MODE=1)
    - Enregistre dans l'audit blockchain

    Prérequis : template XenServer importé (cf. scripts/import_vulnhub_ova.sh).
    """
    entry = VULNHUB_CATALOG.get(vm_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VM '{vm_id}' absente du catalogue. Disponibles : {list(VULNHUB_CATALOG.keys())}",
        )

    ip_info = get_request_ip_info(req)
    start_time = time.time()
    vm_name = f"vulnhub-{vm_id}"
    xen_template = entry["xen_template"]
    cpu = request.cpu_override or entry["cpu"]
    memory_mb = request.memory_mb_override or entry["memory_mb"]
    disk_gb = entry["disk_gb"]

    try:
        logger.info(f"Déploiement VulnHub VM '{vm_name}' depuis template '{xen_template}'")

        vm_uuid = await xenserver_client.create_vm(
            name=vm_name,
            template=xen_template,
            cpu=cpu,
            memory=memory_mb,
            disk=disk_gb,
            network=request.network,
            cloudinit_data=None,
        )
        logger.info(f"VM VulnHub créée : {vm_uuid}")

        ip = await _poll_vm_ip(vm_uuid, request.ip_poll_timeout)

        registered = False
        if ip:
            await vulnhub_manager.add_target(
                address=ip,
                vm_name=vm_name,
                vm_uuid=vm_uuid,
            )
            registered = True
            logger.info(f"host_debug ajouté : {ip} ({vm_name})")
        else:
            logger.warning(
                f"IP non détectée après {request.ip_poll_timeout}s "
                f"— enregistrement manuel via POST /api/v1/vm/rapid7/register"
            )

        await blockchain_service.create_block(
            deployment_type="vm",
            name=vm_name,
            config={**request.dict(), "vm_id": vm_id, "xen_uuid": vm_uuid, "ip": ip,
                    "known_vulns": entry["known_vulns"]},
            resource_ref=vm_uuid,
            status="success",
            source_ip=ip_info.get("source_ip"),
            source_country=ip_info.get("source_country"),
        )

        duration = time.time() - start_time
        record_deployment("vm", "success", "dev", duration)

        msg = (
            f"VM {vm_name} déployée ({vm_uuid}), IP={ip}, ajoutée à host_debug."
            if registered
            else f"VM {vm_name} déployée ({vm_uuid}), IP non disponible — enregistrement manuel requis."
        )
        return VulnHubDeployResponse(
            success=True,
            vm_id=vm_id,
            vm_uuid=vm_uuid,
            ip_address=ip,
            host_debug_registered=registered,
            known_vulns=entry["known_vulns"],
            message=msg,
        )

    except Exception as e:
        duration = time.time() - start_time
        record_deployment("vm", "failed", "dev", duration)
        record_deployment_error("vm", type(e).__name__)
        logger.error(f"Échec déploiement VulnHub VM '{vm_id}' : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Échec déploiement VM VulnHub '{vm_id}' : {e}",
        )


@app.delete("/api/v1/vm/vulnhub/{vm_id}", tags=["VulnHub"])
async def delete_vulnhub_vm(vm_id: str):
    """Arrête une VM VulnHub et la retire de host_debug.

    - Récupère le vm_uuid depuis host_debug
    - Arrête et supprime la VM XenServer
    - Supprime l'entrée host_debug correspondante
    """
    vm_name = f"vulnhub-{vm_id}"
    targets = await vulnhub_manager.list_targets()
    target = next((t for t in targets if t.get("vm_name") == vm_name), None)

    vm_uuid = target.get("vm_uuid") if target else None

    deleted_vm = False
    if vm_uuid:
        try:
            await xenserver_client.delete_vm(vm_uuid, force=True)
            deleted_vm = True
            logger.info(f"VM XenServer supprimée : {vm_uuid}")
        except Exception as e:
            logger.warning(f"Impossible de supprimer la VM XenServer {vm_uuid} : {e}")

    removed = await vulnhub_manager.remove_target_by_name(vm_name)
    logger.info(f"host_debug : {removed} entrée(s) supprimée(s) pour '{vm_name}'")

    return {
        "success": True,
        "vm_id": vm_id,
        "vm_uuid": vm_uuid,
        "vm_deleted": deleted_vm,
        "host_debug_removed": removed,
        "message": f"VM '{vm_name}' supprimée{'  (XenServer + host_debug)' if deleted_vm else ' (host_debug uniquement — VM XenServer introuvable)'}.",
    }


@app.get("/api/v1/hosts", tags=["Hosts"])
async def list_hosts(limit: int = 50):
    """List all registered hosts in host_debug"""
    try:
        hosts = await db.get_hosts(limit=limit)
        serialized = [
            {k: (str(v) if hasattr(v, "isoformat") else v) for k, v in h.items()}
            for h in hosts
        ]
        return {"success": True, "count": len(serialized), "hosts": serialized}
    except Exception as e:
        logger.error(f"Failed to list hosts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list hosts: {str(e)}"
        )


@app.delete("/api/v1/hosts/{address}", tags=["Hosts"])
async def delete_host(address: str):
    """Remove a host from host_debug"""
    try:
        removed = await db.delete_host(address)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Host {address} not found"
            )
        return {"success": True, "message": f"Host {address} removed from host_debug"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete host {address}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete host: {str(e)}"
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
        templates = await template_client.list_templates(os_type)

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
        content = await template_client.get_template(os_type, template_name)

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
        scripts = await template_client.list_common_scripts()

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
        content = await template_client.get_common_script(script_name)

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
    """Clear the template cache (no-op for local templates, kept for API compatibility)."""
    try:
        template_client.clear_cache()

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
