from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import structlog
import hmac
import hashlib
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from config import settings
from models import GiteaWebhook, HealthCheck, DeploymentStatus
from database import db
from orchestrator import orchestrator
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# Configuration du logging structuré
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Métriques Prometheus
webhook_counter = Counter('webhook_received_total', 'Total webhooks received')
deployment_counter = Counter('deployments_total', 'Total deployments', ['type', 'status'])
deployment_duration = Histogram('deployment_duration_seconds', 'Deployment duration')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application"""
    # Startup
    logger.info("application_starting", version=settings.app_version)
    
    try:
        # Connexion à la base de données
        await db.connect()
        logger.info("database_ready")
    except Exception as e:
        logger.error("startup_failed", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("application_stopping")
    await db.disconnect()


# Création de l'application FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Orchestrateur de déploiement VM et containers via Gitea",
    lifespan=lifespan
)


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Vérifie la signature du webhook Gitea"""
    if not settings.gitea_webhook_secret:
        logger.warning("webhook_secret_not_configured")
        return True  # Accepter si pas de secret configuré
    
    expected_signature = hmac.new(
        settings.gitea_webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


@app.get("/")
async def root():
    """Endpoint racine"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Endpoint de health check"""
    services = {
        "database": False,
        "gitea": False
    }
    
    # Vérifier la connexion DB
    try:
        async with db.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            services["database"] = True
    except:
        pass
    
    # Vérifier Gitea (simple ping)
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{settings.gitea_url}/api/v1/version") as resp:
                if resp.status == 200:
                    services["gitea"] = True
    except:
        pass
    
    health = HealthCheck(
        status="healthy" if all(services.values()) else "degraded",
        version=settings.app_version,
        timestamp=datetime.utcnow(),
        services=services
    )
    
    return health


@app.post("/webhook/gitea")
async def gitea_webhook(
    request: Request,
    x_gitea_signature: Optional[str] = Header(None)
):
    """Endpoint pour recevoir les webhooks Gitea"""
    try:
        # Lire le payload
        payload = await request.body()
        
        # Vérifier la signature
        if x_gitea_signature:
            if not verify_webhook_signature(payload, x_gitea_signature):
                logger.warning("webhook_signature_invalid")
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parser le JSON
        webhook_data = await request.json()
        
        # Incrémenter le compteur
        webhook_counter.inc()
        
        # Traiter le webhook en arrière-plan
        result = await orchestrator.process_webhook(webhook_data)
        
        logger.info("webhook_processed", result=result)
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "accepted",
                "message": "Webhook processed successfully",
                "result": result
            }
        )
        
    except Exception as e:
        logger.error("webhook_processing_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/deployments")
async def list_deployments(
    limit: int = 50,
    status: Optional[str] = None,
    environment: Optional[str] = None
):
    """Liste les déploiements récents"""
    try:
        # Construction de la requête SQL
        conditions = []
        params = []
        param_count = 1
        
        if status:
            conditions.append(f"status = ${param_count}")
            params.append(status)
            param_count += 1
        
        if environment:
            conditions.append(f"environment = ${param_count}")
            params.append(environment)
            param_count += 1
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        query = f"""
        SELECT * FROM deployments
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_count}
        """
        params.append(limit)
        
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            deployments = [dict(row) for row in rows]
        
        return {
            "count": len(deployments),
            "deployments": deployments
        }
        
    except Exception as e:
        logger.error("list_deployments_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/deployments/{deployment_id}")
async def get_deployment(deployment_id: int):
    """Récupère les détails d'un déploiement"""
    try:
        deployment = await db.get_deployment(deployment_id)
        
        if not deployment:
            raise HTTPException(status_code=404, detail="Deployment not found")
        
        # Récupérer les logs
        logs = await db.get_deployment_logs(deployment_id)
        
        return {
            "deployment": deployment,
            "logs": logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_deployment_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def metrics():
    """Endpoint Prometheus metrics"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.post("/deployments/{deployment_id}/rollback")
async def rollback_deployment(deployment_id: int):
    """Rollback d'un déploiement (à implémenter)"""
    # TODO: Implémenter la logique de rollback
    raise HTTPException(status_code=501, detail="Rollback not yet implemented")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.webhook_port,
        log_level=settings.log_level.lower(),
        reload=False
    )
