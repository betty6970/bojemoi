"""IP2Location client for IP geolocation lookup"""
import asyncpg
import logging
import ipaddress
from typing import Optional

logger = logging.getLogger(__name__)


# Private IP ranges - these bypass geolocation validation
PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
]


class IP2LocationClient:
    """Client for querying IP geolocation from ip2location database"""

    def __init__(self, database_url: str):
        """
        Initialize IP2Location client

        Args:
            database_url: PostgreSQL connection URL to ip2location database
        """
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def init(self):
        """Initialize connection pool"""
        try:
            logger.info("Initializing IP2Location database connection...")
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=5
            )
            logger.info("IP2Location database connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize IP2Location database: {e}")
            raise

    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("IP2Location database connection closed")

    def is_private_ip(self, ip_address: str) -> bool:
        """
        Check if IP address is in a private range

        Args:
            ip_address: IP address string

        Returns:
            True if private, False otherwise
        """
        try:
            ip = ipaddress.ip_address(ip_address)
            for network in PRIVATE_NETWORKS:
                if ip in network:
                    return True
            return False
        except ValueError:
            logger.warning(f"Invalid IP address: {ip_address}")
            return False

    async def get_country_by_ip(self, ip_address: str) -> Optional[str]:
        """
        Get country code for an IP address

        Uses PostgreSQL CIDR operator >>= to check if network contains the IP

        Args:
            ip_address: IP address string (IPv4 or IPv6)

        Returns:
            ISO 3166-1 alpha-2 country code (e.g., 'FR', 'DE') or None if not found
        """
        # Skip lookup for private IPs
        if self.is_private_ip(ip_address):
            logger.debug(f"IP {ip_address} is private, skipping geolocation")
            return "PRIVATE"

        if not self.pool:
            logger.error("IP2Location database not initialized")
            return None

        try:
            async with self.pool.acquire() as conn:
                # Use CIDR containment operator >>=
                # network >>= ip means "network contains IP"
                row = await conn.fetchrow(
                    """
                    SELECT country_code
                    FROM ip2location
                    WHERE network >>= $1::inet
                    LIMIT 1
                    """,
                    ip_address
                )

                if row:
                    country_code = row["country_code"]
                    logger.debug(f"IP {ip_address} -> country: {country_code}")
                    return country_code.strip() if country_code else None

                logger.warning(f"No country found for IP: {ip_address}")
                return None

        except Exception as e:
            logger.error(f"Failed to lookup IP {ip_address}: {e}")
            return None

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
            logger.error(f"IP2Location database ping failed: {e}")
            return False
