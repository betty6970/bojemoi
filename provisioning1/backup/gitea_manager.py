import aiohttp
import structlog
import yaml
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from config import settings
from models import DeploymentManifest

logger = structlog.get_logger()


class GiteaManager:
    """Gestionnaire pour l'API Gitea"""
    
    def __init__(self):
        self.base_url = settings.gitea_url
        self.token = settings.gitea_token
        self.headers = {
            'Authorization': f'token {self.token}',
            'Content-Type': 'application/json'
        }
    
    async def get_file_content(
        self, 
        owner: str, 
        repo: str, 
        path: str, 
        ref: str = "main"
    ) -> Optional[str]:
        """Récupère le contenu d'un fichier depuis Gitea"""
        try:
            url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/contents/{path}"
            params = {'ref': ref}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Le contenu est en base64
                        import base64
                        content = base64.b64decode(data['content']).decode('utf-8')
                        logger.info("file_retrieved", path=path, repo=repo)
                        return content
                    elif response.status == 404:
                        logger.warning("file_not_found", path=path, repo=repo)
                        return None
                    else:
                        error = await response.text()
                        logger.error("file_retrieval_failed", status=response.status, error=error)
                        return None
                        
        except Exception as e:
            logger.error("get_file_content_failed", error=str(e), path=path)
            raise
    
    async def parse_deployment_manifest(
        self, 
        owner: str, 
        repo: str, 
        manifest_path: str = "deployments/manifest.yaml",
        ref: str = "main"
    ) -> Optional[DeploymentManifest]:
        """Parse un manifeste de déploiement depuis Gitea"""
        try:
            content = await self.get_file_content(owner, repo, manifest_path, ref)
            
            if not content:
                return None
            
            # Parser le YAML
            manifest_data = yaml.safe_load(content)
            
            # Créer le modèle Pydantic
            manifest = DeploymentManifest(**manifest_data)
            logger.info("manifest_parsed", deployment_type=manifest.deployment_type.value)
            
            return manifest
            
        except Exception as e:
            logger.error("parse_manifest_failed", error=str(e), path=manifest_path)
            raise
    
    async def get_changed_files(
        self, 
        owner: str, 
        repo: str, 
        commit_sha: str
    ) -> List[str]:
        """Récupère la liste des fichiers modifiés dans un commit"""
        try:
            url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/git/commits/{commit_sha}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        files = data.get('files', [])
                        changed_files = [f['filename'] for f in files]
                        logger.info("changed_files_retrieved", commit=commit_sha[:7], count=len(changed_files))
                        return changed_files
                    else:
                        logger.error("get_changed_files_failed", status=response.status)
                        return []
                        
        except Exception as e:
            logger.error("get_changed_files_error", error=str(e), commit=commit_sha)
            return []
    
    async def detect_deployment_changes(
        self, 
        owner: str, 
        repo: str, 
        commit_sha: str
    ) -> Dict[str, Any]:
        """Détecte les changements de déploiement dans un commit"""
        try:
            changed_files = await self.get_changed_files(owner, repo, commit_sha)
            
            deployment_changes = {
                'manifests': [],
                'vm_configs': [],
                'container_configs': [],
                'cloud_init': [],
                'compose_files': []
            }
            
            for file_path in changed_files:
                path = Path(file_path)
                
                if 'manifest' in file_path.lower() and path.suffix in ['.yaml', '.yml']:
                    deployment_changes['manifests'].append(file_path)
                
                elif 'vm' in file_path.lower() or 'virtual-machine' in file_path.lower():
                    deployment_changes['vm_configs'].append(file_path)
                
                elif 'container' in file_path.lower() or 'docker' in file_path.lower():
                    deployment_changes['container_configs'].append(file_path)
                
                elif 'cloud-init' in file_path.lower() or 'user-data' in file_path.lower():
                    deployment_changes['cloud_init'].append(file_path)
                
                elif 'compose' in file_path.lower() and path.suffix in ['.yaml', '.yml']:
                    deployment_changes['compose_files'].append(file_path)
            
            logger.info("deployment_changes_detected", changes=deployment_changes)
            return deployment_changes
            
        except Exception as e:
            logger.error("detect_deployment_changes_failed", error=str(e))
            raise
    
    async def get_repository_info(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'un dépôt"""
        try:
            url = f"{self.base_url}/api/v1/repos/{owner}/{repo}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("repository_info_retrieved", repo=repo)
                        return data
                    else:
                        logger.error("get_repository_info_failed", status=response.status)
                        return None
                        
        except Exception as e:
            logger.error("get_repository_info_error", error=str(e), repo=repo)
            return None
    
    async def create_commit_status(
        self,
        owner: str,
        repo: str,
        sha: str,
        state: str,
        description: str,
        context: str = "deployment-orchestrator"
    ):
        """Crée un statut de commit dans Gitea"""
        try:
            url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/statuses/{sha}"
            
            data = {
                'state': state,  # pending, success, error, failure
                'description': description,
                'context': context
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=self.headers, json=data) as response:
                    if response.status in [200, 201]:
                        logger.info("commit_status_created", sha=sha[:7], state=state)
                    else:
                        error = await response.text()
                        logger.error("create_commit_status_failed", status=response.status, error=error)
                        
        except Exception as e:
            logger.error("create_commit_status_error", error=str(e))


# Instance globale
gitea = GiteaManager()
