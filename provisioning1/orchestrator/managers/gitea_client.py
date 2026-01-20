import httpx
from typing import Dict
import yaml
import base64
import logging

logger = logging.getLogger(__name__)

class GiteaClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self.repo_owner = "bojemoi"
        self.repo_name = "infrastructure"
    
    async def check_connection(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/version",
                    headers={"Authorization": f"token {self.token}"}
                )
                return response.status_code == 200
        except:
            return False
    
    async def get_file_content(self, path: str) -> str:
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/api/v1/repos/{self.repo_owner}/{self.repo_name}/contents/{path}"
            response = await client.get(url, headers={"Authorization": f"token {self.token}"})
            response.raise_for_status()
            content = response.json()["content"]
            return base64.b64decode(content).decode("utf-8")
    
    async def get_vm_config(self, vm_name: str) -> Dict:
        content = await self.get_file_content(f"vms/{vm_name}.yaml")
        return yaml.safe_load(content)
    
    async def get_container_config(self, container_name: str) -> Dict:
        content = await self.get_file_content(f"containers/{container_name}.yaml")
        return yaml.safe_load(content)
    
    async def get_service_config(self, service_name: str) -> Dict:
        content = await self.get_file_content(f"services/{service_name}.yaml")
        return yaml.safe_load(content)
    
    async def get_cloud_init_config(self, config_name: str) -> str:
        return await self.get_file_content(f"cloud-init/{config_name}.yaml")

