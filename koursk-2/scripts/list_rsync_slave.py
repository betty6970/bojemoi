#!/usr/bin/env python3
import docker
import json

def list_swarm_service_containers(service_name=None):
    """
    Liste les conteneurs d'un service Docker Swarm
    
    Args:
        service_name (str): Nom du service (optionnel)
    
    Returns:
        dict: Services et leurs conteneurs
    """
    client = docker.from_env()
    services_containers = {}
    
    try:
        # Recupere tous les services Swarm
        services = client.services.list()
        
        if not services:
            print("Aucun service Docker Swarm trouve")
            return services_containers
        
        for service in services:
            current_service_name = service.name
            
            # Filtre par nom de service si specifie
            if service_name and service_name not in current_service_name:
                continue
            
            print("\n=== Service: {} ===".format(current_service_name))
            print("ID: {}".format(service.short_id))
            print("Mode: {}".format(service.attrs.get('Spec', {}).get('Mode', 'N/A')))
            
            # Recupere les taches (conteneurs) du service
            tasks = service.tasks()
            service_containers = []
            
            for task in tasks:
                task_state = task.get('Status', {}).get('State', 'unknown')
                container_id = task.get('Status', {}).get('ContainerStatus', {}).get('ContainerID', '')
                node_id = task.get('NodeID', 'unknown')
                
                if container_id:
                    try:
                        # Recupere les details du conteneur
                        container = client.containers.get(container_id)
                        container_info = {
                            'task_id': task.get('ID', ''),
                            'container_id': container.short_id,
                            'container_name': container.name,
                            'status': container.status,
                            'state': task_state,
                            'node_id': node_id,
                            'image': container.image.tags[0] if container.image.tags else 'N/A',
                            'created': str(container.attrs.get('Created', 'N/A'))
                        }
                        service_containers.append(container_info)
                        
                        print("  [CONTAINER] {} - {} ({})".format(
                            container.name, container.status, task_state))
                        
                    except docker.errors.NotFound:
                        # Conteneur non trouve localement (peut etre sur un autre noeud)
                        container_info = {
                            'task_id': task.get('ID', ''),
                            'container_id': container_id[:12],
                            'container_name': 'N/A',
                            'status': 'remote',
                            'state': task_state,
                            'node_id': node_id,
                            'image': 'N/A',
                            'created': 'N/A'
                        }
                        service_containers.append(container_info)
                        
                        print("  [REMOTE] {} - {} (noeud: {})".format(
                            container_id[:12], task_state, node_id[:12]))
            
            services_containers[current_service_name] = service_containers
            print("Total conteneurs: {}".format(len(service_containers)))
    
    except docker.errors.APIError as e:
        print("Erreur API Docker: {}".format(e))
    except Exception as e:
        print("Erreur: {}".format(e))
    
    return services_containers

def list_compose_service_containers(service_name=None, project_name=None):
    """
    Liste les conteneurs d'un service Docker Compose
    
    Args:
        service_name (str): Nom du service
        project_name (str): Nom du projet Compose
    
    Returns:
        dict: Services et leurs conteneurs
    """
    client = docker.from_env()
    services_containers = {}
    
    try:
        # Recupere tous les conteneurs
        containers = client.containers.list(all=True)
        
        for container in containers:
            labels = container.labels
            
            # Verifie si c'est un conteneur Compose
            compose_service = labels.get('com.docker.compose.service')
            compose_project = labels.get('com.docker.compose.project')
            
            if compose_service:
                # Filtre par nom de service et projet si specifies
                if service_name and service_name != compose_service:
                    continue
                if project_name and project_name != compose_project:
                    continue
                
                service_key = "{}__{}".format(compose_project or 'unknown', compose_service)
                
                if service_key not in services_containers:
                    services_containers[service_key] = []
                    print("\n=== Service Compose: {} (Projet: {}) ===".format(
                        compose_service, compose_project or 'N/A'))
                
                container_info = {
                    'container_id': container.short_id,
                    'container_name': container.name,
                    'status': container.status,
                    'image': container.image.tags[0] if container.image.tags else 'N/A',
                    'service': compose_service,
                    'project': compose_project,
                    'number': labels.get('com.docker.compose.container-number', '1'),
                    'ports': container.ports
                }
                
                services_containers[service_key].append(container_info)
                print("  [CONTAINER] {} - {} ({})".format(
                    container.name, container.status, container.image.tags[0] if container.image.tags else 'N/A'))
    
    except Exception as e:
        print("Erreur: {}".format(e))
    
    return services_containers

def list_all_service_containers(service_name=None):
    """
    Liste tous les conteneurs de services (Swarm + Compose)
    """
    print("=" * 50)
    print("RECHERCHE DE SERVICES DOCKER")
    print("=" * 50)
    
    # Swarm services
    print("\n>>> SERVICES DOCKER SWARM <<<")
    swarm_containers = list_swarm_service_containers(service_name)
    
    # Compose services
    print("\n>>> SERVICES DOCKER COMPOSE <<<")
    compose_containers = list_compose_service_containers(service_name)
    
    # Resume
    print("\n" + "=" * 50)
    print("RESUME")
    print("=" * 50)
    print("Services Swarm: {}".format(len(swarm_containers)))
    print("Services Compose: {}".format(len(compose_containers)))
    
    total_containers = sum(len(containers) for containers in swarm_containers.values())
    total_containers += sum(len(containers) for containers in compose_containers.values())
    print("Total conteneurs: {}".format(total_containers))
    
    return {
        'swarm': swarm_containers,
        'compose': compose_containers
    }

# Exemples d'utilisation
if __name__ == "__main__":
    
    # Exemple 1: Tous les services
    print("=== TOUS LES SERVICES ===")
    all_services = list_all_service_containers()
    
    # Exemple 2: Service specifique
    print("\n=== SERVICE SPECIFIQUE ===")
    web_services = list_all_service_containers("web")
    
    # Exemple 3: Service Swarm specifique
    print("\n=== SWARM UNIQUEMENT ===")
    swarm_only = list_swarm_service_containers("nginx")
    
    # Exemple 4: Service Compose specifique
    print("\n=== COMPOSE UNIQUEMENT ===")
    compose_only = list_compose_service_containers("app", "monprojet")

