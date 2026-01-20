import asyncpg
import structlog
from typing import Optional, List
from datetime import datetime
from config import settings
from models import DeploymentRecord, DeploymentStatus, DeploymentType, Environment

logger = structlog.get_logger()


class DatabaseManager:
    """Gestionnaire de base de données PostgreSQL"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Établit la connexion au pool PostgreSQL"""
        try:
            self.pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                database=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
                min_size=2,
                max_size=10
            )
            logger.info("database_connected", host=settings.postgres_host, db=settings.postgres_db)
            await self.init_schema()
        except Exception as e:
            logger.error("database_connection_failed", error=str(e))
            raise
    
    async def disconnect(self):
        """Ferme le pool de connexions"""
        if self.pool:
            await self.pool.close()
            logger.info("database_disconnected")
    
    async def init_schema(self):
        """Initialise le schéma de la base de données"""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS deployments (
            id SERIAL PRIMARY KEY,
            deployment_type VARCHAR(50) NOT NULL,
            name VARCHAR(255) NOT NULL,
            environment VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL,
            git_commit VARCHAR(255) NOT NULL,
            git_branch VARCHAR(255) NOT NULL,
            git_repository VARCHAR(500) NOT NULL,
            config JSONB NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            completed_at TIMESTAMP,
            error_message TEXT,
            rollback_from INTEGER REFERENCES deployments(id)
        );
        
        CREATE INDEX IF NOT EXISTS idx_deployments_status ON deployments(status);
        CREATE INDEX IF NOT EXISTS idx_deployments_environment ON deployments(environment);
        CREATE INDEX IF NOT EXISTS idx_deployments_type ON deployments(deployment_type);
        CREATE INDEX IF NOT EXISTS idx_deployments_created_at ON deployments(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_deployments_name_env ON deployments(name, environment);
        
        CREATE TABLE IF NOT EXISTS deployment_logs (
            id SERIAL PRIMARY KEY,
            deployment_id INTEGER NOT NULL REFERENCES deployments(id) ON DELETE CASCADE,
            timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
            level VARCHAR(20) NOT NULL,
            message TEXT NOT NULL,
            metadata JSONB
        );
        
        CREATE INDEX IF NOT EXISTS idx_deployment_logs_deployment_id ON deployment_logs(deployment_id);
        CREATE INDEX IF NOT EXISTS idx_deployment_logs_timestamp ON deployment_logs(timestamp DESC);
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(schema_sql)
            logger.info("database_schema_initialized")
    
    async def create_deployment(self, record: DeploymentRecord) -> int:
        """Crée un nouvel enregistrement de déploiement"""
        query = """
        INSERT INTO deployments 
        (deployment_type, name, environment, status, git_commit, git_branch, git_repository, config)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """
        
        async with self.pool.acquire() as conn:
            deployment_id = await conn.fetchval(
                query,
                record.deployment_type.value,
                record.name,
                record.environment.value,
                record.status.value,
                record.git_commit,
                record.git_branch,
                record.git_repository,
                record.config
            )
            logger.info("deployment_created", deployment_id=deployment_id, name=record.name)
            return deployment_id
    
    async def update_deployment_status(
        self, 
        deployment_id: int, 
        status: DeploymentStatus,
        error_message: Optional[str] = None
    ):
        """Met à jour le statut d'un déploiement"""
        completed_at = datetime.utcnow() if status in [DeploymentStatus.COMPLETED, DeploymentStatus.FAILED] else None
        
        query = """
        UPDATE deployments 
        SET status = $1, updated_at = $2, completed_at = $3, error_message = $4
        WHERE id = $5
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                query,
                status.value,
                datetime.utcnow(),
                completed_at,
                error_message,
                deployment_id
            )
            logger.info("deployment_status_updated", deployment_id=deployment_id, status=status.value)
    
    async def get_deployment(self, deployment_id: int) -> Optional[dict]:
        """Récupère un déploiement par son ID"""
        query = "SELECT * FROM deployments WHERE id = $1"
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, deployment_id)
            return dict(row) if row else None
    
    async def get_latest_deployment(self, name: str, environment: Environment) -> Optional[dict]:
        """Récupère le dernier déploiement pour un nom et environnement donnés"""
        query = """
        SELECT * FROM deployments 
        WHERE name = $1 AND environment = $2 
        ORDER BY created_at DESC 
        LIMIT 1
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, name, environment.value)
            return dict(row) if row else None
    
    async def add_deployment_log(
        self, 
        deployment_id: int, 
        level: str, 
        message: str,
        metadata: Optional[dict] = None
    ):
        """Ajoute un log pour un déploiement"""
        query = """
        INSERT INTO deployment_logs (deployment_id, level, message, metadata)
        VALUES ($1, $2, $3, $4)
        """
        
        async with self.pool.acquire() as conn:
            await conn.execute(query, deployment_id, level, message, metadata or {})
    
    async def get_deployment_logs(self, deployment_id: int) -> List[dict]:
        """Récupère les logs d'un déploiement"""
        query = """
        SELECT * FROM deployment_logs 
        WHERE deployment_id = $1 
        ORDER BY timestamp ASC
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, deployment_id)
            return [dict(row) for row in rows]


# Instance globale
db = DatabaseManager()
