import docker
from collections import defaultdict

def get_all_swarm_tasks(client=None, include_historical=False):
    """
    Obtient toutes les tâches de tous les nœuds du swarm
    
    Args:
        client: Client Docker (doit être connecté à un manager node)
        include_historical (bool): Inclure les tâches historiques (shutdown, failed, etc.)
    
    Returns:
        list: Liste de toutes les tâches du swarm
    """
    
    if client is None:
        client = docker.from_env()
    
    try:
        # MÉTHODE 1: Utiliser des filtres pour forcer la récupération globale
        if include_historical:
            # Récupérer TOUTES les tâches (y compris historiques)
            all_tasks = client.api.tasks(filters={})
        else:
            # Récupérer seulement les tâches actives de tous les états désirés
            all_tasks = client.api.tasks(filters={
                'desired-state': ['running', 'ready', 'assigned']
            })
        
        return all_tasks
        
    except docker.errors.APIError as e:
        print(f"Erreur API: {e}")
        return []

def get_tasks_by_node(client=None):
    """
    Organise toutes les tâches par nœud
    
    Returns:
        dict: Dictionnaire {node_id: [tasks]} 
    """
    
    if client is None:
        client = docker.from_env()
    
    # Récupérer tous les nœuds
    nodes = client.nodes.list()
    node_info = {node.id: node.attrs['Description']['Hostname'] for node in nodes}
    
    # Récupérer toutes les tâches
    all_tasks = get_all_swarm_tasks(client)
    
    # Organiser par nœud
    tasks_by_node = defaultdict(list)
    
    for task in all_tasks:
        node_id = task.get('NodeID')
        if node_id:
            tasks_by_node[node_id].append(task)
        else:
            # Tâches sans nœud assigné
            tasks_by_node['unassigned'].append(task)
    
    # Ajouter les noms des nœuds
    result = {}
    for node_id, tasks in tasks_by_node.items():
        if node_id == 'unassigned':
            result[node_id] = {
                'hostname': 'Non assigné',
                'tasks': tasks
            }
        else:
            result[node_id] = {
                'hostname': node_info.get(node_id, 'Nœud inconnu'),
                'tasks': tasks
            }
    
    return result

def ensure_manager_connection(client=None):
    """
    Vérifie que le client est connecté à un nœud manager
    (nécessaire pour voir toutes les tâches du swarm)
    """
    
    if client is None:
        client = docker.from_env()
    
    try:
        # Vérifier le statut du swarm
        swarm_info = client.swarm.attrs
        
        # Vérifier si c'est un manager
        node_info = client.info()
        swarm_node = node_info.get('Swarm', {})
        
        if swarm_node.get('ControlAvailable', False):
            print("✓ Connecté à un nœud manager - accès complet au swarm")
            return True
        else:
            print("⚠ Connecté à un nœud worker - vue limitée")
            print("Pour voir toutes les tâches, connectez-vous à un nœud manager")
            return False
            
    except docker.errors.APIError:
        print("✗ Pas connecté à un swarm ou erreur de connexion")
        return False

def get_all_tasks_with_subnets(client=None):
    """
    Récupère toutes les tâches du swarm avec leurs informations de subnet
    """
    
    if client is None:
        client = docker.from_env()
    
    # Vérifier la connexion manager
    if not ensure_manager_connection(client):
        return []
    
    all_tasks = get_all_swarm_tasks(client)
    tasks_with_subnets = []
    
    for task in all_tasks:
        task_id = task['ID']
        
        subnet_info = {
            'task_id': task_id,
            'task_name': task.get('Name', 'N/A'),
            'service_id': task.get('ServiceID', 'N/A'),
            'node_id': task.get('NodeID', 'N/A'),
            'state': task.get('Status', {}).get('State', 'unknown'),
            'subnets': []
        }
        
        # Extraire les subnets
        for attachment in task.get('NetworksAttachments', []):
            network = attachment.get('Network', {})
            
            for config in network.get('IPAMOptions', {}).get('Configs', []):
                if 'Subnet' in config:
                    subnet_info['subnets'].append({
                        'network_name': network.get('Spec', {}).get('Name', 'N/A'),
                        'subnet': config['Subnet'],
                        'gateway': config.get('Gateway'),
                        'task_ip': attachment.get('Addresses', [None])[0]
                    })
        
        tasks_with_subnets.append(subnet_info)
    
    return tasks_with_subnets

