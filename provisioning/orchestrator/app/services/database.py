"""Database service — registers VMs in host_debug (msf DB)"""
import asyncpg
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL client for host_debug table in msf DB."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool = None

    async def init_db(self):
        """Initialize database connection pool"""
        try:
            logger.info("Initializing database connection pool...")
            self.pool = await asyncpg.create_pool(
                self.database_url, min_size=2, max_size=10
            )
            await self._create_tables()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def _create_tables(self):
        """Create host_debug table if not exists"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS host_debug (
                    id SERIAL PRIMARY KEY,
                    address VARCHAR(255) NOT NULL UNIQUE,
                    vm_name VARCHAR(255),
                    vm_uuid VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            logger.info("host_debug table ready")

    async def register_host(
        self,
        address: str,
        vm_name: Optional[str] = None,
        vm_uuid: Optional[str] = None,
    ) -> int:
        """Register a VM IP in host_debug. Upsert on address."""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    INSERT INTO host_debug (address, vm_name, vm_uuid)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (address) DO UPDATE SET
                        vm_name = EXCLUDED.vm_name,
                        vm_uuid = EXCLUDED.vm_uuid,
                        updated_at = NOW()
                    RETURNING id
                ''', address, vm_name, vm_uuid)
                host_id = row['id']
                logger.info(f"Registered host: {address} (id={host_id})")
                return host_id
        except Exception as e:
            logger.error(f"Failed to register host: {e}")
            raise

    async def get_host(self, address: str) -> Optional[Dict[str, Any]]:
        """Get host by address"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT * FROM host_debug WHERE address = $1', address
                )
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get host: {e}")
            raise

    async def get_hosts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List all registered hosts"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    'SELECT * FROM host_debug ORDER BY created_at DESC LIMIT $1',
                    limit,
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to get hosts: {e}")
            raise

    async def delete_host(self, address: str) -> bool:
        """Remove a host from host_debug"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    'DELETE FROM host_debug WHERE address = $1', address
                )
                return result == 'DELETE 1'
        except Exception as e:
            logger.error(f"Failed to delete host: {e}")
            raise

    async def ping(self) -> bool:
        """Check database connection"""
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
