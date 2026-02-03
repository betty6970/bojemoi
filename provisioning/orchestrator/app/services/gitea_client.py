"""Gitea API client for cloud-init template management.

This module provides access to cloud-init templates stored in a Gitea repository.
Templates are fetched using Gitea's raw file API for efficiency.

Repository structure expected:
    bojemoi-configs/
    ├── cloud-init/
    │   ├── alpine/
    │   │   ├── base.yaml
    │   │   ├── webserver.yaml
    │   │   └── docker-node.yaml
    │   ├── ubuntu/
    │   │   ├── base.yaml
    │   │   └── webserver.yaml
    │   └── common/
    │       ├── docker-setup.sh
    │       └── monitoring-agent.sh
    └── vms/
        └── {vm-name}.yaml
"""
import base64
import hashlib
import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with content and expiration."""
    content: str
    expires_at: float
    etag: Optional[str] = None


class GiteaClient:
    """Client for interacting with Gitea API.

    Provides methods for fetching cloud-init templates and other configuration
    files from a Gitea repository using raw file access.

    Features:
    - Raw file access (efficient, no base64 encoding)
    - In-memory caching with TTL
    - ETag support for conditional requests
    - Template listing and discovery
    """

    # Default paths in the repository
    CLOUD_INIT_PATH = "cloud-init"
    VM_CONFIGS_PATH = "vms"
    COMMON_SCRIPTS_PATH = "cloud-init/common"

    def __init__(
        self,
        base_url: str,
        token: str,
        repo: str = "bojemoi-configs",
        owner: str = "bojemoi",
        cache_ttl: int = 300,  # 5 minutes default
        timeout: float = 30.0
    ):
        """
        Initialize Gitea client.

        Args:
            base_url: Gitea server URL (e.g., https://gitea.bojemoi.me)
            token: API token for authentication
            repo: Repository name containing configs
            owner: Repository owner (user or organization)
            cache_ttl: Cache time-to-live in seconds (0 to disable)
            timeout: HTTP request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.repo = repo
        self.owner = owner
        self.cache_ttl = cache_ttl
        self.timeout = timeout

        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/json",
        }

        # Simple in-memory cache
        self._cache: Dict[str, CacheEntry] = {}

    def _cache_key(self, path: str, branch: str) -> str:
        """Generate cache key for a file."""
        return f"{self.owner}/{self.repo}/{branch}/{path}"

    def _get_cached(self, path: str, branch: str) -> Optional[str]:
        """Get content from cache if valid."""
        if self.cache_ttl <= 0:
            return None

        key = self._cache_key(path, branch)
        entry = self._cache.get(key)

        if entry and entry.expires_at > time.time():
            logger.debug(f"Cache hit: {path}")
            return entry.content

        return None

    def _set_cached(self, path: str, branch: str, content: str, etag: Optional[str] = None):
        """Store content in cache."""
        if self.cache_ttl <= 0:
            return

        key = self._cache_key(path, branch)
        self._cache[key] = CacheEntry(
            content=content,
            expires_at=time.time() + self.cache_ttl,
            etag=etag
        )
        logger.debug(f"Cached: {path} (TTL: {self.cache_ttl}s)")

    def clear_cache(self):
        """Clear all cached entries."""
        self._cache.clear()
        logger.info("Cache cleared")

    async def get_file_raw(
        self,
        path: str,
        branch: str = "main",
        use_cache: bool = True
    ) -> str:
        """
        Get file content using raw API endpoint.

        This is more efficient than the contents API as it returns
        the raw file without base64 encoding.

        Args:
            path: File path in repository
            branch: Git branch (default: main)
            use_cache: Whether to use cache (default: True)

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file not found (404)
            httpx.HTTPStatusError: For other HTTP errors
        """
        # Check cache first
        if use_cache:
            cached = self._get_cached(path, branch)
            if cached is not None:
                return cached

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Use raw endpoint for direct file access
                url = f"{self.base_url}/api/v1/repos/{self.owner}/{self.repo}/raw/{path}"
                params = {"ref": branch}

                logger.debug(f"Fetching raw file: {path} (branch: {branch})")

                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()

                content = response.text
                etag = response.headers.get("ETag")

                # Cache the result
                self._set_cached(path, branch, content, etag)

                logger.debug(f"Fetched raw file: {path} ({len(content)} bytes)")
                return content

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"File not found: {path}")
                raise FileNotFoundError(f"File not found in repository: {path}")
            logger.error(f"Gitea API error for {path}: {e.response.status_code}")
            raise
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching file: {path}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch raw file {path}: {e}")
            raise

    async def get_file_content(
        self,
        path: str,
        branch: str = "main"
    ) -> str:
        """
        Get file content from repository (contents API with base64).

        This method uses the contents API which returns base64-encoded content.
        For new code, prefer get_file_raw() which is more efficient.

        Args:
            path: File path in repository
            branch: Git branch (default: main)

        Returns:
            File content as string
        """
        # Check cache first
        cached = self._get_cached(path, branch)
        if cached is not None:
            return cached

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}/api/v1/repos/{self.owner}/{self.repo}/contents/{path}"
                params = {"ref": branch}

                logger.debug(f"Fetching file (contents API): {path}")

                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()

                data = response.json()
                content_b64 = data.get("content", "")

                # Decode from base64
                content = base64.b64decode(content_b64).decode('utf-8')

                # Cache the result
                self._set_cached(path, branch, content)

                logger.debug(f"Fetched file: {path}")
                return content

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"File not found: {path}")
                raise FileNotFoundError(f"File not found: {path}")
            raise
        except Exception as e:
            logger.error(f"Failed to fetch file: {e}")
            raise

    async def list_directory(
        self,
        path: str = "",
        branch: str = "main"
    ) -> List[Dict[str, Any]]:
        """
        List directory contents.

        Args:
            path: Directory path in repository
            branch: Git branch

        Returns:
            List of file/directory entries with keys:
            - name: File or directory name
            - path: Full path
            - type: 'file' or 'dir'
            - size: File size (for files)
            - sha: Git SHA
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                url = f"{self.base_url}/api/v1/repos/{self.owner}/{self.repo}/contents/{path}"
                params = {"ref": branch}

                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()

                return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"Directory not found: {path}")
                return []
            raise
        except Exception as e:
            logger.error(f"Failed to list directory {path}: {e}")
            raise

    async def get_template(
        self,
        os_type: str,
        template_name: str,
        branch: str = "main"
    ) -> str:
        """
        Get a cloud-init template by OS type and name.

        Args:
            os_type: Operating system type (alpine, ubuntu, debian)
            template_name: Template name (without .yaml extension)
            branch: Git branch

        Returns:
            Template content as string

        Raises:
            FileNotFoundError: If template not found

        Example:
            template = await client.get_template("alpine", "webserver")
        """
        # Normalize template name
        if not template_name.endswith('.yaml'):
            template_name = f"{template_name}.yaml"

        path = f"{self.CLOUD_INIT_PATH}/{os_type}/{template_name}"
        return await self.get_file_raw(path, branch)

    async def list_templates(
        self,
        os_type: Optional[str] = None,
        branch: str = "main"
    ) -> Dict[str, List[str]]:
        """
        List available cloud-init templates.

        Args:
            os_type: Filter by OS type, or None for all
            branch: Git branch

        Returns:
            Dictionary mapping OS type to list of template names

        Example:
            templates = await client.list_templates()
            # {'alpine': ['base', 'webserver'], 'ubuntu': ['base']}

            alpine_templates = await client.list_templates('alpine')
            # {'alpine': ['base', 'webserver', 'docker-node']}
        """
        result: Dict[str, List[str]] = {}

        try:
            if os_type:
                # List templates for specific OS
                path = f"{self.CLOUD_INIT_PATH}/{os_type}"
                entries = await self.list_directory(path, branch)

                templates = []
                for entry in entries:
                    if entry.get('type') == 'file' and entry['name'].endswith('.yaml'):
                        # Remove .yaml extension
                        name = entry['name'][:-5]
                        templates.append(name)

                result[os_type] = sorted(templates)
            else:
                # List all OS types first
                entries = await self.list_directory(self.CLOUD_INIT_PATH, branch)

                for entry in entries:
                    if entry.get('type') == 'dir' and entry['name'] != 'common':
                        os_name = entry['name']
                        os_templates = await self.list_templates(os_name, branch)
                        result.update(os_templates)

            return result

        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return result

    async def get_vm_config(
        self,
        vm_name: str,
        branch: str = "main"
    ) -> Optional[str]:
        """
        Get VM-specific configuration file.

        Args:
            vm_name: VM name
            branch: Git branch

        Returns:
            VM config content, or None if not found
        """
        path = f"{self.VM_CONFIGS_PATH}/{vm_name}.yaml"
        try:
            return await self.get_file_raw(path, branch)
        except FileNotFoundError:
            logger.debug(f"No VM config found for: {vm_name}")
            return None

    async def get_common_script(
        self,
        script_name: str,
        branch: str = "main"
    ) -> str:
        """
        Get a common script from cloud-init/common directory.

        Args:
            script_name: Script filename (with or without extension)
            branch: Git branch

        Returns:
            Script content
        """
        # Add .sh extension if not present
        if not script_name.endswith('.sh'):
            script_name = f"{script_name}.sh"

        path = f"{self.COMMON_SCRIPTS_PATH}/{script_name}"
        return await self.get_file_raw(path, branch)

    async def list_common_scripts(self, branch: str = "main") -> List[str]:
        """
        List available common scripts.

        Returns:
            List of script names (without .sh extension)
        """
        try:
            entries = await self.list_directory(self.COMMON_SCRIPTS_PATH, branch)

            scripts = []
            for entry in entries:
                if entry.get('type') == 'file' and entry['name'].endswith('.sh'):
                    name = entry['name'][:-3]  # Remove .sh
                    scripts.append(name)

            return sorted(scripts)

        except Exception as e:
            logger.error(f"Failed to list common scripts: {e}")
            return []

    async def file_exists(
        self,
        path: str,
        branch: str = "main"
    ) -> bool:
        """
        Check if a file exists in the repository.

        Args:
            path: File path
            branch: Git branch

        Returns:
            True if file exists, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.base_url}/api/v1/repos/{self.owner}/{self.repo}/contents/{path}"
                params = {"ref": branch}

                response = await client.head(
                    url,
                    headers=self.headers,
                    params=params
                )

                return response.status_code == 200

        except Exception:
            return False

    async def get_file_sha(
        self,
        path: str,
        branch: str = "main"
    ) -> Optional[str]:
        """
        Get the Git SHA of a file (useful for caching/versioning).

        Args:
            path: File path
            branch: Git branch

        Returns:
            SHA string or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.base_url}/api/v1/repos/{self.owner}/{self.repo}/contents/{path}"
                params = {"ref": branch}

                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )

                if response.status_code == 200:
                    return response.json().get('sha')

                return None

        except Exception:
            return None

    async def ping(self) -> bool:
        """
        Check if Gitea is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.base_url}/api/v1/version"

                response = await client.get(url, headers=self.headers)

                if response.status_code == 200:
                    version = response.json()
                    logger.info(f"Gitea connection OK - Version: {version.get('version', 'unknown')}")
                    return True
                else:
                    logger.warning(f"Gitea returned status: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"Gitea ping failed: {e}")
            return False

    async def get_repo_info(self) -> Optional[Dict[str, Any]]:
        """
        Get repository information.

        Returns:
            Repository info dict or None on error
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{self.base_url}/api/v1/repos/{self.owner}/{self.repo}"

                response = await client.get(url, headers=self.headers)
                response.raise_for_status()

                return response.json()

        except Exception as e:
            logger.error(f"Failed to get repo info: {e}")
            return None
