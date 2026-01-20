#!/usr/bin/env python3
"""
Script pour extraire les images des fichiers Docker stack,
verifier leur existence et les construire si necessaire.
"""

import os
import sys
import re
import yaml
import subprocess
import glob
import argparse
from pathlib import Path

def run_command(cmd, cwd=None):
    """Execute une commande et retourne le resultat"""
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            cwd=cwd,
            check=True
        )
        return result.stdout.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de l'execution de: {cmd}")
        print(f"Code de retour: {e.returncode}")
        print(f"Erreur: {e.stderr}")
        return None, e.returncode

def extract_images_from_stack(stack_file):
    """Extrait toutes les images du fichier docker-compose/stack"""
    images = set()
    
    try:
        with open(stack_file, 'r', encoding='utf-8') as f:
            stack_data = yaml.safe_load(f)
        
        # Parcourir tous les services
        if 'services' in stack_data:
            for service_name, service_config in stack_data['services'].items():
                if 'image' in service_config:
                    images.add(service_config['image'])
                    
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier {stack_file}: {e}")
        
    return images

def is_local_image(image_name):
    """Determine si une image est locale (pas de registry externe)"""
    # Images locales: pas de '/' ou commence par localhost
    if '/' not in image_name or image_name.startswith('localhost:'):
        return True
    
    # Exclure les images des registries publics
    external_registries = ['docker.io', 'gcr.io', 'quay.io', 'ghcr.io', 'registry.']
    
    for registry in external_registries:
        if image_name.startswith(registry):
            return False
            
    return True

def image_exists(image_name):
    """Verifie si une image existe localement"""
    cmd = f"docker image inspect {image_name}"
    _, returncode = run_command(cmd)
    return returncode == 0

def extract_service_name_from_stack_file(stack_file):
    """Extrait le nom du service depuis le nom du fichier stack"""
    # Format attendu: ??-service-*.yml
    filename = os.path.basename(stack_file)
    
    # Pattern pour extraire la partie variable
    pattern = r'\d{2}-service-(.+)\.yml'
    match = re.match(pattern, filename)
    
    if match:
        return match.group(1)
    else:
        print(f"Impossible d'extraire le nom du service depuis: {filename}")
        return None

def build_image(service_name, base_dir):
    """Construit l'image Docker pour le service donne"""
    service_dir = os.path.join(base_dir, service_name)
    dockerfile_name = f"Dockerfile.{service_name}"
    dockerfile_path = os.path.join(service_dir, dockerfile_name)
    
    print(f"Construction de l'image pour le service: {service_name}")
    print(f"Repertoire: {service_dir}")
    print(f"Dockerfile: {dockerfile_name}")
    
    # Verifier que le repertoire existe
    if not os.path.exists(service_dir):
        print(f"Erreur: Le repertoire {service_dir} n'existe pas")
        return False
        
    # Verifier que le Dockerfile existe
    if not os.path.exists(dockerfile_path):
        print(f"Erreur: Le Dockerfile {dockerfile_path} n'existe pas")
        return False
    
    # Construire l'image
    image_tag = f"localhost:5000/{service_name}:latest"
    build_cmd = f"docker build -f {dockerfile_name} -t {image_tag} ."
    
    print(f"Execution: {build_cmd}")
    output, returncode = run_command(build_cmd, cwd=service_dir)
    
    if returncode != 0:
        print(f"Erreur lors de la construction de l'image {service_name}")
        return False
        
    print(f"Image {image_tag} construite avec succes")
    
    # Push vers la registry locale
    push_cmd = f"docker push {image_tag}"
    print(f"Push vers la registry: {push_cmd}")
    
    output, returncode = run_command(push_cmd)
    
    if returncode != 0:
        print(f"Erreur lors du push de l'image {image_tag}")
        return False
        
    print(f"Image {image_tag} pushee avec succes")
    return True

def process_stack_files(stack_dir, base_dir):
    """Traite tous les fichiers stack dans le repertoire donne"""
    # Pattern pour les fichiers stack
    pattern = os.path.join(stack_dir, "??-service-*.yml")
    stack_files = glob.glob(pattern)
    
    if not stack_files:
        print(f"Aucun fichier stack trouve dans {stack_dir}")
        return
        
    print(f"Fichiers stack trouves: {len(stack_files)}")
    
    for stack_file in sorted(stack_files):
        print(f"\n=== Traitement de {os.path.basename(stack_file)} ===")
        
        # Extraire les images du fichier stack
        images = extract_images_from_stack(stack_file)
        print(f"Images trouvees: {len(images)}")
        
        # Filtrer les images locales
        local_images = [img for img in images if is_local_image(img)]
        print(f"Images locales: {len(local_images)}")
        
        for image in local_images:
            print(f"Verification de l'image: {image}")
            
            if not image_exists(image):
                print(f"Image {image} n'existe pas localement")
                
                # Extraire le nom du service
                service_name = extract_service_name_from_stack_file(stack_file)
                
                if service_name:
                    success = build_image(service_name, base_dir)
                    if not success:
                        print(f"Echec de la construction pour {service_name}")
                else:
                    print(f"Impossible de determiner le service pour {stack_file}")
            else:
                print(f"Image {image} existe deja")

def main():
    parser = argparse.ArgumentParser(
        description="Construit les images Docker manquantes pour les services stack"
    )
    parser.add_argument(
        "stack_dir", 
        nargs='?', 
        default="../stack",
        help="Repertoire contenant les fichiers stack (defaut: ../stack)"
    )
    parser.add_argument(
        "--base-dir", 
        default=".",
        help="Repertoire de base pour chercher les sous-repertoires de services (defaut: .)"
    )
    
    args = parser.parse_args()
    
    stack_dir = os.path.abspath(args.stack_dir)
    base_dir = os.path.abspath(args.base_dir)
    
    print(f"Repertoire des stacks: {stack_dir}")
    print(f"Repertoire de base: {base_dir}")
    
    if not os.path.exists(stack_dir):
        print(f"Erreur: Le repertoire {stack_dir} n'existe pas")
        sys.exit(1)
        
    if not os.path.exists(base_dir):
        print(f"Erreur: Le repertoire de base {base_dir} n'existe pas")
        sys.exit(1)
    
    process_stack_files(stack_dir, base_dir)

if __name__ == "__main__":
    main()

