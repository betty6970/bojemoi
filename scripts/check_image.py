#!/usr/bin/env python3
"""
Script pour extraire les images des fichiers Docker Stack/Compose,
vérifier leur existence et déclencher un build si nécessaire.
"""

import os
import sys
import yaml
import subprocess
import argparse
from pathlib import Path
from typing import List, Set, Dict, Any
import docker
from docker.errors import ImageNotFound, APIError


class DockerImageChecker:
    def __init__(self, build_script_path: str = None):
        """
        Initialise le vérificateur d'images Docker.
        
        Args:
            build_script_path: Chemin vers le script de build à exécuter
        """
        self.build_script_path = build_script_path
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            print(f"Erreur lors de la connexion à Docker: {e}")
            sys.exit(1)
    
    def extract_images_from_compose_file(self, file_path: Path) -> Set[str]:
        """
        Extrait toutes les images d'un fichier Docker Compose/Stack.
        
        Args:
            file_path: Chemin vers le fichier YAML
            
        Returns:
            Set des noms d'images trouvées
        """
        images = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                compose_data = yaml.safe_load(f)
            
            if not compose_data:
                print(f"Attention: {file_path} est vide ou invalide")
                return images
            
            # Parcourir les services
            services = compose_data.get('services', {})
            for service_name, service_config in services.items():
                if isinstance(service_config, dict):
                    # Récupérer l'image directement spécifiée
                    if 'image' in service_config:
                        images.add(service_config['image'])
                    
                    # Vérifier si il y a un build (image construite)
                    elif 'build' in service_config:
                        # Si c'est un build, on peut avoir un nom d'image dans le contexte
                        build_config = service_config['build']
                        if isinstance(build_config, dict):
                            if 'image' in build_config:
                                images.add(build_config['image'])
                            # Sinon, utiliser le nom du service comme nom d'image potentiel
                            else:
                                potential_image = f"{service_name}:latest"
                                images.add(potential_image)
                        else:
                            # build est juste un chemin
                            potential_image = f"{service_name}:latest"
                            images.add(potential_image)
        
        except yaml.YAMLError as e:
            print(f"Erreur lors de l'analyse YAML de {file_path}: {e}")
        except Exception as e:
            print(f"Erreur lors de la lecture de {file_path}: {e}")
        
        return images
    
    def find_compose_files(self, directory: Path, patterns: List[str] = None) -> List[Path]:
        """
        Trouve tous les fichiers Docker Compose/Stack dans un répertoire.
        
        Args:
            directory: Répertoire à parcourir
            patterns: Motifs de noms de fichiers à rechercher
            
        Returns:
            Liste des fichiers trouvés
        """
        if patterns is None:
            patterns = [
                '??-service-*.yml',
                'docker-compose*.yml',
                'docker-compose*.yaml',
                'docker-stack*.yml',
                'docker-stack*.yaml',
                'stack*.yml',
                'stack*.yaml'
            ]
        
        files = []
        for pattern in patterns:
            files.extend(directory.glob(pattern))
            # Recherche récursive
            files.extend(directory.rglob(pattern))
        
        # Supprimer les doublons
        return list(set(files))
    
    def image_exists_locally(self, image_name: str) -> bool:
        """
        Vérifie si une image existe localement.
        
        Args:
            image_name: Nom de l'image à vérifier
            
        Returns:
            True si l'image existe, False sinon
        """
        try:
            self.docker_client.images.get(image_name)
            return True
        except ImageNotFound:
            return False
        except APIError as e:
            print(f"Erreur API Docker pour l'image {image_name}: {e}")
            return False
    
    def image_exists_remotely(self, image_name: str) -> bool:
        """
        Vérifie si une image existe dans un registre distant.
        
        Args:
            image_name: Nom de l'image à vérifier
            
        Returns:
            True si l'image existe, False sinon
        """
        try:
            # Tenter de récupérer les métadonnées de l'image
            result = subprocess.run(
                ['docker', 'manifest', 'inspect', image_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"Timeout lors de la vérification distante de {image_name}")
            return False
        except Exception as e:
            print(f"Erreur lors de la vérification distante de {image_name}: {e}")
            return False
    
    def run_build_script(self, missing_image: List[str]) -> bool:
        """
        Exécute le script de build pour les images manquantes.
        
        Args:
            missing_image: image manquante
            
        Returns:
            True si le script s'est exécuté avec succès
        """
        if not self.build_script_path:
            print("Aucun script de build spécifié")
            return False
        
        if not os.path.exists(self.build_script_path):
            print(f"Script de build non trouvé: {self.build_script_path}")
            return False
        
        try:
            print(f"Exécution du script de build: {self.build_script_path}")
            print(f"Image manquante: {', '.join(missing_image)}")
            
            # Passer l'image manquante comme arguments
            cmd = [self.build_script_path, missing_image]
            result = subprocess.run(cmd, check=True, text=True, capture_output=True)
            
            print("Script de build exécuté avec succès")
            print(f"Sortie: {result.stdout}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Erreur lors de l'exécution du script de build: {e}")
            print(f"Sortie d'erreur: {e.stderr}")
            return False
        except Exception as e:
            print(f"Erreur inattendue lors de l'exécution du script: {e}")
            return False
    
    def check_images(self, directory: Path, check_remote: bool = False) -> Dict[str, Any]:
        """
        Vérifie toutes les images trouvées dans les fichiers Docker Compose.
        
        Args:
            directory: Répertoire à analyser
            check_remote: Vérifier aussi les registres distants
            
        Returns:
            Dictionnaire avec les résultats de la vérification
        """
        print(f"Recherche des fichiers Docker Stack/Compose dans: {directory}")
        
        # Trouver tous les fichiers Docker Compose
        compose_files = self.find_compose_files(directory)
        
        if not compose_files:
            print("Aucun fichier Docker Stack/Compose trouvé")
            return {
                'files_found': 0,
                'images_found': 0,
                'images_missing': [],
                'images_existing': []
            }
        
        print(f"Fichiers trouvés: {len(compose_files)}")
        for f in compose_files:
            print(f"  - {f}")
        
        # Extraire toutes les images
        all_images = set()
        for compose_file in compose_files:
            images = self.extract_images_from_compose_file(compose_file)
            all_images.update(images)
            if images:
                print(f"\nImages dans {compose_file.name}: {', '.join(images)}")
        
        if not all_images:
            print("\nAucune image trouvée dans les fichiers")
            return {
                'files_found': len(compose_files),
                'images_found': 0,
                'images_missing': [],
                'images_existing': []
            }
        
        print(f"\nTotal d'images uniques trouvées: {len(all_images)}")
        
        # Vérifier l'existence des images
        existing_images = []
        missing_images = []
        
        for image in all_images:
            print(f"\nVérification de l'image: {image}")
            
            # Vérification locale
            if self.image_exists_locally(image):
                print(f"  ✓ Existe localement")
                existing_images.append(image)
            elif check_remote and self.image_exists_remotely(image):
                print(f"  ✓ Existe dans le registre distant")
                existing_images.append(image)
            else:
                print(f"  ✗ Manquante")
                missing_images.append(image)
        
        return {
            'files_found': len(compose_files),
            'images_found': len(all_images),
            'images_missing': missing_images,
            'images_existing': existing_images
        }
    
    def run(self, directory: Path, check_remote: bool = False, auto_build: bool = False):
        """
        Fonction principale du script.
        
        Args:
            directory: Répertoire à analyser
            check_remote: Vérifier les registres distants
            auto_build: Lancer automatiquement le build si des images manquent
        """
        results = self.check_images(directory, check_remote)
        
        print("\n" + "="*60)
        print("RÉSUMÉ")
        print("="*60)
        print(f"Fichiers Docker Stack/Compose analysés: {results['files_found']}")
        print(f"Images trouvées: {results['images_found']}")
        print(f"Images existantes: {len(results['images_existing'])}")
        print(f"Images manquantes: {len(results['images_missing'])}")
        
        if results['images_existing']:
            print(f"\nImages existantes:")
            for img in results['images_existing']:
                print(f"  ✓ {img}")
        
        if results['images_missing']:
            print(f"\nImages manquantes:")
            for img in results['images_missing']:
                print(f"  ✗ {img}")
            
            if auto_build and self.build_script_path:
                print(f"\nLancement du build automatique...")
                success = self.run_build_script(img)
                if success:
                    print("Build terminé avec succès")
                else:
                    print("Échec du build")
                    sys.exit(1)
            elif self.build_script_path:
                response = input(f"\nVoulez-vous lancer le script de build? (y/N): ")
                if response.lower() in ['y', 'yes', 'o', 'oui']:
                    success = self.run_build_script(img)
                    if not success:
                        sys.exit(1)
        else:
            print("\n✓ Toutes les images sont disponibles!")


def main():
    parser = argparse.ArgumentParser(
        description="Vérifie l'existence des images Docker dans les fichiers Compose/Stack"
    )
    parser.add_argument(
        'directory',
        type=Path,
        help='Répertoire contenant les fichiers Docker Compose'
    )
    parser.add_argument(
        '--build-script',
        type=str,
        help='Chemin vers le script de build à exécuter pour les images manquantes'
    )
    parser.add_argument(
        '--check-remote',
        action='store_true',
        help='Vérifier aussi les registres distants (plus lent)'
    )
    parser.add_argument(
        '--auto-build',
        action='store_true',
        help='Lancer automatiquement le build sans demander confirmation'
    )
    
    args = parser.parse_args()
    
    if not args.directory.exists():
        print(f"Erreur: Le répertoire {args.directory} n'existe pas")
        sys.exit(1)
    
    checker = DockerImageChecker(args.build_script)
    checker.run(args.directory, args.check_remote, args.auto_build)


if __name__ == "__main__":
    main()

