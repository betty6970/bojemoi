"""Database service for logging deployments"""
import asyncpg
import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL database client"""
    
    def __init__(self, database_url: str):
        """
        Initialize database client
        
        Args:
            database_url: PostgreSQL connection URL
        """
        self.database_url = database_url
        self.pool = None
    
    async def init_db(self):
        """Initialize database connection pool"""
        try:
            logger.info("Initializing database connection pool...")
            
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10
            )
            
            # Create tables if they don't exist
            await self._create_tables()
            
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def _create_tables(self):
        """Create database tables"""
        async with self.pool.acquire() as conn:
            # Deployments table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS deployments (
                    id SERIAL PRIMARY KEY,
                    type VARCHAR(50) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    config JSONB NOT NULL,
                    resource_ref VARCHAR(255),
                    status VARCHAR(50) NOT NULL,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index on type and status
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_deployments_type 
                ON deployments(type)
            ''')
            
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_deployments_status 
                ON deployments(status)
            ''')
            
            logger.info("Database tables created/verified")
    
    async def log_deployment(
        self,
        deployment_type: str,
        name: str,
        config: Dict[str, Any],
        resource_ref: Optional[str] = None,
        status: str = "pending",
        error: Optional[str] = None
    ) -> int:
        """
        Log a deployment
        
        Args:
            deployment_type: Type of deployment (vm, container)
            name: Deployment name
            config: Configuration dict
            resource_ref: Resource reference (VM ref, service ID)
            status: Deployment status
            error: Error message if failed
        
        Returns:
            Deployment ID
        """
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    INSERT INTO deployments 
                    (type, name, config, resource_ref, status, error)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                ''', deployment_type, name, json.dumps(config), 
                    resource_ref, status, error)
                
                deployment_id = row['id']
                logger.info(f"Logged deployment: {deployment_id}")
                
                return deployment_id
                
        except Exception as e:
            logger.error(f"Failed to log deployment: {e}")
            raise
    
    async def update_deployment_status(
        self,
        deployment_id: int,
        status: str,
        error: Optional[str] = None
    ):
        """
        Update deployment status
        
        Args:
            deployment_id: Deployment ID
            status: New status
            error: Error message if failed
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute('''
                    UPDATE deployments 
                    SET status = $1, error = $2, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $3
                ''', status, error, deployment_id)
                
                logger.info(f"Updated deployment {deployment_id} status to {status}")
                
        except Exception as e:
            logger.error(f"Failed to update deployment status: {e}")
            raise
    
    async def get_deployment(self, deployment_id: int) -> Optional[Dict[str, Any]]:
        """
        Get deployment by ID
        
        Args:
            deployment_id: Deployment ID
        
        Returns:
            Deployment record or None
        """
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT * FROM deployments WHERE id = $1
                ''', deployment_id)
                
                if row:
                    return dict(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get deployment: {e}")
            raise
    
    async def get_deployments(
        self,
        deployment_type: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get deployments with optional filtering
        
        Args:
            deployment_type: Filter by type (vm, container)
            status_filter: Filter by status
            limit: Maximum number of records
        
        Returns:
            List of deployment records
        """
        try:
            async with self.pool.acquire() as conn:
                query = 'SELECT * FROM deployments WHERE 1=1'
                params = []
                param_count = 1
                
                if deployment_type:
                    query += f' AND type = ${param_count}'
                    params.append(deployment_type)
                    param_count += 1
                
                if status_filter:
                    query += f' AND status = ${param_count}'
                    params.append(status_filter)
                    param_count += 1
                
                query += f' ORDER BY created_at DESC LIMIT ${param_count}'
                params.append(limit)
                
                rows = await conn.fetch(query, *params)
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get deployments: {e}")
            raise
    
    async def ping(self) -> bool:
        """
        Check database connection
        
        Returns:
            True if connected, False otherwise
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
                return True
                
        except Exception as e:
            logger.error(f"Database ping failed: {e}")
            return False
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
