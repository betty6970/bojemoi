"""Rapid7 debug VM manager.

Gère la table host_debug dans la DB msf.
Cette table est lue par thearm_uzi en mode DEBUG_MODE=1
pour cibler une VM Rapid7 (Metasploitable) à la place d'un hôte aléatoire.

Schéma de la table host_debug (créée automatiquement) :
    id         SERIAL PRIMARY KEY
    address    VARCHAR(255) UNIQUE NOT NULL   -- IP de la VM
    vm_name    VARCHAR(255)                   -- Nom de la VM sur XenServer
    vm_uuid    VARCHAR(255)                   -- UUID XenServer
    created_at TIMESTAMP DEFAULT NOW()
    updated_at TIMESTAMP DEFAULT NOW()
"""
import asyncpg
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class Rapid7Manager:
    """Gestion de la table host_debug dans la DB msf."""

    def __init__(self, msf_db_url: str):
        self.msf_db_url = msf_db_url
        self.pool = None

    async def init(self):
        """Initialise le pool de connexions et crée la table si nécessaire."""
        try:
            self.pool = await asyncpg.create_pool(
                self.msf_db_url,
                min_size=1,
                max_size=5
            )
            await self._ensure_table()
            logger.info("Rapid7Manager initialisé (table host_debug prête)")
        except Exception as e:
            logger.error(f"Rapid7Manager init failed: {e}")
            raise

    async def _ensure_table(self):
        """Crée host_debug si elle n'existe pas."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS host_debug (
                    id         SERIAL PRIMARY KEY,
                    address    VARCHAR(255) NOT NULL UNIQUE,
                    vm_name    VARCHAR(255),
                    vm_uuid    VARCHAR(255),
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

    async def upsert_host(
        self,
        address: str,
        vm_name: str,
        vm_uuid: Optional[str] = None
    ) -> Dict[str, Any]:
        """Insère ou met à jour l'enregistrement debug.

        Un seul enregistrement actif à la fois (UPSERT sur address).
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO host_debug (address, vm_name, vm_uuid, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (address) DO UPDATE SET
                    vm_name    = EXCLUDED.vm_name,
                    vm_uuid    = EXCLUDED.vm_uuid,
                    updated_at = NOW()
                RETURNING id, address, vm_name, vm_uuid, created_at, updated_at
            """, address, vm_name, vm_uuid)
            return dict(row)

    async def replace_host(
        self,
        address: str,
        vm_name: str,
        vm_uuid: Optional[str] = None
    ) -> Dict[str, Any]:
        """Remplace toute la table par un unique enregistrement.

        Utilisé lors d'un nouveau déploiement pour éviter les entrées orphelines.
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM host_debug")
                row = await conn.fetchrow("""
                    INSERT INTO host_debug (address, vm_name, vm_uuid)
                    VALUES ($1, $2, $3)
                    RETURNING id, address, vm_name, vm_uuid, created_at, updated_at
                """, address, vm_name, vm_uuid)
                return dict(row)

    async def get_host(self) -> Optional[Dict[str, Any]]:
        """Retourne le premier enregistrement de host_debug (ou None)."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, address, vm_name, vm_uuid, created_at, updated_at "
                "FROM host_debug LIMIT 1"
            )
            return dict(row) if row else None

    async def clear(self):
        """Vide la table host_debug."""
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM host_debug")

    async def close(self):
        if self.pool:
            await self.pool.close()
