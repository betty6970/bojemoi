"""Gitea API client"""
import httpx
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GiteaClient:
    """Client for interacting with Gitea API"""
    
    def __init__(self, base_url: str, token: str, repo: str = "bojemoi-configs"):
        """
        Initialize Gitea client
        
        Args:
            base_url: Gitea server URL (e.g., https://gitea.bojemoi.me)
            token: API token
            repo: Repository name
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.repo = repo
        self.owner = "bojemoi"  # Adjust as needed
        
        self.headers = {
            "Authorization": f"token {token}",
            "Content-Type": "application/json"
        }
    
    async def get_file_content(
        self, 
        path: str, 
        branch: str = "main"
    ) -> str:
        """
        Get file content from repository
        
        Args:
            path: File path in repository
            branch: Git branch (default: main)
        
        Returns:
            File content as string
        
        Raises:
            Exception: If file not found or API error
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/repos/{self.owner}/{self.repo}/contents/{path}"
                params = {"ref": branch}
                
                logger.debug(f"Fetching file from Gitea: {path}")
                
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                
                # Gitea returns content in base64
                data = response.json()
                content_b64 = data.get("content", "")
                
                # Decode from base64
                content = base64.b64decode(content_b64).decode('utf-8')
                
                logger.debug(f"Successfully fetched file: {path}")
                return content
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.error(f"File not found in Gitea: {path}")
                raise FileNotFoundError(f"File not found: {path}")
            else:
                logger.error(f"Gitea API error: {e}")
                raise
        except Exception as e:
            logger.error(f"Failed to fetch file from Gitea: {e}")
            raise
    
    async def list_directory(
        self,
        path: str = "",
        branch: str = "main"
    ) -> list:
        """
        List directory contents
        
        Args:
            path: Directory path in repository
            branch: Git branch
        
        Returns:
            List of file/directory entries
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/api/v1/repos/{self.owner}/{self.repo}/contents/{path}"
                params = {"ref": branch}
                
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params
                )
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            logger.error(f"Failed to list directory: {e}")
            raise
    
    async def ping(self) -> bool:
        """
        Check if Gitea is accessible
        
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
                    return False
                    
        except Exception as e:
            logger.error(f"Gitea ping failed: {e}")
            return False
