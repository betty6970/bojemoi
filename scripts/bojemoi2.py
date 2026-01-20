#!/usr/bin/env python3
"""
Docker Services Manager Module

Ce module fournit des fonctions pour lister et gerer les conteneurs 
de services Docker (Swarm ).

Exemple d'utilisation:
    import bojemoi as dsm
    
    # Lister tous les services
    all_services = dsm.list_all_services()
    
    # Service specifique
    service_containers = dsm.get_swarm_service_containers("rsync-master")
    

Auteur: Generated for Docker management
Version: 1.0
"""

import docker
import json
from typing import Dict, List, Optional, Union, Any
from docker.errors import APIError, DockerException
import json
import logging
from datetime import datetime

# Configuration du client Docker global
_docker_client = None
# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_docker_client():
    """
    Retourne une instance du client Docker (singleton pattern)
    
    Returns:
        docker.DockerClient: Instance du client Docker
    """
    global _docker_client
    _docker_client = docker.from_env()
    return _docker_client



class DockerSwarmManager:
    def __init__(self, manager_url: str = 'unix://var/run/docker.sock'):
        """
        Initialise le gestionnaire Docker Swarm.
        
        Args:
            manager_url: URL de connexion au daemon Docker manager
        """
        try:
            self.client = docker.DockerClient(base_url=manager_url)
            # Vérifier que nous sommes connectés à un swarm
            self.swarm_info = self.client.swarm.attrs
            logger.info("✅ Connexion au swarm manager réussie")
        except APIError as e:
            if "This node is not a swarm manager" in str(e):
                raise Exception("Ce node n'est pas un manager de swarm Docker")
            raise e
        except Exception as e:
            raise Exception(f"Impossible de se connecter au daemon Docker manager: {e}")
    
    def get_swarm_nodes(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère la liste de tous les nodes du swarm.
        
        Returns:
            Dictionnaire des nodes indexés par ID
        """
        try:
            nodes = self.client.nodes.list()
            nodes_dict = {}
            
            for node in nodes:
                node_data = {
                    'id': node.id,
                    'hostname': node.attrs['Description']['Hostname'],
                    'role': node.attrs['Spec']['Role'],
                    'status': node.attrs['Status']['State'],
                    'availability': node.attrs['Spec']['Availability'],
                    'address': node.attrs['Status'].get('Addr', 'N/A'),
                    'engine_version': node.attrs['Description']['Engine']['EngineVersion'],
                    'labels': node.attrs['Spec'].get('Labels', {}),
                    'resources': {
                        'cpu': node.attrs['Description']['Resources']['NanoCPUs'] // 1000000000,
                        'memory_mb': node.attrs['Description']['Resources']['MemoryBytes'] // (1024*1024)
                    }
                }
                nodes_dict[node.id] = node_data
            
            return nodes_dict
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des nodes: {e}")
            return {}
    
    def get_swarm_services(self) -> List[Dict[str, Any]]:
        """
        Récupère tous les services du swarm.
        
        Returns:
            Liste des services avec leurs informations
        """
        try:
            services = self.client.services.list()
            services_info = []
            
            for service in services:
                service_data = {
                    'id': service.id,
                    'name': service.name,
                    'image': service.attrs['Spec']['TaskTemplate']['ContainerSpec']['Image'],
                    'mode': 'replicated' if 'Replicated' in service.attrs['Spec']['Mode'] else 'global',
                    'replicas': service.attrs['Spec']['Mode'].get('Replicated', {}).get('Replicas', 1),
                    'labels': service.attrs['Spec'].get('Labels', {}),
                    'created': service.attrs['CreatedAt'],
                    'updated': service.attrs['UpdatedAt']
                }
                services_info.append(service_data)
            
            return services_info
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des services: {e}")
            return []
    
    def get_swarm_tasks(self) -> List[Dict[str, Any]]:
        """
        Récupère toutes les tasks (containers) du swarm avec leur localisation.
        
        Returns:
            Liste des tasks/containers avec leurs nodes
        """
        try:
            tasks = self.client.api.tasks()
            active_tasks = []
            
            for task in tasks:
                # Ne récupérer que les tasks en cours d'exécution
                if task['Status']['State'] in ['running', 'starting']:
                    task_data = {
                        'task_id': task['ID'][:12],
                        'service_id': task['ServiceID'],
                        'node_id': task['NodeID'],
                        'container_id': task['Status']['ContainerStatus']['ContainerID'][:12] if task.get('Status', {}).get('ContainerStatus', {}).get('ContainerID') else 'N/A',
                        'desired_state': task['DesiredState'],
                        'current_state': task['Status']['State'],
                        'timestamp': task['Status']['Timestamp'],
                        'image': task['Spec']['ContainerSpec']['Image'],
                        'name': task.get('Name', f"task_{task['ID'][:8]}"),
                        'ports': self._extract_task_ports(task),
                        'networks': [net['Target'] for net in task['Spec'].get('Networks', [])],
                        'labels': task['Spec'].get('Labels', {}),
                        'env': task['Spec']['ContainerSpec'].get('Env', [])
                    }
                    active_tasks.append(task_data)
            
            return active_tasks
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tasks: {e}")
            return []
    
    def _extract_task_ports(self, task: Dict[str, Any]) -> List[str]:
        """
        Extrait les informations de ports d'une task.
        """
        ports = []
        container_spec = task.get('Spec', {}).get('ContainerSpec', {})
        
        # Ports exposés
        if 'ExposedPorts' in container_spec:
            for port in container_spec['ExposedPorts']:
                ports.append(port)
        
        # Ports publiés au niveau du service
        endpoint_spec = task.get('Spec', {}).get('EndpointSpec', {})
        if 'Ports' in endpoint_spec:
            for port_config in endpoint_spec['Ports']:
                published = port_config.get('PublishedPort', '')
                target = port_config.get('TargetPort', '')
                protocol = port_config.get('Protocol', 'tcp')
                if published and target:
                    ports.append(f"{published}:{target}/{protocol}")
        
        return ports
    
    def get_local_containers_if_manager(self) -> List[Dict[str, Any]]:
        """
        Récupère les containers locaux si nous sommes sur un node manager.
        
        Returns:
            Liste des containers locaux
        """
        try:
            containers = self.client.containers.list(all=False)
            local_containers = []
            
            for container in containers:
                try:
                    container_data = {
                        'id': container.id[:12],
                        'name': container.name,
                        'image': container.image.tags[0] if container.image.tags else container.image.id[:12],
                        'status': container.status,
                        'state': container.attrs['State']['Status'],
                        'created': container.attrs['Created'],
                        'ports': self._format_container_ports(container.ports),
                        'labels': container.labels or {},
                        'networks': list(container.attrs['NetworkSettings']['Networks'].keys()),
                        'node_type': 'local_manager',
                        'source': 'local_docker_api'
                    }
                    local_containers.append(container_data)
                except Exception as e:
                    logger.warning(f"Erreur container {container.id[:12]}: {e}")
                    continue
            
            return local_containers
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des containers locaux: {e}")
            return []
    
    def _format_container_ports(self, ports: Dict) -> List[str]:
        """
        Formate les informations de ports des containers Docker.
        """
        if not ports:
            return []
        
        formatted_ports = []
        for container_port, host_bindings in ports.items():
            if host_bindings:
                for binding in host_bindings:
                    host_port = binding.get('HostPort', '')
                    host_ip = binding.get('HostIp', '0.0.0.0')
                    formatted_ports.append(f"{host_ip}:{host_port}->{container_port}")
            else:
                formatted_ports.append(container_port)
        
        return formatted_ports
    
    def merge_containers_data(self, nodes_dict: Dict[str, Dict], services: List[Dict], 
                            tasks: List[Dict], local_containers: List[Dict]) -> Dict[str, Any]:
        """
        Fusionne les données des services, tasks et containers locaux.
        
        Args:
            nodes_dict: Dictionnaire des nodes
            services: Liste des services
            tasks: Liste des tasks
            local_containers: Containers locaux
            
        Returns:
            Structure complète des données
        """
        # Créer un mapping service_id -> service_info
        services_map = {s['id']: s for s in services}
        
        # Traiter les tasks (containers de services)
        containers_by_node = {}
        all_containers = []
        
        for task in tasks:
            node_id = task['node_id']
            if node_id not in nodes_dict:
                continue
            
            node_info = nodes_dict[node_id]
            service_info = services_map.get(task['service_id'], {})
            
            container = {
                'id': task['container_id'],
                'name': f"{service_info.get('name', 'unknown')}_{task['task_id']}",
                'image': task['image'],
                'status': task['current_state'],
                'created': task['timestamp'],
                'node_id': node_id,
                'node_hostname': node_info['hostname'],
                'node_role': node_info['role'],
                'node_address': node_info['address'],
                'service_name': service_info.get('name', 'unknown'),
                'service_mode': service_info.get('mode', 'unknown'),
                'ports': task['ports'],
                'networks': task['networks'],
                'labels': {**service_info.get('labels', {}), **task['labels']},
                'source': 'swarm_task'
            }
            
            if node_id not in containers_by_node:
                containers_by_node[node_id] = []
            containers_by_node[node_id].append(container)
            all_containers.append(container)
        
        # Ajouter les containers locaux
        for container in local_containers:
            # Essayer de déterminer sur quel node nous sommes
            current_node = None
            for node in nodes_dict.values():
                if node['role'] == 'manager':  # Supposer que nous sommes sur un manager
                    current_node = node
                    break
            
            if current_node:
                container['node_id'] = current_node['id']
                container['node_hostname'] = current_node['hostname']
                container['node_role'] = current_node['role']
                container['node_address'] = current_node['address']
                
                if current_node['id'] not in containers_by_node:
                    containers_by_node[current_node['id']] = []
                containers_by_node[current_node['id']].append(container)
                all_containers.append(container)
        
        # Construire le résultat final
        result = {
            'swarm_info': {
                'total_nodes': len(nodes_dict),
                'total_services': len(services),
                'total_containers': len(all_containers),
                'scan_timestamp': datetime.now().isoformat()
            },
            'nodes': [],
            'all_containers': all_containers
        }
        
        # Organiser par nodes
        for node_id, node_info in nodes_dict.items():
            containers = containers_by_node.get(node_id, [])
            node_data = {
                'node_info': node_info,
                'containers': containers,
                'container_count': len(containers)
            }
            result['nodes'].append(node_data)
        
        return result
    
    def get_all_active_containers(self) -> Dict[str, Any]:
        """
        Récupère tous les containers actifs via l'API Swarm manager.
        """
        logger.info("� Récupération des informations du swarm...")
        
        # Récupérer les informations via l'API manager
        nodes_dict = self.get_swarm_nodes()
        services = self.get_swarm_services()
        tasks = self.get_swarm_tasks()
        local_containers = self.get_local_containers_if_manager()
        
        logger.info(f"� Trouvé: {len(nodes_dict)} nodes, {len(services)} services, {len(tasks)} tasks actives")
        
        # Fusionner toutes les données
        result = self.merge_containers_data(nodes_dict, services, tasks, local_containers)
        
        return result
    
    def display_containers_table(self, data: Dict[str, Any]) -> None:
        """
        Affiche les containers sous forme de tableau lisible.
        """
        print("\n" + "="*130)
        print("� CONTAINERS ACTIFS SUR LE SWARM DOCKER (via Manager API)")
        print("="*130)
        
        swarm_info = data['swarm_info']
        print(f"\n� Résumé du Swarm:")
        print(f"   • {swarm_info['total_containers']} containers/tasks actifs")
        print(f"   • {swarm_info['total_services']} services déployés")
        print(f"   • {swarm_info['total_nodes']} nodes dans le swarm")
        print(f"   • Scan effectué: {swarm_info['scan_timestamp']}")
        
        for node_data in data['nodes']:
            node = node_data['node_info']
            containers = node_data['containers']
            
            role_icon = "�" if node['role'] == 'manager' else "⚙️"
            status_icon = "�" if node['status'] == 'ready' else "�"
            
            print(f"\n{role_icon} {status_icon} NODE: {node['hostname']} ({node['role'].upper()})")
            print(f"    � ID: {node['id'][:12]} | Adresse: {node['address']}")
            print(f"    � CPU: {node['resources']['cpu']} cores | RAM: {node['resources']['memory_mb']} MB")
            print(f"    � Containers/Tasks: {len(containers)}")
            
            if containers:
                print(f"\n    CONTAINERS/TASKS ACTIFS:")
                print("    " + "-"*120)
                print(f"    {'ID':<12} {'NAME':<30} {'IMAGE':<40} {'STATUS':<12} {'SOURCE':<12}")
                print("    " + "-"*120)
                
                for container in containers:
                    source_icon = "�" if container['source'] == 'swarm_task' else "�"
                    print(f"    {container['id']:<12} {container['name'][:29]:<30} "
                          f"{container['image'][:39]:<40} {container['status']:<12} "
                          f"{source_icon}{container['source']:<11}")
                
                # Afficher les services uniques sur ce node
                services_on_node = set(c.get('service_name', 'N/A') for c in containers if c.get('service_name'))
                if services_on_node and 'N/A' not in services_on_node:
                    print(f"\n    � Services: {', '.join(sorted(services_on_node))}")
            else:
                print("    ℹ️  Aucun container/task actif")
        
        print("\n" + "="*130)

def main():
    """
    Fonction principale du script.
    """
    try:
        print("� Initialisation du gestionnaire Docker Swarm...")
        
        # Connexion au manager
        swarm_manager = DockerSwarmManager()
        
        print("� Récupération des containers via l'API Manager...")
        
        # Récupérer tous les containers actifs
        containers_data = swarm_manager.get_all_active_containers()
        
        # Afficher les résultats
        swarm_manager.display_containers_table(containers_data)
        
        # Sauvegarder en JSON si demandé
        save_json = input("\n� Sauvegarder les résultats en JSON? (y/N): ").lower().strip()
        if save_json == 'y':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"docker_swarm_containers_{timestamp}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(containers_data, f, indent=2, ensure_ascii=False, default=str)
            print(f"✅ Résultats sauvegardés dans: {filename}")
        
        # Retourner le tableau simple des containers
        return containers_data['all_containers']
        
    except Exception as e:
        logger.error(f"❌ Erreur dans le script principal: {e}")
        return []

def get_containers_array(manager_url: str = 'unix://var/run/docker.sock') -> List[Dict[str, Any]]:
    """
    Fonction utilitaire pour récupérer directement un tableau de tous les containers.
    
    Args:
        manager_url: URL de connexion au manager Docker
        
    Returns:
        Liste simple de tous les containers actifs avec informations de node
    """
    try:
        swarm_manager = DockerSwarmManager(manager_url)
        data = swarm_manager.get_all_active_containers()
        return data['all_containers']
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création du tableau: {e}")
        return []

def analyze_containers_by_node(containers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyse les containers par node pour des statistiques.
    
    Args:
        containers: Liste des containers
        
    Returns:
        Statistiques par node
    """
    from collections import defaultdict, Counter
    
    stats = {
        'by_node': defaultdict(list),
        'by_service': Counter(),
        'by_status': Counter(),
        'by_image': Counter()
    }
    
    for container in containers:
        # Par node
        node_key = f"{container['node_hostname']} ({container['node_role']})"
        stats['by_node'][node_key].append(container)
        
        # Par service
        service_name = container.get('service_name', container.get('name', 'unknown'))
        stats['by_service'][service_name] += 1
        
        # Par statut
        stats['by_status'][container['status']] += 1
        
        # Par image
        image_name = container['image'].split(':')[0]  # Enlever le tag
        stats['by_image'][image_name] += 1
    
    return dict(stats)

if __name__ == "__main__":
    # Configuration
    DOCKER_MANAGER_URL = 'unix://var/run/docker.sock'  # ou tcp://manager-ip:2376
    
    # Exécuter le script
    containers_array = main()
    
    if containers_array:
        print(f"\n� Tableau Python créé avec {len(containers_array)} containers")
        
        # Analyse rapide
        print("\n� Analyse rapide:")
        stats = analyze_containers_by_node(containers_array)
        
        print("   � Containers par node:")
        for node, containers in stats['by_node'].items():
            print(f"     • {node}: {len(containers)} containers")
        
        print("   � Top 5 services:")
        for service, count in stats['by_service'].most_common(5):
            print(f"     • {service}: {count} instances")
        
        print("\n� Usage du tableau:")
        print("   # Filtrer par node:")
       
≠===≠==≠≠======≠===≠====≠≠

    def get_node_info(node_id: Optional[str] = None, node_name: Optional[str] = None) -> Dict[str, Any]:
       """
       Obtient les informations détaillées d'un node Docker Swarm.
    
       Args:
           node_id (str, optional): ID du node à récupérer
           node_name (str, optional): Nom du node à récupérer
        
       Returns:
           Dict[str, Any]: Dictionnaire contenant toutes les informations du node
        
       Raises:
           docker.errors.NotFound: Si le node n'existe pas
           docker.errors.APIError: Si erreur API Docker
           ValueError: Si aucun identifiant n'est fourni
       """
    
       # Vérifier qu'au moins un identifiant est fourni
       if not node_id and not node_name:
           raise ValueError("Vous devez fournir soit node_id soit node_name")
    
       try:
           # Créer le client Docker
           client = docker.from_env()
        
           # Si on a le node_id, l'utiliser directement
           if node_id:
               node = client.nodes.get(node_id)
           else:
               # Sinon, chercher par nom
               nodes = client.nodes.list()
               node = None
               for n in nodes:
                   if n.attrs.get('Description', {}).get('Hostname') == node_name:
                       node = n
                       break
            
               if not node:
                   raise docker.errors.NotFound(f"Node avec le nom '{node_name}' introuvable")
        
           # Extraire les informations importantes
           node_info = {
               "id": node.id,
               "version": node.version,
               "created_at": node.attrs.get('CreatedAt'),
               "updated_at": node.attrs.get('UpdatedAt'),
               "spec": node.attrs.get('Spec', {}),
               "description": node.attrs.get('Description', {}),
               "status": node.attrs.get('Status', {}),
               "manager_status": node.attrs.get('ManagerStatus'),
           }
        
           # Informations détaillées du node
           description = node_info['description']
           spec = node_info['spec']
           status = node_info['status']
        
           # Informations formatées
           formatted_info = {
               # Identification
               "id": node_info['id'],
               "hostname": description.get('Hostname', 'Unknown'),
               "role": spec.get('Role', 'Unknown'),
               "availability": spec.get('Availability', 'Unknown'),
            
               # Statut
               "state": status.get('State', 'Unknown'),
               "message": status.get('Message', ''),
               "addr": status.get('Addr', 'Unknown'),
            
               # Informations système
               "architecture": description.get('Platform', {}).get('Architecture', 'Unknown'),
               "os": description.get('Platform', {}).get('OS', 'Unknown'),
            
               # Ressources
               "nano_cpus": description.get('Resources', {}).get('NanoCPUs', 0),
               "memory_bytes": description.get('Resources', {}).get('MemoryBytes', 0),
            
               # Labels
               "labels": spec.get('Labels', {}),
            
               # Informations moteur Docker
               "engine_version": description.get('Engine', {}).get('EngineVersion', 'Unknown'),
               "plugins": description.get('Engine', {}).get('Plugins', []),
            
               # Dates
               "created_at": node_info['created_at'],
               "updated_at": node_info['updated_at'],
            
               # Statut manager (si applicable)
               "is_manager": node_info['manager_status'] is not None,
               "leader": node_info['manager_status'].get('Leader', False) if node_info['manager_status'] else False,
               "reachability": node_info['manager_status'].get('Reachability') if node_info['manager_status'] else None,
            
               # Données complètes brutes
               "raw_attrs": node.attrs
           }
        
           return formatted_info
        
       except docker.errors.NotFound as e:
           raise docker.errors.NotFound(f"Node introuvable: {e}")
       except docker.errors.APIError as e:
           raise docker.errors.APIError(f"Erreur API Docker: {e}")
       except Exception as e:
           raise Exception(f"Erreur inattendue: {e}")


    def list_all_nodes() -> list:
       """
       Liste tous les nodes du cluster Swarm avec leurs informations de base.
    
       Returns:
           list: Liste des informations de base de tous les nodes
       """
       try:
           client = docker.from_env()
           nodes = client.nodes.list()
        
           nodes_info = []
           for node in nodes:
               basic_info = {
                   "id": node.id,
                   "hostname": node.attrs.get('Description', {}).get('Hostname', 'Unknown'),
                   "role": node.attrs.get('Spec', {}).get('Role', 'Unknown'),
                   "availability": node.attrs.get('Spec', {}).get('Availability', 'Unknown'),
                   "state": node.attrs.get('Status', {}).get('State', 'Unknown'),
                   "is_manager": node.attrs.get('ManagerStatus') is not None,
                   "leader": node.attrs.get('ManagerStatus', {}).get('Leader', False)
               }
               nodes_info.append(basic_info)
            
           return nodes_info
        
       except Exception as e:
           raise Exception(f"Erreur lors de la récupération des nodes: {e}")


    
    def get_swarm_service_containers(self, service_name: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        Recupere les conteneurs des services Docker Swarm
        
        Args:
            service_name (str, optional): Nom du service a filtrer
        
        Returns:
            Dict[str, List[Dict]]: Services et leurs conteneurs
        """
        services_containers = {}
        
        try:
            services = self.client.services.list()
            
            for service in services:
                current_service_name = service.name
                
                if service_name and service_name not in current_service_name:
                    continue
                
                # Recupere les taches du service
                tasks = service.tasks()
                service_containers = []
                
                for task in tasks:
                    container_info = self._extract_task_container_info(task)
                    if container_info:
                        service_containers.append(container_info)
                
                services_containers[current_service_name] = service_containers
        
        except docker.errors.APIError as e:
            raise RuntimeError("Erreur lors de la recuperation des conteneurs Swarm: {}".format(e))
        
        return services_containers
    
    
    def get_all_service_containers(self, service_name: Optional[str] = None) -> Dict[str, Dict]:
        """
        Recupere tous les conteneurs de services (Swarm )
        
        Args:
            service_name (str, optional): Nom du service a filtrer
        
        Returns:
            Dict[str, Dict]: Conteneurs Swarm et Compose
        """
        return {
            'swarm': self.get_swarm_service_containers(service_name),
        }
    
    def _format_service_info(self, service) -> Dict:
        """
        Formate les informations d'un service Swarm
        
        Args:
            service: Objet service Docker
        
        Returns:
            Dict: Informations formatees du service
        """
        spec = service.attrs.get('Spec', {})
        return {
            'id': service.short_id,
            'name': service.name,
            'mode': spec.get('Mode', {}),
            'replicas': self._get_replica_info(spec),
            'image': spec.get('TaskTemplate', {}).get('ContainerSpec', {}).get('Image', 'N/A'),
            'created': service.attrs.get('CreatedAt', 'N/A'),
            'updated': service.attrs.get('UpdatedAt', 'N/A')
        }
    
    def _get_replica_info(self, spec: Dict) -> Dict:
        """
        Extrait les informations de replicas d'un service
        
        Args:
            spec (Dict): Specification du service
        
        Returns:
            Dict: Informations des replicas
        """
        mode = spec.get('Mode', {})
        if 'Replicated' in mode:
            return {
                'mode': 'replicated',
                'replicas': mode['Replicated'].get('Replicas', 0)
            }
        elif 'Global' in mode:
            return {
                'mode': 'global',
                'replicas': 'N/A'
            }
        return {'mode': 'unknown', 'replicas': 0}
    
    def _extract_task_container_info(self, task: Dict) -> Optional[Dict]:
        """
        Extrait les informations d'un conteneur depuis une tache Swarm
        
        Args:
            task (Dict): Tache Swarm
        
        Returns:
            Optional[Dict]: Informations du conteneur ou None
        """
        task_status = task.get('Status', {})
        task_state = task_status.get('State', 'unknown')
        container_status = task_status.get('ContainerStatus', {})
        container_id = container_status.get('ContainerID', '')
        
        if not container_id:
            return None
        
        try:
            container = self.client.containers.get(container_id)
            return {
                'task_id': task.get('ID', ''),
                'container_id': container.short_id,
                'container_name': container.name,
                'status': container.status,
                'state': task_state,
                'node_id': task.get('NodeID', 'unknown'),
                'image': container.image.tags[0] if container.image.tags else 'N/A',
                'created': str(container.attrs.get('Created', 'N/A')),
                'slot': task.get('Slot', 0)
            }
        except docker.errors.NotFound:
            # Conteneur sur un autre noeud
            return {
                'task_id': task.get('ID', ''),
                'container_id': container_id[:12],
                'container_name': 'N/A (remote)',
                'status': 'remote',
                'state': task_state,
                'node_id': task.get('NodeID', 'unknown'),
                'image': 'N/A',
                'created': 'N/A',
                'slot': task.get('Slot', 0)
            }
    

# Instance globale du gestionnaire
_manager = None

def get_manager() -> DockerServicesManager:
    """
    Retourne une instance globale du gestionnaire (singleton pattern)
    
    Returns:
        DockerServicesManager: Instance du gestionnaire
    """
    global _manager
    if _manager is None:
        _manager = DockerServicesManager()
    return _manager

# Fonctions d'API publique (raccourcis)
def list_swarm_services(service_name: Optional[str] = None) -> List[Dict]:
    """
    Liste les services Docker Swarm
    
    Args:
        service_name (str, optional): Nom du service a filtrer
    
    Returns:
        List[Dict]: Liste des services
    """
    return get_manager().get_swarm_services(service_name)

def get_swarm_service_containers(service_name: Optional[str] = None) -> Dict[str, List[Dict]]:
    """
    Recupere les conteneurs des services Swarm
    
    Args:
        service_name (str, optional): Nom du service a filtrer
    
    Returns:
        Dict[str, List[Dict]]: Services et leurs conteneurs
    """
    return get_manager().get_swarm_service_containers(service_name)


def list_all_services(service_name: Optional[str] = None) -> Dict[str, Dict]:
    """
    Liste tous les services (Swarm )
    
    Args:
        service_name (str, optional): Nom du service a filtrer
    
    Returns:
        Dict[str, Dict]: Tous les services et conteneurs
    """
    return get_manager().get_all_service_containers(service_name)

def print_services_summary(services_data: Dict[str, Dict]) -> None:
    """
    Affiche un resume des services
    
    Args:
        services_data (Dict): Donnees des services
    """
    swarm_services = services_data.get('swarm', {})
    
    print("=" * 50)
    print("RESUME DES SERVICES DOCKER")
    print("=" * 50)
    print("Services Swarm: {}".format(len(swarm_services)))
    
    total_containers = 0
    total_containers += sum(len(containers) for containers in swarm_services.values())
    
    print("Total conteneurs: {}".format(total_containers))
    
    # Detail par service
    for service_name, containers in swarm_services.items():
        print("  [SWARM] {}: {} conteneurs".format(service_name, len(containers)))
    

# Point d'entree pour tests
if __name__ == "__main__":
    # Exemple d'utilisation du module
    try:
        print("Test du module Docker Services Manager")
        print("=" * 50)
        
        # Test des services
        all_services = list_all_services()
        print_services_summary(all_services)
        
        # Test service specifique
        services_containers = get_swarm_service_containers("rsync-master")
        if services_containers:
            print("\nServices 'rsync' trouves: {}".format(len(services_containers)))
        
    except Exception as e:
        print("Erreur lors du test: {}".format(e))

