"""VulnHub VM manager.

Catalogue des VMs VulnHub/vulnérables + gestion des cibles actives dans host_debug.

Les VMs doivent être importées comme templates XenServer une fois (manuellement ou
via le script scripts/import_vulnhub_ova.sh sur le host XenServer).
Ensuite l'orchestrateur les clone, les démarre, et enregistre leur IP dans host_debug
pour que bm12/uzi les scannent (DEBUG_MODE=1).
"""
import asyncpg
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─── Catalogue VulnHub ────────────────────────────────────────────────────────
# xen_template : nom exact du template XenServer après import de l'OVA
VULNHUB_CATALOG: Dict[str, Dict[str, Any]] = {
    "metasploitable2": {
        "name": "Metasploitable 2",
        "description": "Ubuntu 8.04 LTS. Dizaines de vulns : vsftpd 2.3.4 backdoor, UnrealIRCd, distcc, Tomcat, phpMyAdmin, MySQL sans auth, NFS export, ProFTPD mod_copy.",
        "xen_template": "metasploitable2",
        "cpu": 1,
        "memory_mb": 512,
        "disk_gb": 8,
        "tags": ["linux", "ubuntu", "classic", "beginner", "multi-exploit"],
        "known_vulns": [
            "vsftpd_backdoor", "proftpd_modcopy", "tomcat_manager",
            "phpmyadmin", "mongodb_noauth", "nfs_export", "snmp_public",
            "smtp_openrelay",
        ],
        "ova_hint": "http://sourceforge.net/projects/metasploitable/files/Metasploitable2/",
    },
    "metasploitable3-ubuntu": {
        "name": "Metasploitable 3 (Ubuntu 14.04)",
        "description": "Ubuntu 14.04. Vulns modernes : ManageEngine, Apache Struts, Jenkins, ElasticSearch, ProFTPD, Samba.",
        "xen_template": "metasploitable3-ubuntu",
        "cpu": 2,
        "memory_mb": 2048,
        "disk_gb": 20,
        "tags": ["linux", "ubuntu", "modern", "intermediate"],
        "known_vulns": [
            "proftpd_modcopy", "jenkins", "elasticsearch",
            "struts", "anonymous_ftp", "samba_old",
        ],
        "ova_hint": "https://github.com/rapid7/metasploitable3 (vagrant build)",
    },
    "dvwa": {
        "name": "Damn Vulnerable Web Application",
        "description": "PHP/MySQL, toutes les vulns OWASP Top 10 : SQLi, XSS, LFI, RFI, command injection.",
        "xen_template": "dvwa",
        "cpu": 1,
        "memory_mb": 512,
        "disk_gb": 8,
        "tags": ["linux", "web", "sqli", "xss", "lfi", "command-injection", "beginner"],
        "known_vulns": ["shellshock", "phpmyadmin"],
        "ova_hint": "https://dvwa.co.uk/",
    },
    "dc-1": {
        "name": "DC: 1",
        "description": "Drupal 7 + MySQL. Exploitable via Drupalgeddon (CVE-2018-7600).",
        "xen_template": "dc-1",
        "cpu": 1,
        "memory_mb": 512,
        "disk_gb": 20,
        "tags": ["linux", "drupal", "ctf"],
        "known_vulns": ["drupal"],
        "ova_hint": "https://www.vulnhub.com/entry/dc-1,292/",
    },
    "kioptrix-1": {
        "name": "Kioptrix Level 1",
        "description": "Red Hat/CentOS. Apache mod_ssl buffer overflow, Samba 2.2.x trans2open.",
        "xen_template": "kioptrix-1",
        "cpu": 1,
        "memory_mb": 256,
        "disk_gb": 8,
        "tags": ["linux", "redhat", "apache", "samba", "classic"],
        "known_vulns": ["samba_old"],
        "ova_hint": "https://www.vulnhub.com/entry/kioptrix-level-1-1,22/",
    },
    "basic-pentesting-1": {
        "name": "Basic Pentesting 1",
        "description": "FTP anonyme, WordPress, ProFTPD mod_copy, Samba.",
        "xen_template": "basic-pentesting-1",
        "cpu": 1,
        "memory_mb": 512,
        "disk_gb": 20,
        "tags": ["linux", "wordpress", "ftp", "smb", "beginner"],
        "known_vulns": ["wordpress", "anonymous_ftp", "proftpd_modcopy"],
        "ova_hint": "https://www.vulnhub.com/entry/basic-pentesting-1,216/",
    },
    "lampiao": {
        "name": "Lampião",
        "description": "Drupal 7 + dirty cow privilege escalation (CVE-2016-5195).",
        "xen_template": "lampiao",
        "cpu": 1,
        "memory_mb": 512,
        "disk_gb": 8,
        "tags": ["linux", "drupal", "privesc", "ctf"],
        "known_vulns": ["drupal"],
        "ova_hint": "https://www.vulnhub.com/entry/lampiao-1,249/",
    },
    "pwnlab-init": {
        "name": "PwnLab: init",
        "description": "PHP LFI → file upload bypass → reverse shell → privilege escalation.",
        "xen_template": "pwnlab-init",
        "cpu": 1,
        "memory_mb": 512,
        "disk_gb": 8,
        "tags": ["linux", "web", "lfi", "file-upload", "ctf"],
        "known_vulns": ["shellshock", "phpmyadmin"],
        "ova_hint": "https://www.vulnhub.com/entry/pwnlab-init,158/",
    },
}


class VulnHubManager:
    """Gestion des VMs VulnHub actives dans host_debug (multi-target)."""

    def __init__(self, msf_db_url: str):
        self.msf_db_url = msf_db_url
        self.pool = None

    async def init(self):
        try:
            self.pool = await asyncpg.create_pool(
                self.msf_db_url, min_size=1, max_size=5
            )
            await self._ensure_table()
            logger.info("VulnHubManager initialisé (table host_debug prête)")
        except Exception as e:
            logger.error(f"VulnHubManager init failed: {e}")
            raise

    async def _ensure_table(self):
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

    async def add_target(
        self,
        address: str,
        vm_name: str,
        vm_uuid: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Ajoute ou met à jour une VM dans host_debug (plusieurs cibles simultanées)."""
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

    async def remove_target_by_name(self, vm_name_prefix: str) -> int:
        """Supprime les entrées host_debug dont vm_name commence par vm_name_prefix."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM host_debug WHERE vm_name LIKE $1",
                f"{vm_name_prefix}%",
            )
            return int(result.split()[-1])

    async def list_targets(self) -> List[Dict[str, Any]]:
        """Retourne toutes les VMs actives dans host_debug."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, address, vm_name, vm_uuid, created_at, updated_at "
                "FROM host_debug ORDER BY created_at"
            )
            return [dict(r) for r in rows]

    async def close(self):
        if self.pool:
            await self.pool.close()
