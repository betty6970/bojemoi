"""Docker Swarm client"""
import docker
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class DockerSwarmClient:
    """Client for interacting with Docker Swarm"""
    
    def __init__(self, base_url: str = "unix:///var/run/docker.sock"):
        """
        Initialize Docker Swarm client
        
        Args:
            base_url: Docker daemon URL
        """
        self.base_url = base_url
        self.client = docker.DockerClient(base_url=base_url)
    
    async def create_service(
        self,
        name: str,
        image: str,
        replicas: int = 1,
        environment: Optional[Dict[str, str]] = None,
        ports: Optional[List[str]] = None,
        networks: Optional[List[str]] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create a service on Docker Swarm
        
        Args:
            name: Service name
            image: Docker image
            replicas: Number of replicas
            environment: Environment variables
            ports: Port mappings (e.g., ['80:80'])
            networks: Networks to attach
            labels: Service labels
        
        Returns:
            Service ID
        """
        try:
            logger.info(f"Creating Docker service: {name}")
            
            # Parse port mappings
            endpoint_spec = None
            if ports:
                port_list = []
                for port_mapping in ports:
                    if ':' in port_mapping:
                        published, target = port_mapping.split(':')
                        port_list.append({
                            'Protocol': 'tcp',
                            'PublishedPort': int(published),
                            'TargetPort': int(target)
                        })
                
                if port_list:
                    endpoint_spec = docker.types.EndpointSpec(ports=port_list)
            
            # Create service
            service = self.client.services.create(
                image=image,
                name=name,
                env=environment or {},
                labels=labels or {},
                networks=networks or [],
                endpoint_spec=endpoint_spec,
                mode=docker.types.ServiceMode('replicated', replicas=replicas)
            )
            
            service_id = service.id
            logger.info(f"Service {name} created successfully: {service_id}")
            
            return service_id
            
        except Exception as e:
            logger.error(f"Failed to create service {name}: {e}")
            raise
    
    async def delete_service(self, service_id: str) -> bool:
        """
        Delete a service
        
        Args:
            service_id: Service ID or name
        
        Returns:
            True if successful
        """
        try:
            logger.info(f"Deleting Docker service: {service_id}")
            
            service = self.client.services.get(service_id)
            service.remove()
            
            logger.info(f"Service {service_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete service {service_id}: {e}")
            raise
    
    async def get_service_info(self, service_id: str) -> Dict[str, Any]:
        """
        Get service information
        
        Args:
            service_id: Service ID or name
        
        Returns:
            Service information dictionary
        """
        try:
            service = self.client.services.get(service_id)
            
            attrs = service.attrs
            
            return {
                "id": attrs['ID'],
                "name": attrs['Spec']['Name'],
                "image": attrs['Spec']['TaskTemplate']['ContainerSpec']['Image'],
                "replicas": attrs['Spec']['Mode'].get('Replicated', {}).get('Replicas', 0),
                "created_at": attrs['CreatedAt'],
                "updated_at": attrs['UpdatedAt']
            }
            
        except Exception as e:
            logger.error(f"Failed to get service info {service_id}: {e}")
            raise
    
    async def list_services(self) -> List[Dict[str, Any]]:
        """
        List all services
        
        Returns:
            List of service information
        """
        try:
            services = self.client.services.list()
            
            return [
                {
                    "id": s.id,
                    "name": s.name,
                    "image": s.attrs['Spec']['TaskTemplate']['ContainerSpec']['Image']
                }
                for s in services
            ]
            
        except Exception as e:
            logger.error(f"Failed to list services: {e}")
            raise
    
    async def ping(self) -> bool:
        """
        Check if Docker daemon is accessible
        
        Returns:
            True if accessible, False otherwise
        """
        try:
            info = self.client.info()
            
            # Check if Swarm is active
            swarm_active = info.get('Swarm', {}).get('LocalNodeState') == 'active'
            
            if swarm_active:
                logger.info("Docker Swarm connection OK")
                return True
            else:
                logger.warning("Docker daemon accessible but Swarm not active")
                return False
                
        except Exception as e:
            logger.error(f"Docker ping failed: {e}")
            return False
    
    async def close(self):
        """Close client connection"""
        try:
            self.client.close()
            logger.info("Docker client closed")
        except Exception as e:
            logger.error(f"Error closing Docker client: {e}")
