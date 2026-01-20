import docker
import structlog
from typing import Dict, Any, Optional, List
from config import settings
from models import ContainerDeploymentConfig, SwarmServiceConfig

logger = structlog.get_logger()


class DockerManager:
    """Gestionnaire Docker pour containers et Swarm"""
    
    def __init__(self):
        self.client: Optional[docker.DockerClient] = None
        self.swarm_enabled = settings.docker_swarm_enabled
    
    def connect(self):
        """Établit la connexion au daemon Docker"""
        try:
            if settings.docker_host:
                self.client = docker.DockerClient(base_url=settings.docker_host)
            else:
                self.client = docker.from_env()
            
            # Vérifier la connexion
            self.client.ping()
            
            # Vérifier si Swarm est actif
            if self.swarm_enabled:
                try:
                    self.client.swarm.attrs
                    logger.info("docker_connected", swarm=True)
                except docker.errors.APIError:
                    logger.warning("docker_connected_swarm_not_active", swarm=False)
                    self.swarm_enabled = False
            else:
                logger.info("docker_connected", swarm=False)
                
        except Exception as e:
            logger.error("docker_connection_failed", error=str(e))
            raise
    
    def disconnect(self):
        """Ferme la connexion Docker"""
        if self.client:
            self.client.close()
            logger.info("docker_disconnected")
    
    def pull_image(self, image: str, tag: str = "latest") -> str:
        """Pull une image Docker"""
        try:
            full_image = f"{image}:{tag}"
            logger.info("pulling_image", image=full_image)
            
            self.client.images.pull(image, tag=tag)
            logger.info("image_pulled", image=full_image)
            
            return full_image
            
        except Exception as e:
            logger.error("pull_image_failed", error=str(e), image=image, tag=tag)
            raise
    
    def deploy_container(self, config: ContainerDeploymentConfig) -> Dict[str, Any]:
        """Déploie un container standalone"""
        container = None
        
        try:
            self.connect()
            
            # Pull de l'image
            full_image = self.pull_image(config.image, config.tag)
            
            # Préparation des ports
            ports = {}
            if config.ports:
                for port_mapping in config.ports:
                    if ':' in port_mapping:
                        host_port, container_port = port_mapping.split(':')
                        ports[container_port] = host_port
                    else:
                        ports[port_mapping] = port_mapping
            
            # Préparation des volumes
            volumes = {}
            if config.volumes:
                for volume in config.volumes:
                    if ':' in volume:
                        host_path, container_path = volume.split(':', 1)
                        mode = 'rw'
                        if ':' in container_path:
                            container_path, mode = container_path.rsplit(':', 1)
                        volumes[host_path] = {'bind': container_path, 'mode': mode}
            
            # Labels avec métadonnées
            labels = config.labels or {}
            labels.update({
                'bojemoi.environment': config.environment.value,
                'bojemoi.managed': 'true',
                'bojemoi.deployment_tool': 'orchestrator'
            })
            
            # Vérifier si un container avec ce nom existe déjà
            try:
                existing = self.client.containers.get(config.name)
                logger.info("removing_existing_container", container=config.name)
                existing.stop()
                existing.remove()
            except docker.errors.NotFound:
                pass
            
            # Créer et démarrer le container
            container = self.client.containers.run(
                image=full_image,
                name=config.name,
                environment=config.env_vars or {},
                ports=ports,
                volumes=volumes,
                network=config.networks[0] if config.networks else None,
                restart_policy={'Name': config.restart_policy},
                labels=labels,
                detach=True
            )
            
            logger.info("container_deployed", container=config.name, id=container.short_id)
            
            return {
                'container_id': container.id,
                'container_name': config.name,
                'status': 'running',
                'image': full_image
            }
            
        except Exception as e:
            logger.error("deploy_container_failed", error=str(e), container=config.name)
            if container:
                try:
                    container.stop()
                    container.remove()
                except:
                    pass
            raise
            
        finally:
            self.disconnect()
    
    def deploy_swarm_service(self, config: SwarmServiceConfig) -> Dict[str, Any]:
        """Déploie un service Docker Swarm"""
        try:
            self.connect()
            
            if not self.swarm_enabled:
                raise Exception("Docker Swarm is not enabled")
            
            # Pull de l'image
            full_image = self.pull_image(config.image, config.tag)
            
            # Préparation des ports (endpoint_spec)
            ports = []
            if config.ports:
                for port_mapping in config.ports:
                    if ':' in port_mapping:
                        published, target = port_mapping.split(':')
                        ports.append({
                            'PublishedPort': int(published),
                            'TargetPort': int(target),
                            'Protocol': 'tcp'
                        })
            
            # Préparation des labels
            labels = config.labels or {}
            labels.update({
                'bojemoi.environment': config.environment.value,
                'bojemoi.managed': 'true',
                'bojemoi.deployment_tool': 'orchestrator'
            })
            
            # Préparation de la configuration de mise à jour
            update_config = config.update_config or {
                'parallelism': 1,
                'delay': 10,
                'failure_action': 'rollback'
            }
            
            # Vérifier si le service existe déjà
            existing_service = None
            try:
                existing_service = self.client.services.get(config.name)
                logger.info("updating_existing_service", service=config.name)
            except docker.errors.NotFound:
                logger.info("creating_new_service", service=config.name)
            
            # Créer ou mettre à jour le service
            if existing_service:
                # Mise à jour du service existant
                existing_service.update(
                    image=full_image,
                    env=config.env_vars or {},
                    endpoint_spec={'Ports': ports} if ports else None,
                    networks=config.networks,
                    constraints=config.constraints,
                    labels=labels
                )
                service = existing_service
            else:
                # Création d'un nouveau service
                service = self.client.services.create(
                    image=full_image,
                    name=config.name,
                    env=config.env_vars or {},
                    endpoint_spec={'Ports': ports} if ports else None,
                    networks=config.networks,
                    constraints=config.constraints,
                    labels=labels,
                    mode={'Replicated': {'Replicas': config.replicas}},
                    update_config=update_config
                )
            
            logger.info("swarm_service_deployed", service=config.name, id=service.short_id)
            
            return {
                'service_id': service.id,
                'service_name': config.name,
                'status': 'deployed',
                'image': full_image,
                'replicas': config.replicas
            }
            
        except Exception as e:
            logger.error("deploy_swarm_service_failed", error=str(e), service=config.name)
            raise
            
        finally:
            self.disconnect()
    
    def get_container_status(self, container_name: str) -> Dict[str, Any]:
        """Récupère le statut d'un container"""
        try:
            self.connect()
            container = self.client.containers.get(container_name)
            
            return {
                'id': container.id,
                'name': container.name,
                'status': container.status,
                'image': container.image.tags[0] if container.image.tags else None
            }
            
        except docker.errors.NotFound:
            return {'status': 'not_found'}
        except Exception as e:
            logger.error("get_container_status_failed", error=str(e), container=container_name)
            raise
        finally:
            self.disconnect()
    
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """Récupère le statut d'un service Swarm"""
        try:
            self.connect()
            
            if not self.swarm_enabled:
                raise Exception("Docker Swarm is not enabled")
            
            service = self.client.services.get(service_name)
            tasks = service.tasks()
            
            return {
                'id': service.id,
                'name': service.name,
                'replicas': len([t for t in tasks if t['Status']['State'] == 'running']),
                'desired_replicas': service.attrs['Spec']['Mode']['Replicated']['Replicas'],
                'image': service.attrs['Spec']['TaskTemplate']['ContainerSpec']['Image']
            }
            
        except docker.errors.NotFound:
            return {'status': 'not_found'}
        except Exception as e:
            logger.error("get_service_status_failed", error=str(e), service=service_name)
            raise
        finally:
            self.disconnect()


# Instance globale
docker_manager = DockerManager()
