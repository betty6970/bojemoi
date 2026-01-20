#!/usr/bin/env python3
"""
Script pour supprimer toutes les images Docker ayant le même nom ou ID
Inclut les images dans le repository local
"""

import subprocess
import sys
import argparse
import json
from typing import List, Dict, Any

def run_docker_command(cmd: List[str]) -> tuple:
    """
    Exécute une commande Docker et retourne le résultat
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()

def get_all_images() -> List[Dict[str, Any]]:
    """
    Récupère la liste de toutes les images Docker
    """
    success, output = run_docker_command(['docker', 'images', '--format', 'json'])
    if not success:
        print(f"Erreur lors de la récupération des images : {output}")
        return []
    
    images = []
    for line in output.split('\n'):
        if line.strip():
            try:
                image_data = json.loads(line)
                images.append(image_data)
            except json.JSONDecodeError:
                continue
    
    return images

def find_matching_images(search_term: str) -> List[Dict[str, Any]]:
    """
    Trouve toutes les images correspondant au terme de recherche (nom ou ID)
    """
    all_images = get_all_images()
    matching_images = []
    
    for image in all_images:
        # Vérifier par ID (complet ou partiel)
        if search_term in image.get('ID', ''):
            matching_images.append(image)
        # Vérifier par nom du repository
        elif search_term in image.get('Repository', ''):
            matching_images.append(image)
        # Vérifier par tag complet (repository:tag)
        elif search_term == f"{image.get('Repository', '')}:{image.get('Tag', '')}":
            matching_images.append(image)
    
    return matching_images

def remove_image(image_id: str, force: bool = False) -> bool:
    """
    Supprime une image Docker par son ID
    """
    cmd = ['docker', 'rmi']
    if force:
        cmd.append('-f')
    cmd.append(image_id)
    
    success, output = run_docker_command(cmd)
    if success:
        print(f"✓ Image supprimée : {image_id}")
        return True
    else:
        print(f"✗ Erreur lors de la suppression de {image_id} : {output}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Supprime toutes les images Docker ayant le même nom ou ID"
    )
    parser.add_argument(
        'search_term',
        help='Nom de l\'image ou ID à rechercher et supprimer'
    )
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Force la suppression même si l\'image est utilisée par un conteneur'
    )
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Confirme automatiquement la suppression sans demander'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Affiche les images qui seraient supprimées sans les supprimer'
    )
    
    args = parser.parse_args()
    
    # Vérifier que Docker est accessible
    success, _ = run_docker_command(['docker', '--version'])
    if not success:
        print("Erreur : Docker n'est pas accessible ou n'est pas installé")
        sys.exit(1)
    
    # Trouver les images correspondantes
    print(f"Recherche des images correspondant à : {args.search_term}")
    matching_images = find_matching_images(args.search_term)
    
    if not matching_images:
        print("Aucune image trouvée correspondant au critère de recherche.")
        sys.exit(0)
    
    # Afficher les images trouvées
    print(f"\nImages trouvées ({len(matching_images)}) :")
    print("-" * 80)
    for image in matching_images:
        size = image.get('Size', 'N/A')
        created = image.get('CreatedSince', image.get('CreatedAt', 'N/A'))
        repo_tag = f"{image.get('Repository', '<none>')}:{image.get('Tag', '<none>')}"
        print(f"ID: {image['ID']:<12} | {repo_tag:<40} | Taille: {size:<10} | Créé: {created}")
    
    if args.dry_run:
        print(f"\n[DRY RUN] {len(matching_images)} image(s) seraient supprimée(s)")
        sys.exit(0)
    
    # Demander confirmation si nécessaire
    if not args.yes:
        response = input(f"\nÊtes-vous sûr de vouloir supprimer ces {len(matching_images)} image(s) ? [y/N]: ")
        if response.lower() not in ['y', 'yes', 'o', 'oui']:
            print("Suppression annulée.")
            sys.exit(0)
    
    # Supprimer les images
    print(f"\nSuppression des images...")
    success_count = 0
    
    for image in matching_images:
        if remove_image(image['ID'], args.force):
            success_count += 1
    
    print(f"\nRésumé : {success_count}/{len(matching_images)} image(s) supprimée(s) avec succès")
    
    if success_count < len(matching_images):
        print("Certaines images n'ont pas pu être supprimées. Utilisez -f pour forcer la suppression.")
        sys.exit(1)

if __name__ == "__main__":
    main()

