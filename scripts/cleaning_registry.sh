#!/bin/bash

REGISTRY="registry.bojemoi.lab:5000"
# REGISTRY="localhost:5000"  # Décommenter si registry locale

echo "=== Nettoyage des tags non-latest ==="

# Récupérer la liste des repositories
REPOS=$(curl -s http://${REGISTRY}/v2/_catalog | jq -r '.repositories[]')

for repo in $REPOS; do
    echo -e "\n📦 Repository: $repo"
    
    # Récupérer tous les tags
    TAGS=$(curl -s http://${REGISTRY}/v2/${repo}/tags/list | jq -r '.tags[]')
    
    for tag in $TAGS; do
        if [ "$tag" != "latest" ]; then
            echo "  🗑️  Suppression du tag: $tag"
            
            # Récupérer le digest du manifest
            DIGEST=$(curl -s -I -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
                http://${REGISTRY}/v2/${repo}/manifests/${tag} | \
                grep -i Docker-Content-Digest | awk '{print $2}' | tr -d '\r')
            
            if [ ! -z "$DIGEST" ]; then
                # Supprimer l'image par son digest
                curl -X DELETE http://${REGISTRY}/v2/${repo}/manifests/${DIGEST}
                echo "     ✓ Supprimé: ${repo}:${tag} (${DIGEST})"
            else
                echo "     ✗ Impossible de récupérer le digest pour ${repo}:${tag}"
            fi
        else
            echo "  ✓ Conservé: $tag"
        fi
    done
done

echo -e "\n=== Nettoyage terminé ==="
echo "N'oublie pas de lancer le garbage collector sur la registry:"
echo "docker exec <registry-container> bin/registry garbage-collect /etc/docker/registry/config.yml"


