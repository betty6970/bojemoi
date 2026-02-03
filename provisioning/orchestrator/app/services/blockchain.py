"""Blockchain service for immutable deployment logging.

This module provides an immutable audit trail for all deployments using
a SHA-256 hash chain. Each block contains:
- Deployment metadata (type, name, config)
- Source IP and country for audit
- Previous block hash for chain integrity
- Timestamp for ordering

The chain uses PostgreSQL advisory locks to prevent race conditions
during block creation.
"""
import asyncpg
import hashlib
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Genesis block configuration
GENESIS_BLOCK_CONFIG = {
    "type": "genesis",
    "message": "Bojemoi Lab Blockchain Initialized",
    "version": "1.0.0",
}


class BlockchainService:
    """Service for managing blockchain-based deployment records.

    The blockchain provides an immutable audit trail for all deployments.
    Each block is cryptographically linked to the previous block via SHA-256
    hashing, making tampering detectable.

    Features:
    - Genesis block auto-creation on initialization
    - Advisory locks for concurrent write protection
    - Full chain integrity verification
    - Pagination and filtering support
    """

    def __init__(self, database_url: str):
        """
        Initialize blockchain service.

        Args:
            database_url: PostgreSQL connection URL to karacho database
        """
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False

    async def init(self):
        """Initialize connection pool, create tables, and ensure genesis block exists."""
        try:
            logger.info("Initializing blockchain database connection...")
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=2,
                max_size=10
            )

            # Create tables if they don't exist
            await self._create_tables()

            # Ensure genesis block exists
            await self._ensure_genesis_block()

            self._initialized = True
            logger.info("Blockchain database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize blockchain database: {e}")
            raise

    async def _ensure_genesis_block(self):
        """Create genesis block if chain is empty."""
        async with self.pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM deployment_blocks"
            )

            if count == 0:
                logger.info("Creating genesis block...")
                await self._create_genesis_block(conn)

    async def _create_genesis_block(self, conn: asyncpg.Connection):
        """
        Create the first block in the blockchain.

        The genesis block has:
        - block_number = 0
        - previous_hash = None (64 zeros for hash computation)
        - Special genesis configuration

        Args:
            conn: Database connection to use
        """
        timestamp = datetime.utcnow()

        # Calculate hash for genesis block
        genesis_hash = self.calculate_hash(
            block_number=0,
            previous_hash=None,
            timestamp=timestamp,
            deployment_type="genesis",
            name="genesis",
            config=GENESIS_BLOCK_CONFIG,
            status="success",
            source_ip=None
        )

        await conn.execute('''
            INSERT INTO deployment_blocks
            (block_number, previous_hash, current_hash,
             deployment_type, name, config, resource_ref,
             status, error, source_ip, source_country, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        ''', 0, None, genesis_hash,
            "genesis", "genesis", json.dumps(GENESIS_BLOCK_CONFIG),
            None, "success", None, None, None, timestamp)

        logger.info(f"Genesis block created: {genesis_hash[:16]}...")

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
        Create a new block in the blockchain.

        This method uses PostgreSQL advisory locks to ensure only one block
        can be created at a time, preventing race conditions and ensuring
        chain integrity.

        Args:
            deployment_type: Type of deployment (vm, container, service)
            name: Deployment name
            config: Configuration dictionary (will be JSON serialized)
            resource_ref: Resource reference (VM ref, service ID)
            status: Deployment status (pending, success, failed)
            error: Error message if deployment failed
            source_ip: Source IP address of the request
            source_country: Source country code (2-letter ISO)

        Returns:
            Created block record as dictionary

        Raises:
            RuntimeError: If database is not initialized
            Exception: If block creation fails
        """
        if not self.pool:
            raise RuntimeError("Blockchain database not initialized")

        if not self._initialized:
            raise RuntimeError("Blockchain service not initialized. Call init() first.")

        try:
            async with self.pool.acquire() as conn:
                # Use advisory lock for block creation to prevent race conditions
                async with conn.transaction():
                    # Acquire advisory lock (lock ID 1 is reserved for blockchain)
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
                        # This shouldn't happen if init() was called properly
                        # But handle it gracefully by starting at block 1
                        logger.warning("No genesis block found, creating first deployment block")
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
                        f"for {deployment_type}/{name} [status={status}]"
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
        Verify the integrity of the entire blockchain.

        This method checks:
        1. Block number sequence (should be 0, 1, 2, ...)
        2. Previous hash linkage (each block references previous block's hash)
        3. Hash integrity (recompute hash and compare)

        Returns:
            Dictionary containing:
            - valid: Boolean indicating if chain is intact
            - blocks_checked: Number of blocks verified
            - invalid_blocks: List of invalid blocks (if any)
            - message: Human-readable status message
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
                    block_num = block['block_number']

                    # Check block number sequence (starts at 0 for genesis)
                    expected_number = i
                    if block_num != expected_number:
                        invalid_blocks.append({
                            "block_number": block_num,
                            "error": f"Expected block number {expected_number}, got {block_num}"
                        })
                        continue

                    # Check previous hash linkage
                    if i == 0:
                        # Genesis block (block 0) should have no previous hash
                        if block['previous_hash'] is not None:
                            invalid_blocks.append({
                                "block_number": block_num,
                                "error": "Genesis block should not have previous_hash"
                            })
                    else:
                        # Non-genesis blocks should reference previous block's hash
                        expected_prev_hash = blocks[i - 1]['current_hash']
                        if block['previous_hash'] != expected_prev_hash:
                            invalid_blocks.append({
                                "block_number": block_num,
                                "error": f"Invalid previous_hash linkage (expected {expected_prev_hash[:16]}...)"
                            })
                            continue

                    # Verify current hash by recomputing it
                    config = block['config']
                    if isinstance(config, str):
                        config = json.loads(config)

                    expected_hash = self.calculate_hash(
                        block_number=block_num,
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
                            "block_number": block_num,
                            "error": f"Hash mismatch - block data may have been tampered (expected {expected_hash[:16]}..., got {block['current_hash'][:16]}...)"
                        })

                is_valid = len(invalid_blocks) == 0

                result = {
                    "valid": is_valid,
                    "blocks_checked": blocks_checked,
                    "message": "Chain integrity verified" if is_valid else "Chain integrity compromised"
                }

                if not is_valid:
                    result["invalid_blocks"] = invalid_blocks
                    result["invalid_count"] = len(invalid_blocks)

                return result

        except Exception as e:
            logger.error(f"Failed to verify chain integrity: {e}")
            return {
                "valid": False,
                "error": str(e),
                "blocks_checked": 0
            }

    async def ping(self) -> bool:
        """
        Check database connection.

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

    async def count_blocks(self) -> int:
        """
        Get total number of blocks in the chain.

        Returns:
            Total block count (including genesis block)
        """
        if not self.pool:
            return 0

        try:
            async with self.pool.acquire() as conn:
                count = await conn.fetchval(
                    "SELECT COUNT(*) FROM deployment_blocks"
                )
                return count or 0
        except Exception as e:
            logger.error(f"Failed to count blocks: {e}")
            return 0

    async def get_chain_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive blockchain statistics.

        Returns:
            Dictionary containing:
            - total_blocks: Total number of blocks
            - deployments_by_type: Count by deployment type
            - deployments_by_status: Count by status
            - first_block_time: Timestamp of genesis block
            - last_block_time: Timestamp of most recent block
            - chain_valid: Whether chain integrity is intact
        """
        if not self.pool:
            return {"error": "Database not initialized"}

        try:
            async with self.pool.acquire() as conn:
                # Total blocks
                total = await conn.fetchval(
                    "SELECT COUNT(*) FROM deployment_blocks"
                )

                # By type (excluding genesis)
                type_rows = await conn.fetch('''
                    SELECT deployment_type, COUNT(*) as count
                    FROM deployment_blocks
                    WHERE deployment_type != 'genesis'
                    GROUP BY deployment_type
                ''')
                by_type = {row['deployment_type']: row['count'] for row in type_rows}

                # By status
                status_rows = await conn.fetch('''
                    SELECT status, COUNT(*) as count
                    FROM deployment_blocks
                    GROUP BY status
                ''')
                by_status = {row['status']: row['count'] for row in status_rows}

                # Time range
                time_range = await conn.fetchrow('''
                    SELECT
                        MIN(created_at) as first_block,
                        MAX(created_at) as last_block
                    FROM deployment_blocks
                ''')

                # Quick integrity check (just verify chain length matches block numbers)
                max_block = await conn.fetchval(
                    "SELECT MAX(block_number) FROM deployment_blocks"
                )
                chain_continuous = (max_block is not None and max_block + 1 == total)

                return {
                    "total_blocks": total or 0,
                    "deployments_by_type": by_type,
                    "deployments_by_status": by_status,
                    "first_block_time": time_range['first_block'].isoformat() if time_range and time_range['first_block'] else None,
                    "last_block_time": time_range['last_block'].isoformat() if time_range and time_range['last_block'] else None,
                    "chain_continuous": chain_continuous,
                }

        except Exception as e:
            logger.error(f"Failed to get chain stats: {e}")
            return {"error": str(e)}

    async def get_blocks_by_name(self, name: str) -> List[Dict[str, Any]]:
        """
        Get all blocks for a specific deployment name.

        Useful for tracking the history of a particular deployment.

        Args:
            name: Deployment name to search for

        Returns:
            List of blocks matching the name, ordered by block number
        """
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT * FROM deployment_blocks
                    WHERE name = $1
                    ORDER BY block_number ASC
                ''', name)

                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get blocks by name: {e}")
            return []

    async def export_chain(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Export blockchain data for backup or analysis.

        Args:
            limit: Maximum number of blocks to export

        Returns:
            List of all blocks in chain order
        """
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('''
                    SELECT * FROM deployment_blocks
                    ORDER BY block_number ASC
                    LIMIT $1
                ''', limit)

                blocks = []
                for row in rows:
                    block = dict(row)
                    # Convert timestamps to ISO format
                    if block.get('created_at'):
                        block['created_at'] = block['created_at'].isoformat()
                    # Parse config if it's a string
                    if isinstance(block.get('config'), str):
                        block['config'] = json.loads(block['config'])
                    blocks.append(block)

                return blocks

        except Exception as e:
            logger.error(f"Failed to export chain: {e}")
            return []
