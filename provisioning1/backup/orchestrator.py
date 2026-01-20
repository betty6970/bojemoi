import structlog
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from config import settings
from models import (
    DeploymentManifest, DeploymentRecord, DeploymentStatus, 
    DeploymentType, VMDeploymentConfig, ContainerDeploymentConfig,
    SwarmServiceConfig
)
from database import db
from xenserver import xenserver
from docker_manager import docker_manager
from gitea_manager import gitea

logger = structlog.get_logger()


class DeploymentOrchestrator:
    """Orchestrateur principal des déploiements"""
    
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Traite un webhook Gitea et déclenche les déploiements"""
        try:
            # Extraire les informations du webhook
            ref = webhook_data.get('ref', '')
            branch = ref.split('/')[-1] if '/' in ref else ref
            repository = webhook_data.get('repository', {})
            repo_name = repository.get('name')
            repo_owner = repository.get('owner', {}).get('username')
            commits = webhook_data.get('commits', [])
            
            if not commits:
                logger.info("no_commits_in_webhook")
                return {'status': 'skipped', 'reason': 'no commits'}
            
            head_commit = commits[-1]
            commit_sha = head_commit.get('id')
            
            logger.info(
                "webhook_received",
                repo=repo_name,
                branch=branch,
                commit=commit_sha[:7] if commit_sha else None
            )
            
            # Détecter les changements de déploiement
            changes = await gitea.detect_deployment_changes(repo_owner, repo_name, commit_sha)
            
            results = []
            
            # Traiter les manifestes de déploiement
            for manifest_path in changes.get('manifests', []):
                try:
                    result = await self.process_manifest(
                        repo_owner,
                        repo_name,
                        manifest_path,
                        branch,
                        commit_sha
                    )
                    results.append(result)
                except Exception as e:
                    logger.error("manifest_processing_failed", error=str(e), manifest=manifest_path)
                    results.append({
                        'status': 'failed',
                        'manifest': manifest_path,
                        'error': str(e)
                    })
            
            # Si aucun manifeste, chercher le manifeste par défaut
            if not changes.get('manifests'):
                try:
                    result = await self.process_manifest(
                        repo_owner,
                        repo_name,
                        "deployments/manifest.yaml",
                        branch,
                        commit_sha
                    )
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.info("no_default_manifest", error=str(e))
            
            return {
                'status': 'processed',
                'branch': branch,
                'commit': commit_sha[:7] if commit_sha else None,
                'deployments': results
            }
            
        except Exception as e:
            logger.error("webhook_processing_failed", error=str(e))
            raise
    
    async def process_manifest(
        self,
        owner: str,
        repo: str,
        manifest_path: str,
        branch: str,
        commit_sha: str
    ) -> Optional[Dict[str, Any]]:
        """Traite un manifeste de déploiement"""
        try:
            # Récupérer et parser le manifeste
            manifest = await gitea.parse_deployment_manifest(owner, repo, manifest_path, branch)
            
            if not manifest:
                logger.warning("manifest_not_found", path=manifest_path)
                return None
            
            # Mettre à jour le statut du commit
            await gitea.create_commit_status(
                owner, repo, commit_sha,
                'pending',
                f'Déploiement {manifest.deployment_type.value} en cours...'
            )
            
            # Créer l'enregistrement de déploiement
            deployment_record = DeploymentRecord(
                deployment_type=manifest.deployment_type,
                name=self._get_deployment_name(manifest),
                environment=manifest.environment,
                status=DeploymentStatus.PENDING,
                git_commit=commit_sha,
                git_branch=branch,
                git_repository=f"{owner}/{repo}",
                config=manifest.dict()
            )
            
            deployment_id = await db.create_deployment(deployment_record)
            
            # Lancer le déploiement selon le type
            try:
                result = await self.execute_deployment(manifest, deployment_id)
                
                # Mettre à jour le statut
                await db.update_deployment_status(deployment_id, DeploymentStatus.COMPLETED)
                
                await gitea.create_commit_status(
                    owner, repo, commit_sha,
                    'success',
                    f'Déploiement {manifest.deployment_type.value} réussi'
                )
                
                return {
                    'status': 'success',
                    'deployment_id': deployment_id,
                    'type': manifest.deployment_type.value,
                    'result': result
                }
                
            except Exception as e:
                error_msg = str(e)
                await db.update_deployment_status(
                    deployment_id, 
                    DeploymentStatus.FAILED,
                    error_msg
                )
                
                await gitea.create_commit_status(
                    owner, repo, commit_sha,
                    'failure',
                    f'Déploiement échoué: {error_msg[:100]}'
                )
                
                raise
                
        except Exception as e:
            logger.error("process_manifest_failed", error=str(e), manifest=manifest_path)
            raise
    
    def _get_deployment_name(self, manifest: DeploymentManifest) -> str:
        """Extrait le nom du déploiement depuis le manifeste"""
        if manifest.vm_config:
            return manifest.vm_config.name
        elif manifest.container_config:
            return manifest.container_config.name
        elif manifest.swarm_config:
            return manifest.swarm_config.name
        else:
            return "unknown"
    
    async def execute_deployment(
        self,
        manifest: DeploymentManifest,
        deployment_id: int
    ) -> Dict[str, Any]:
        """Exécute un déploiement selon son type"""
        
        # Log de début
        await db.add_deployment_log(
            deployment_id,
            'info',
            f'Démarrage du déploiement {manifest.deployment_type.value}'
        )
        
        # Mettre à jour le statut
        await db.update_deployment_status(deployment_id, DeploymentStatus.IN_PROGRESS)
        
        try:
            if manifest.deployment_type == DeploymentType.VM:
                result = await self._deploy_vm(manifest, deployment_id)
            
            elif manifest.deployment_type == DeploymentType.CONTAINER:
                result = await self._deploy_container(manifest, deployment_id)
            
            elif manifest.deployment_type == DeploymentType.SWARM_SERVICE:
                result = await self._deploy_swarm_service(manifest, deployment_id)
            
            else:
                raise ValueError(f"Type de déploiement non supporté: {manifest.deployment_type}")
            
            # Log de succès
            await db.add_deployment_log(
                deployment_id,
                'info',
                f'Déploiement {manifest.deployment_type.value} terminé avec succès',
                {'result': result}
            )
            
            return result
            
        except Exception as e:
            # Log d'erreur
            await db.add_deployment_log(
                deployment_id,
                'error',
                f'Échec du déploiement: {str(e)}'
            )
            raise
    
    async def _deploy_vm(
        self,
        manifest: DeploymentManifest,
        deployment_id: int
    ) -> Dict[str, Any]:
        """Déploie une VM via XenServer"""
        if not manifest.vm_config:
            raise ValueError("Configuration VM manquante dans le manifeste")
        
        await db.add_deployment_log(
            deployment_id,
            'info',
            f'Déploiement VM: {manifest.vm_config.name}'
        )
        
        # Exécuter le déploiement XenServer dans un thread séparé (car sync)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            xenserver.deploy_vm,
            manifest.vm_config
        )
        
        await db.add_deployment_log(
            deployment_id,
            'info',
            f'VM déployée: {result.get("vm_ref")}'
        )
        
        return result
    
    async def _deploy_container(
        self,
        manifest: DeploymentManifest,
        deployment_id: int
    ) -> Dict[str, Any]:
        """Déploie un container Docker"""
        if not manifest.container_config:
            raise ValueError("Configuration container manquante dans le manifeste")
        
        await db.add_deployment_log(
            deployment_id,
            'info',
            f'Déploiement container: {manifest.container_config.name}'
        )
        
        # Exécuter le déploiement Docker dans un thread séparé
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            docker_manager.deploy_container,
            manifest.container_config
        )
        
        await db.add_deployment_log(
            deployment_id,
            'info',
            f'Container déployé: {result.get("container_id")}'
        )
        
        return result
    
    async def _deploy_swarm_service(
        self,
        manifest: DeploymentManifest,
        deployment_id: int
    ) -> Dict[str, Any]:
        """Déploie un service Docker Swarm"""
        if not manifest.swarm_config:
            raise ValueError("Configuration Swarm manquante dans le manifeste")
        
        await db.add_deployment_log(
            deployment_id,
            'info',
            f'Déploiement service Swarm: {manifest.swarm_config.name}'
        )
        
        # Exécuter le déploiement Swarm dans un thread séparé
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            docker_manager.deploy_swarm_service,
            manifest.swarm_config
        )
        
        await db.add_deployment_log(
            deployment_id,
            'info',
            f'Service Swarm déployé: {result.get("service_id")}'
        )
        
        return result


# Instance globale
orchestrator = DeploymentOrchestrator()
