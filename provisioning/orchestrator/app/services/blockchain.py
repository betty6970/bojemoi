"""Blockchain service for immutable deployment logging"""
import asyncpg
import hashlib
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class BlockchainService:
    """Service for managing blockchain-based deployment records in karacho database"""

    def __init__(self, database_url: str):
        """
        Initialize blockchain service

        Args:
            database_url: PostgreSQL connection URL to karacho database
        """
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def init(self):
        """Initialize connection pool and create tables"""
        try:
            logger.info("Initializing blockchain database connection...")
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10
            )

            # Create tables if they don't exist
            await self._create_tables()

            logger.info("Blockchain database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize blockchain database: {e}")
            raise

    async def _create_tables(self):
        """Create blockchain tables"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS deployment_blocks (
                    id SERIAL PRIMARY KEY,
                    block_number BIGINT NOT NULL UNIQUE,
                    previous_hash VARCHAR(64),
                    current_hash VARCHAR(64) NOT NULL UNIQUE,

                    -- Deployment data
                    deployment_type VARCHAR(50) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    config JSONB NOT NULL,
                    resource_ref VARCHAR(255),
                    status VARCHAR(50) NOT NULL,
                    error TEXT,
                    source_ip VARCHAR(45),
                    source_country VARCHAR(10),

                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    CONSTRAINT valid_hash CHECK (LENGTH(current_hash) = 64)
                )
            ''')

            # Create indexes
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_blocks_hash
                ON deployment_blocks(current_hash)
            ''')

            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_blocks_number
                ON deployment_blocks(block_number)
            ''')

            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_blocks_type
                ON deployment_blocks(deployment_type)
            ''')

            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_blocks_status
                ON deployment_blocks(status)
            ''')

            logger.info("Blockchain tables created/verified")

    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Blockchain database connection closed")

    def calculate_hash(
        self,
        block_number: int,
        previous_hash: Optional[str],
        timestamp: datetime,
        deployment_type: str,
        name: str,
        config: Dict[str, Any],
        status: str,
        source_ip: Optional[str] = None
    ) -> str:
        """
        Calculate SHA-256 hash for a block

        Args:
            block_number: Block number in the chain
            previous_hash: Hash of the previous block (None for genesis)
            timestamp: Block creation timestamp
            deployment_type: Type of deployment (vm, container)
            name: Deployment name
            config: Configuration dictionary
            status: Deployment status
            source_ip: Source IP address of the request

        Returns:
            64-character hex string (SHA-256 hash)
        """
        # Serialize config to JSON with sorted keys for deterministic hashing
        config_json = json.dumps(config, sort_keys=True, default=str)

        # Create hash input string
        hash_input = (
            f"{block_number}|"
            f"{previous_hash or 'GENESIS'}|"
            f"{timestamp.isoformat()}|"
            f"{deployment_type}|"
            f"{name}|"
            f"{config_json}|"
            f"{status}|"
            f"{source_ip or 'unknown'}"
        )

        # Calculate SHA-256 hash
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

    async def get_last_block(self) -> Optional[Dict[str, Any]]:
        """
        Get the last block in the chain

        Returns:
            Last block record or None if chain is empty
        """
        if not self.pool:
            logger.error("Blockchain database not initialized")
            return None

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT * FROM deployment_blocks
                    ORDER BY block_number DESC
                    LIMIT 1
                ''')

                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"Failed to get last block: {e}")
            raise

    async def create_block(
        self,
        deployment_type: str,
        name: str,
        config: Dict[str, Any],
        resource_ref: Optional[str] = None,
        status: str = "pending",
        error: Optional[str] = None,
        source_ip: Optional[str] = None,
        source_country: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new block in the blockchain

        Args:
            deployment_type: Type of deployment (vm, container)
            name: Deployment name
            config: Configuration dictionary
            resource_ref: Resource reference (VM ref, service ID)
            status: Deployment status
            error: Error message if failed
            source_ip: Source IP address
            source_country: Source country code

        Returns:
            Created block record
        """
        if not self.pool:
            raise RuntimeError("Blockchain database not initialized")

        try:
            async with self.pool.acquire() as conn:
                # Use advisory lock for block creation to prevent race conditions
                async with conn.transaction():
                    # Acquire advisory lock
                    await conn.execute("SELECT pg_advisory_xact_lock(1)")

                    # Get last block for chaining
                    last_block = await conn.fetchrow('''
                        SELECT block_number, current_hash
                        FROM deployment_blocks
                        ORDER BY block_number DESC
                        LIMIT 1
                    ''')

                    # Calculate block number and previous hash
                    if last_block:
                        block_number = last_block['block_number'] + 1
                        previous_hash = last_block['current_hash']
                    else:
                        # Genesis block
                        block_number = 1
                        previous_hash = None

                    # Get timestamp
                    timestamp = datetime.utcnow()

                    # Calculate current hash
                    current_hash = self.calculate_hash(
                        block_number=block_number,
                        previous_hash=previous_hash,
                        timestamp=timestamp,
                        deployment_type=deployment_type,
                        name=name,
                        config=config,
                        status=status,
                        source_ip=source_ip
                    )

                    # Insert block
                    row = await conn.fetchrow('''
                        INSERT INTO deployment_blocks
                        (block_number, previous_hash, current_hash,
                         deployment_type, name, config, resource_ref,
                         status, error, source_ip, source_country, created_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                        RETURNING *
                    ''', block_number, previous_hash, current_hash,
                        deployment_type, name, json.dumps(config),
                        resource_ref, status, error, source_ip, source_country,
                        timestamp)

                    block = dict(row)
                    logger.info(
                        f"Created block #{block_number} hash={current_hash[:16]}... "
                        f"for {deployment_type}/{name}"
                    )

                    return block

        except Exception as e:
            logger.error(f"Failed to create block: {e}")
            raise

    async def get_block_by_hash(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get a block by its hash

        Args:
            block_hash: SHA-256 hash of the block

        Returns:
            Block record or None if not found
        """
        if not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT * FROM deployment_blocks
                    WHERE current_hash = $1
                ''', block_hash)

                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"Failed to get block by hash: {e}")
            raise

    async def get_block_by_number(self, block_number: int) -> Optional[Dict[str, Any]]:
        """
        Get a block by its number

        Args:
            block_number: Block number

        Returns:
            Block record or None if not found
        """
        if not self.pool:
            return None

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow('''
                    SELECT * FROM deployment_blocks
                    WHERE block_number = $1
                ''', block_number)

                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"Failed to get block by number: {e}")
            raise

    async def get_blocks(
        self,
        deployment_type: Optional[str] = None,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get blocks with optional filtering

        Args:
            deployment_type: Filter by deployment type
            status_filter: Filter by status
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of block records
        """
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                query = 'SELECT * FROM deployment_blocks WHERE 1=1'
                params = []
                param_count = 1

                if deployment_type:
                    query += f' AND deployment_type = ${param_count}'
                    params.append(deployment_type)
                    param_count += 1

                if status_filter:
                    query += f' AND status = ${param_count}'
                    params.append(status_filter)
                    param_count += 1

                query += f' ORDER BY block_number DESC LIMIT ${param_count} OFFSET ${param_count + 1}'
                params.extend([limit, offset])

                rows = await conn.fetch(query, *params)

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get blocks: {e}")
            raise

    async def verify_chain_integrity(self) -> Dict[str, Any]:
        """
        Verify the integrity of the entire blockchain

        Returns:
            Verification result with details
        """
        if not self.pool:
            return {
                "valid": False,
                "error": "Database not initialized",
                "blocks_checked": 0
            }

        try:
            async with self.pool.acquire() as conn:
                # Get all blocks ordered by block number
                rows = await conn.fetch('''
                    SELECT * FROM deployment_blocks
                    ORDER BY block_number ASC
                ''')

                if not rows:
                    return {
                        "valid": True,
                        "message": "Chain is empty",
                        "blocks_checked": 0
                    }

                blocks = [dict(row) for row in rows]
                blocks_checked = 0
                invalid_blocks = []

                for i, block in enumerate(blocks):
                    blocks_checked += 1

                    # Check block number sequence
                    expected_number = i + 1
                    if block['block_number'] != expected_number:
                        invalid_blocks.append({
                            "block_number": block['block_number'],
                            "error": f"Expected block number {expected_number}"
                        })
                        continue

                    # Check previous hash linkage
                    if i == 0:
                        # Genesis block should have no previous hash
                        if block['previous_hash'] is not None:
                            invalid_blocks.append({
                                "block_number": block['block_number'],
                                "error": "Genesis block should not have previous_hash"
                            })
                    else:
                        # Non-genesis block should reference previous block's hash
                        expected_prev_hash = blocks[i - 1]['current_hash']
                        if block['previous_hash'] != expected_prev_hash:
                            invalid_blocks.append({
                                "block_number": block['block_number'],
                                "error": f"Invalid previous_hash linkage"
                            })

                    # Verify current hash
                    config = block['config']
                    if isinstance(config, str):
                        config = json.loads(config)

                    expected_hash = self.calculate_hash(
                        block_number=block['block_number'],
                        previous_hash=block['previous_hash'],
                        timestamp=block['created_at'],
                        deployment_type=block['deployment_type'],
                        name=block['name'],
                        config=config,
                        status=block['status'],
                        source_ip=block['source_ip']
                    )

                    if block['current_hash'] != expected_hash:
                        invalid_blocks.append({
                            "block_number": block['block_number'],
                            "error": "Hash mismatch - block data may have been tampered"
                        })

                is_valid = len(invalid_blocks) == 0

                return {
                    "valid": is_valid,
                    "blocks_checked": blocks_checked,
                    "invalid_blocks": invalid_blocks if not is_valid else None,
                    "message": "Chain integrity verified" if is_valid else "Chain integrity compromised"
                }

        except Exception as e:
            logger.error(f"Failed to verify chain integrity: {e}")
            return {
                "valid": False,
                "error": str(e),
                "blocks_checked": 0
            }

    async def ping(self) -> bool:
        """
        Check database connection

        Returns:
            True if connected, False otherwise
        """
        if not self.pool:
            return False

        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Blockchain database ping failed: {e}")
            return False