def display_swarm_subnet_overview(client=None):
    """
    Affiche un aperçu complet des subnets utilisés dans le swarm
    """
    
    if client is None:
        client = docker.from_env()
    
    print("APERÇU DES SUBNETS DU SWARM")
    print("="*60)
    
    # Organiser les tâches par nœud
    tasks_by_node = get_tasks_by_node(client)
    
    subnet_usage = defaultdict(list)
    
    for node_id, node_data in tasks_by_node.items():
        hostname = node_data['hostname']
        tasks = node_data['tasks']
        
        print(f"\nNœud: {hostname} ({len(tasks)} tâches)")
        print("-" * 40)
        
        for task in tasks:
            task_id = task['ID']
            task_name = task.get('Name', 'N/A')
            state = task.get('Status', {}).get('State', 'unknown')
            
            print(f"  Tâche: {task_name[:30]}... [{state}]")
            
            # Extraire et afficher les subnets
            for attachment in task.get('NetworksAttachments', []):
                network = attachment.get('Network', {})
                network_name = network.get('Spec', {}).get('Name', 'N/A')
                
                for config in network.get('IPAMOptions', {}).get('Configs', []):
                    if 'Subnet' in config:
                        subnet = config['Subnet']
                        gateway = config.get('Gateway', 'N/A')
                        task_ip = attachment.get('Addresses', ['N/A'])[0]
                        
                        print(f"    └─ {network_name}: {subnet} (IP: {task_ip})")
                        
                        # Collecter pour le résumé
                        subnet_usage[subnet].append({
                            'node': hostname,
                            'task': task_name,
                            'network': network_name
                        })
    
    # Résumé des subnets
    print(f"\n{'='*60}")
    print("RÉSUMÉ DES SUBNETS UTILISÉS")
    print(f"{'='*60}")
    
    for subnet, usage_list in subnet_usage.items():
        print(f"\nSubnet: {subnet}")
        print(f"  Utilisé par {len(usage_list)} tâche(s):")
        for usage in usage_list:
            print(f"    - {usage['task']} sur {usage['node']} (réseau: {usage['network']})")

# Fonction de connexion explicite à un manager
def connect_to_manager(manager_ip, port=2376):
    """
    Se connecte explicitement à un nœud manager pour avoir accès complet
    """
    try:
        # Connexion directe au manager
        client = docker.DockerClient(base_url=f'tcp://{manager_ip}:{port}')
        
        # Vérifier que c'est bien un manager
        node_info = client.info()
        if node_info.get('Swarm', {}).get('ControlAvailable', False):
            print(f"✓ Connexion réussie au manager {manager_ip}")
            return client
        else:
            print(f"⚠ {manager_ip} n'est pas un nœud manager")
            return None
            
    except Exception as e:
        print(f"✗ Erreur de connexion à {manager_ip}: {e}")
        return None

# Exemple d'utilisation avec connexion manager explicite
if __name__ == "__main__":
    # Option 1: Connexion locale (si vous êtes sur un manager)
    client = docker.from_env()
    
    # Option 2: Connexion explicite à un manager distant
    # client = connect_to_manager('192.168.1.100')
    # if not client:
    #     exit(1)
    
    # Afficher l'aperçu complet
    display_swarm_subnet_overview(client)
    
    # Ou récupérer toutes les tâches avec subnets pour traitement
    all_tasks_subnets = get_all_tasks_with_subnets(client)
    print(f"\nTotal: {len(all_tasks_subnets)} tâches analysées")
    
    # Filtrer par subnet spécifique
    target_subnet = "10.0.1.0/24"
    filtered_tasks = [t for t in all_tasks_subnets 
                     if any(s['subnet'] == target_subnet for s in t['subnets'])]
    print(f"Tâches utilisant {target_subnet}: {len(filtered_tasks)}")
