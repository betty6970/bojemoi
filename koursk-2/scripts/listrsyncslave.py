#!/bin/env python
# -*- coding: utf-8 -*-
import docker

def get_containers_by_naming_rule(naming_pattern, stack_name=None):
    """
    Récupère tous les conteneurs qui suivent une règle de nommage spécifique
    
    Args:
        naming_pattern (str): Pattern de nommage (ex: "rsync-slave-","web-", "app_", etc.)
        stack_name (str): Nom du stack (optionnel pour filtrer)
    
    Returns:
        list: Liste des conteneurs correspondants
    """
    client = docker.from_env()
    containers_list = []
    
    try:
        # Récupère tous les conteneurs (actifs et arrêtés)
        all_containers = client.containers.list(all=True)
        for container in all_containers:
            container_name = container.name
            
            # Vérifie si le nom correspond au pattern
            if naming_pattern in container_name:
                
                
                # Ajoute les informations du conteneur
                container_info = {
                    'name': container_name,
                    'id': container.short_id,
                    'status': container.status,
                    'image': container.image.tags[0] if container.image.tags else 'N/A',
                    'labels': container.labels,
                    'ports': container.ports if hasattr(container, 'ports') else {}
                }
                
                containers_list.append(container_info)
                print(f"[OK] Trouve: {container_name} - Status: {container.status}")
    
    except docker.errors.DockerException as e:
        print(f"Erreur Docker: {e}")
    except Exception as e:
        print(f"Erreur: {e}")
    
    return containers_list

# Exemples d'utilisation
if __name__ == "__main__":
    
    # Exemple 1: Tous les conteneurs avec "web" dans le nom
    web_containers = get_containers_by_naming_rule("rsync","base")
    print(f"\n=== Conteneurs 'rsync' ({len(web_containers)} trouves) ===")
    
    # Exemple 2: Conteneurs d'un stack spécifique avec pattern
    app_containers = get_containers_by_naming_rule("app", "monstack")
    print(f"\n=== Conteneurs 'app' du stack 'monstack' ({len(app_containers)} trouves) ===")
    
    # Exemple 3: Boucle avec plusieurs patterns
    patterns = ["rsync-slave","web-", "api-", "db-", "cache-"]
    all_service_containers = []
    
    print(f"\n=== Recherche par patterns multiples ===")
    for pattern in patterns:
        containers = get_containers_by_naming_rule(pattern)
        all_service_containers.extend(containers)
        print(f"Pattern '{pattern}': {len(containers)} conteneurs")
    
    # Affichage du résumé
    print(f"\n=== RESUME ===")
    print(f"Total des conteneurs trouves: {len(all_service_containers)}")
    
    for container in all_service_containers:
        if container['status'] == 'running':
            status_symbol = "[RUNNING]"
        else:
            status_symbol = "[STOPPED]"
        print("{} {} ({})".format(status_symbol, container['name'], container['status']))

