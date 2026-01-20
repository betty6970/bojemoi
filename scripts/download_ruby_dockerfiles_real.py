#!/usr/bin/env python3
"""
Script pour récupérer RÉELLEMENT tous les Dockerfiles Ruby
Source: https://github.com/docker-library/ruby
"""

import requests
import os
import json

    def download_all_ruby_dockerfiles():
    """Télécharge tous les Dockerfiles Ruby depuis GitHub"""
    
    # Récupérer l'arborescence
    tree_url = "https://api.github.com/repos/docker-library/ruby/git/trees/master?recursive=1"
    response = requests.get(tree_url)
    tree = response.json()['tree']
    
    # Filtrer les Dockerfiles
    dockerfiles = [item for item in tree if 'Dockerfile' in item['path']]
    
    print(f"Trouvé {len(dockerfiles)} Dockerfiles")
    
    # Créer le dossier de sortie
    os.makedirs('ruby_dockerfiles_real', exist_ok=True)
    
    # Télécharger chaque Dockerfile
    for df in dockerfiles:
        path = df['path']
        download_url = f"https://raw.githubusercontent.com/docker-library/ruby/master/{path}"
        
        try:
            file_response = requests.get(download_url)
            content = file_response.text
            
            # Nom de fichier sécurisé
            safe_name = path.replace('/', '_').replace('\\', '_')
            filename = f"ruby_dockerfiles_real/{safe_name}"
            
            with open(filename, 'w') as f:
                f.write(f"# Source: {path}\n")
                f.write(f"# URL: {download_url}\n")
                f.write("# " + "="*50 + "\n\n")
                f.write(content)
            
            print(f"✓ {path}")
            
        except Exception as e:
            print(f"✗ {path}: {e}")

if __name__ == "__main__":
    download_all_ruby_dockerfiles()
