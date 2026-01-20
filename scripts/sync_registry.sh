#!/bin/ash

# Filtrer et pousser toutes les images localhost:5000/*:latest
echo "=== Images trouvées ==="
docker images localhost:5000/*:latest

echo -e "\n=== Push vers le registre local ==="
docker images --format "{{.Repository}}:{{.Tag}}" | grep "localhost:5000.*:latest" | while read image; do
    echo "Pushing $image..."
    docker push "$image"
    if [ $? -eq 0 ]; then
        echo "✓ $image pushed successfully"
    else
        echo "✗ Failed to push $image"
    fi
done
