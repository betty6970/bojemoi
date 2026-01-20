#!/usr/bin/env python3
"""
Script de vérification et synchronisation du Docker Registry
Vérifie que toutes les images locales sont présentes dans le registry
et recrée les enregistrements manquants.
"""

import docker
import requests
import json
import sys
import logging
from typing import List, Dict, Set
from urllib.parse import urljoin
import argparse

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DockerRegistrySync:
    def __init__(self, registry_url: str, username: str = None, password: str = None):
        """
        Initialise le synchronisateur Docker Registry
        
        Args:
            registry_url: URL du registry Docker (ex: https://registry.example.com)
            username: Nom d'utilisateur pour l'authentification (optionnel)
            password: Mot de passe pour l'authentification (optionnel)
        """
        self.registry_url = registry_url.rstrip('/')
        self.username = username
        self.password = password
        self.docker_client = docker.from_env()
        self.session = requests.Session()
        
        # Configuration de l'authentification si fournie
        if username and password:
            self.session.auth = (username, password)
    
    def get_local_images(self) -> List[Dict]:
        """
        Récupère la liste des images Docker locales
        
        Returns:
            Liste des images avec leurs tags
        """
        logger.info("Récupération des images Docker locales...")
        images = []
        
        for image in self.docker_client.images.list():
            # Ignorer les images sans tags (dangling images)
            if image.tags:
                for tag in image.tags:
                    # Séparer le nom du repository et le tag
                    if ':' in tag:
                        repo, version = tag.rsplit(':', 1)
                    else:
                        repo, version = tag, 'latest'
                    
                    images.append({
                        'repository': repo,
                        'tag': version,
                        'full_name': tag,
                        'id': image.id,
                        'size': image.attrs.get('Size', 0)
                    })
        
        logger.info(f"Trouvé {len(images)} images locales")
        return images
    
    def get_registry_repositories(self) -> Set[str]:
        """
        Récupère la liste des repositories dans le registry
        
        Returns:
            Ensemble des noms de repositories
        """
        try:
            url = urljoin(self.registry_url, '/v2/_catalog')
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            repositories = set(data.get('repositories', []))
            logger.info(f"Trouvé {len(repositories)} repositories dans le registry")
            return repositories
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération des repositories: {e}")
            return set()
    
    def get_repository_tags(self, repository: str) -> Set[str]:
        """
        Récupère les tags d'un repository spécifique
        
        Args:
            repository: Nom du repository
            
        Returns:
            Ensemble des tags disponibles
        """
        try:
            url = urljoin(self.registry_url, f'/v2/{repository}/tags/list')
            response = self.session.get(url)
            response.raise_for_status()
            
            data = response.json()
            tags = set(data.get('tags', []))
            return tags
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la récupération des tags pour {repository}: {e}")
            return set()
    
    def check_image_exists_in_registry(self, repository: str, tag: str) -> bool:
        """
        Vérifie si une image existe dans le registry
        
        Args:
            repository: Nom du repository
            tag: Tag de l'image
            
        Returns:
            True si l'image existe, False sinon
        """
        try:
            url = urljoin(self.registry_url, f'/v2/{repository}/manifests/{tag}')
            response = self.session.head(url)
            return response.status_code == 200
            
        except requests.exceptions.RequestException:
            return False
    
    def push_image_to_registry(self, image_name: str) -> bool:
        """
        Pousse une image vers le registry
        
        Args:
            image_name: Nom complet de l'image (repository:tag)
            
        Returns:
            True si le push réussit, False sinon
        """
        try:
            logger.info(f"Push de l'image {image_name} vers le registry...")
            
            # Tag l'image pour le registry si nécessaire
            registry_tag = f"{self.registry_url.replace('https://', '').replace('http://', '')}/{image_name}"
            
            # Récupérer l'image locale
            local_image = self.docker_client.images.get(image_name)
            local_image.tag(registry_tag)
            
            # Pousser l'image
            push_logs = self.docker_client.images.push(
                registry_tag,
                auth_config={
                    'username': self.username,
                    'password': self.password
                } if self.username and self.password else None,
                stream=True,
                decode=True
            )
            
            # Vérifier le succès du push
            for log in push_logs:
                if 'error' in log:
                    logger.error(f"Erreur lors du push: {log['error']}")
                    return False
                elif 'status' in log:
                    logger.debug(f"Push status: {log['status']}")
            
            logger.info(f"Image {image_name} poussée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du push de {image_name}: {e}")
            return False
    
    def sync_images(self, dry_run: bool = False) -> Dict:
        """
        Synchronise les images locales avec le registry
        
        Args:
            dry_run: Si True, affiche seulement ce qui serait fait sans l'exécuter
            
        Returns:
            Dictionnaire avec les statistiques de synchronisation
        """
        stats = {
            'total_local_images': 0,
            'images_in_registry': 0,
            'missing_images': 0,
            'pushed_images': 0,
            'failed_pushes': 0
        }
        
        # Récupérer les images locales
        local_images = self.get_local_images()
        stats['total_local_images'] = len(local_images)
        
        if not local_images:
            logger.warning("Aucune image locale trouvée")
            return stats
        
        # Récupérer les repositories du registry
        registry_repositories = self.get_registry_repositories()
        
        missing_images = []
        
        # Vérifier chaque image locale
        for image in local_images:
            repository = image['repository']
            tag = image['tag']
            full_name = image['full_name']
            
            logger.info(f"Vérification de l'image {full_name}...")
            
            # Vérifier si l'image existe dans le registry
            if self.check_image_exists_in_registry(repository, tag):
                logger.info(f"✓ Image {full_name} présente dans le registry")
                stats['images_in_registry'] += 1
            else:
                logger.warning(f"✗ Image {full_name} manquante dans le registry")
                missing_images.append(image)
                stats['missing_images'] += 1
        
        # Pousser les images manquantes
        if missing_images:
            logger.info(f"\nTrouvé {len(missing_images)} images manquantes dans le registry")
            
            if dry_run:
                logger.info("Mode dry-run: Les images suivantes seraient poussées:")
                for image in missing_images:
                    logger.info(f"  - {image['full_name']}")
            else:
                logger.info("Push des images manquantes...")
                for image in missing_images:
                    if self.push_image_to_registry(image['full_name']):
                        stats['pushed_images'] += 1
                    else:
                        stats['failed_pushes'] += 1
        else:
            logger.info("✓ Toutes les images locales sont présentes dans le registry")
        
        return stats
    
    def print_stats(self, stats: Dict):
        """
        Affiche les statistiques de synchronisation
        
        Args:
            stats: Dictionnaire des statistiques
        """
        print("\n" + "="*50)
        print("STATISTIQUES DE SYNCHRONISATION")
        print("="*50)
        print(f"Images locales totales:      {stats['total_local_images']}")
        print(f"Images présentes au registry: {stats['images_in_registry']}")
        print(f"Images manquantes:           {stats['missing_images']}")
        print(f"Images poussées:             {stats['pushed_images']}")
        print(f"Échecs de push:              {stats['failed_pushes']}")
        print("="*50)


def main():
    parser = argparse.ArgumentParser(
        description='Synchronise les images Docker locales avec un registry'
    )
    parser.add_argument(
        'registry_url',
        help='URL du registry Docker (ex: https://registry.example.com)'
    )
    parser.add_argument(
        '--username', '-u',
        help='Nom d\'utilisateur pour l\'authentification'
    )
    parser.add_argument(
        '--password', '-p',
        help='Mot de passe pour l\'authentification'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Affiche seulement ce qui serait fait sans l\'exécuter'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Active le mode verbose'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Créer l'instance du synchronisateur
    sync = DockerRegistrySync(
        registry_url=args.registry_url,
        username=args.username,
        password=args.password
    )
    
    try:
        # Lancer la synchronisation
        stats = sync.sync_images(dry_run=args.dry_run)
        
        # Afficher les statistiques
        sync.print_stats(stats)
        
        # Code de sortie basé sur les résultats
        if stats['failed_pushes'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("\nSynchronisation interrompue par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
