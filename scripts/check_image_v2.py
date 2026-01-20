#!/usr/bin/env python3
"""
Script pour extraire les images des fichiers Docker Stack,
vérifier leur existence et déclencher un build si nécessaire.
"""

import os
import sys
import yaml
import subprocess
import argparse
import tempfile
from pathlib import Path
from typing import List, Set, Dict, Optional


class DockerStackImageChecker:
    def __init__(self, build_script_path: str = "./build.sh", local_only: bool = True, interactive: bool = True, keep_temp_file: bool = False):
        self.build_script_path = build_script_path
        self.local_only = local_only
        self.interactive = interactive
        self.keep_temp_file = keep_temp_file
        self.missing_images = set()
        self.existing_images = set()
        self.images_by_file = {}  # Dictionnaire pour tracker les images par fichier
        
    def extract_images_from_compose_file(self, file_path: str) -> Set[str]:
        """Extrait toutes les images d'un fichier Docker Compose/Stack."""
        images = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                compose_data = yaml.safe_load(file)
                
            if not compose_data or 'services' not in compose_data:
                print(f"ATTENTION: Aucun service trouvé dans {file_path}")
                return images
                
            for service_name, service_config in compose_data['services'].items():
                if 'image' in service_config:
                    image = service_config['image']
                    images.add(image)
                    print(f"Service '{service_name}': {image}")
                elif 'build' in service_config:
                    # Si c'est un build local, on peut générer un nom d'image
                    build_config = service_config['build']
                    if isinstance(build_config, str):
                        context = build_config
                        image_name = f"local/{service_name}:latest"
                    elif isinstance(build_config, dict):
                        context = build_config.get('context', '.')
                        dockerfile = build_config.get('dockerfile', 'Dockerfile')
                        image_name = build_config.get('tags', [f"local/{service_name}:latest"])
                        if isinstance(image_name, list):
                            image_name = image_name[0]
                    
                    images.add(image_name)
                    print(f"Service '{service_name}' (build): {image_name}")
            
            # Enregistrer les images trouvées pour ce fichier
            self.images_by_file[file_path] = list(images)
                    
        except yaml.YAMLError as e:
            print(f"ERREUR: Erreur lors de la lecture de {file_path}: {e}")
        except FileNotFoundError:
            print(f"ERREUR: Fichier non trouvé: {file_path}")
        except Exception as e:
            print(f"ERREUR: Erreur inattendue avec {file_path}: {e}")
            
        return images
    
    def check_image_exists(self, image: str) -> bool:
        """Vérifie si une image Docker existe localement."""
        try:
            result = subprocess.run(
                ['docker', 'image', 'inspect', image],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT: Timeout lors de la vérification de {image}")
            return False
        except FileNotFoundError:
            print("ERREUR: Docker n'est pas installé ou accessible")
            sys.exit(1)
        except Exception as e:
            print(f"ERREUR: Erreur lors de la vérification de {image}: {e}")
            return False
    
    def check_image_exists_remote(self, image: str) -> bool:
        """Vérifie si une image existe sur un registry distant."""
        try:
            # Essayer de récupérer le manifest sans télécharger l'image
            result = subprocess.run(
                ['docker', 'manifest', 'inspect', image],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print(f"TIMEOUT: Timeout lors de la vérification distante de {image}")
            return False
        except Exception as e:
            print(f"ATTENTION: Impossible de vérifier {image} sur le registry distant: {e}")
            return False
    
    def ask_user_confirmation(self, images: List[str]) -> List[str]:
        """Demande à l'utilisateur de confirmer pour chaque image."""
        selected_images = []
        
        print(f"\nCONFIRMATION: Confirmation pour {len(images)} image(s):")
        print("=" * 50)
        
        for i, image in enumerate(sorted(images), 1):
            while True:
                # Déterminer le type d'image pour l'affichage
                image_type = "locale" if self.is_local_image(image) else "publique"
                
                response = input(f"\n[{i}/{len(images)}] Construire/télécharger '{image}' ({image_type})? [o/N/a/q]: ").strip().lower()
                
                if response in ['o', 'oui', 'y', 'yes']:
                    selected_images.append(image)
                    print(f"  OK: {image} ajoutée à la liste")
                    break
                elif response in ['n', 'non', 'no', '']:
                    print(f"  IGNORE: {image} ignorée")
                    break
                elif response in ['a', 'all', 'tout']:
                    # Ajouter toutes les images restantes
                    selected_images.extend(images[images.index(image):])
                    print(f"  TOUT: Toutes les images restantes ajoutées ({len(images) - images.index(image)} images)")
                    return selected_images
                elif response in ['q', 'quit', 'quitter']:
                    print(f"\nARRET: Arrêt demandé par l'utilisateur")
                    return selected_images
                else:
                    print("  AIDE: Réponse non reconnue. Utilisez:")
                    print("     o/oui = Oui pour cette image")
                    print("     n/non = Non pour cette image (défaut)")
                    print("     a/tout = Oui pour toutes les images restantes")
                    print("     q/quitter = Arrêter maintenant")
        
        return selected_images
    
    def filter_local_images(self, images: Set[str]) -> List[str]:
        """Filtre pour ne garder que les images locales (non publiques)."""
        local_images = []
        
        for image in images:
            if self.is_local_image(image):
                local_images.append(image)
            else:
                print(f"  IGNORE: {image} (image publique - ignorée)")
        
        return local_images
    
    def is_local_image(self, image: str) -> bool:
        """Détermine si une image est locale (doit être construite) ou publique."""
        # Séparer le nom et le tag
        if ':' in image:
            image_name, tag = image.rsplit(':', 1)
        else:
            image_name = image
            tag = 'latest'
        
        # Patterns d'images locales
        local_patterns = [
            'localhost:',           # Registry local (localhost:5000/...)
            '127.0.0.1:',          # Registry local IP
            'local/',              # Préfixe local
            'app-',                # Applications custom
            'custom-',             # Images custom
            'test-',               # Images de test
            'dev-',                # Images de développement
        ]
        
        # Vérifier si l'image contient un pattern local
        for pattern in local_patterns:
            if pattern in image_name:
                return True
        
        # Images publiques communes (Docker Hub officiel)
        public_patterns = [
            'redis',
            'nginx', 
            'postgres',
            'mysql',
            'mongo',
            'alpine',
            'ubuntu',
            'node',
            'python',
            'php',
            'httpd',
            'memcached',
            'rabbitmq',
            'elasticsearch',
            'kibana',
            'logstash',
            'grafana',
            'prometheus'
        ]
        
        # Si c'est une image publique connue sans registry spécifique
        if not '/' in image_name or image_name.count('/') == 1:
            base_name = image_name.split('/')[-1]
            if any(base_name.startswith(pattern) for pattern in public_patterns):
                return False
        
        # Par défaut, traiter comme locale si pas clairement publique
        # ou si ça contient un registry privé
        if '/' in image_name and not any(registry in image_name for registry in ['docker.io', 'registry-1.docker.io']):
            return True
            
        return False
        """Exécute le script de build avec la liste des images manquantes."""
        if not os.path.exists(self.build_script_path):
            print(f"ERREUR: Script de build non trouvé: {self.build_script_path}")
            return False
            
        if not os.access(self.build_script_path, os.X_OK):
            print(f"ERREUR: Script de build non exécutable: {self.build_script_path}")
            return False
        
        try:
            print(f"DEMARRAGE: Exécution du script de build: {self.build_script_path}")
            print(f"LISTE: Images à construire: {', '.join(images)}")
            
            # Passer les images manquantes comme arguments
            # Convertir en liste si c'est une chaîne unique
            if isinstance(images, str):
                cmd = [self.build_script_path, images]
            else:
                cmd = [self.build_script_path] + list(images)
            result = subprocess.run(cmd, timeout=1800)  # 30 minutes max
            
            if result.returncode == 0:
                print("SUCCES: Script de build exécuté avec succès")
                return True
            else:
                print(f"ERREUR: Le script de build a échoué avec le code: {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            print("TIMEOUT: Timeout lors de l'exécution du script de build")
            return False
        except Exception as e:
            print(f"ERREUR: Erreur lors de l'exécution du script de build: {e}")
            return False
    
    def run_build_script(self, images: List[str]) -> bool:
        """Exécute le script de build avec un fichier contenant la liste des images."""
        if not os.path.exists(self.build_script_path):
            print(f"ERREUR: Script de build non trouvé: {self.build_script_path}")
            return False
            
        if not os.access(self.build_script_path, os.X_OK):
            print(f"ERREUR: Script de build non exécutable: {self.build_script_path}")
            return False
        
        # Créer un fichier temporaire avec la liste des images
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, prefix='docker_images_') as temp_file:
                temp_file_path = temp_file.name
                
                # Écrire chaque image sur une ligne
                for image in images:
                    temp_file.write(f"{image}\n")
                
                print(f"FICHIER: Liste des images écrite dans: {temp_file_path}")
        
        except Exception as e:
            print(f"ERREUR: Impossible de créer le fichier temporaire: {e}")
            return False
        
        try:
            print(f"DEMARRAGE: Exécution du script de build: {self.build_script_path}")
            print(f"LISTE: {len(images)} images à construire")
            
            # Passer le fichier temporaire comme argument
            cmd = [self.build_script_path, temp_file_path]
            result = subprocess.run(cmd, timeout=1800)  # 30 minutes max
            
            if result.returncode == 0:
                print("SUCCES: Script de build exécuté avec succès")
                return True
            else:
                print(f"ERREUR: Le script de build a échoué avec le code: {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            print("TIMEOUT: Timeout lors de l'exécution du script de build")
            return False
        except Exception as e:
            print(f"ERREUR: Erreur lors de l'exécution du script de build: {e}")
            return False
        finally:
            # Nettoyer le fichier temporaire (sauf si demandé de le garder)
            try:
                if os.path.exists(temp_file_path):
                    if self.keep_temp_file:
                        print(f"CONSERVATION: Fichier temporaire conservé: {temp_file_path}")
                    else:
                        os.unlink(temp_file_path)
                        print(f"NETTOYAGE: Fichier temporaire supprimé: {temp_file_path}")
            except Exception as e:
                print(f"ATTENTION: Impossible de supprimer le fichier temporaire {temp_file_path}: {e}")
    
    def display_images_summary_table(self):
        """Affiche un tableau récapitulatif des images par fichier."""
        if not self.images_by_file:
            print("TABLEAU: Aucune donnée à afficher")
            return
        
        print("\nTABLEAU: Récapitulatif des images par fichier Docker Stack")
        print("=" * 80)
        
        # Calculer la largeur des colonnes
        max_file_width = max(len(f) for f in self.images_by_file.keys())
        max_file_width = max(max_file_width, len("Fichier"))
        
        # En-tête du tableau
        print(f"{'Fichier':<{max_file_width}} | {'Nb Images':<10} | Images")
        print("-" * max_file_width + "-+-" + "-" * 10 + "-+-" + "-" * 40)
        
        total_images = 0
        for file_path, images in self.images_by_file.items():
            file_name = os.path.basename(file_path)  # Afficher seulement le nom du fichier
            nb_images = len(images)
            total_images += nb_images
            
            if nb_images == 0:
                images_str = "(aucune)"
            elif nb_images == 1:
                images_str = images[0]
            else:
                # Afficher la première image et indiquer le nombre total
                images_str = f"{images[0]} (+{nb_images-1} autres)"
            
            print(f"{file_name:<{max_file_width}} | {nb_images:<10} | {images_str}")
            
            # Si plus d'une image, afficher les autres sur des lignes séparées
            if nb_images > 1:
                for image in images[1:]:
                    print(f"{'':<{max_file_width}} | {'':<10} | {image}")
        
        print("-" * max_file_width + "-+-" + "-" * 10 + "-+-" + "-" * 40)
        print(f"{'TOTAL':<{max_file_width}} | {total_images:<10} | images trouvées")
        print()
    
    def process_stack_files(self, file_paths: List[str], check_remote: bool = False) -> bool:
        """Traite une liste de fichiers Docker Stack."""
        all_images = set()
        
        print("� Extraction des images des fichiers Docker Stack...")
        for file_path in file_paths:
            print(f"\n� Analyse de: {file_path}")
            images = self.extract_images_from_compose_file(file_path)
            all_images.update(images)
        
        if not all_images:
            print("⚠️  Aucune image trouvée dans les fichiers spécifiés")
            return True
            
        print(f"\n� Vérification de {len(all_images)} images...")
        
        for image in all_images:
            print(f"� Vérification de {image}...")
            
            # Vérification locale
            if self.check_image_exists(image):
                print(f"✅ {image} existe localement")
                self.existing_images.add(image)
                continue
            
            # Vérification distante si demandée
            if check_remote and self.check_image_exists_remote(image):
                print(f"✅ {image} existe sur le registry distant")
                self.existing_images.add(image)
                continue
            
            print(f"❌ {image} n'existe pas")
            self.missing_images.add(image)
        
        # Résumé
        print(f"\n� Résumé:")
        print(f"✅ Images existantes: {len(self.existing_images)}")
        print(f"❌ Images manquantes: {len(self.missing_images)}")
        
        if self.missing_images:
            print(f"\n� Images manquantes:")
            for image in sorted(self.missing_images):
                print(f"  - {image}")
            
            # Filtrer pour ne garder que les images locales si demandé
            if self.local_only:
                local_images = self.filter_local_images(self.missing_images)
                images_to_process = local_images
            else:
                images_to_process = list(self.missing_images)
            
            if images_to_process:
                # Demander confirmation pour chaque image si mode interactif
                if self.interactive:
                    selected_images = self.ask_user_confirmation(images_to_process)
                else:
                    # Mode non-interactif : traiter toutes les images filtrées
                    selected_images = images_to_process
                    print(f"\n� Mode non-interactif : traitement de toutes les images")
                
                if selected_images:
                    print(f"\n�️  Images sélectionnées pour construction:")
                    for image in selected_images:
                        print(f"  ✓ {image}")
                    
                    # Exécuter le script de build pour les images sélectionnées
                    return self.run_build_script(selected_images)
                else:
                    print(f"\n⚠️  Aucune image sélectionnée pour construction")
                    return True
            else:
                if self.local_only:
                    print(f"\n⚠️  Aucune image locale à construire (toutes les images manquantes sont publiques)")
                    print(f"� Astuce: Utilisez 'docker pull' pour télécharger les images publiques")
                else:
                    print(f"\n⚠️  Aucune image manquante à traiter")
                return True
        else:
            print("SUCCES: Toutes les images sont disponibles!")
            return True


def find_stack_files(directory: str = ".") -> List[str]:
    """Trouve automatiquement les fichiers Docker Stack dans un répertoire."""
    patterns = [
        "docker-compose.yml",
        "docker-compose.yaml", 
        "docker-stack.yml",
        "docker-stack.yaml",
        "stack.yml",
        "stack.yaml"
    ]
    
    found_files = []
    path = Path(directory)
    
    for pattern in patterns:
        for file_path in path.rglob(pattern):
            found_files.append(str(file_path))
    
    return found_files


def main():
    parser = argparse.ArgumentParser(
        description="Vérifie les images Docker Stack et lance un build si nécessaire"
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Fichiers Docker Stack à analyser (auto-détection si vide)"
    )
    parser.add_argument(
        "-b", "--build-script",
        default="./build.sh",
        help="Chemin vers le script de build (défaut: ./build.sh)"
    )
    parser.add_argument(
        "-r", "--check-remote",
        action="store_true",
        help="Vérifier aussi les registries distants"
    )
    parser.add_argument(
        "-d", "--directory",
        default=".",
        help="Répertoire à scanner pour les fichiers Stack (défaut: répertoire courant)"
    )
    
