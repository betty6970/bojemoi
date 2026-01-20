#!/bin/bash
REGISTRY="registry.bojemoi.lab:5000"

echo "=== Images dans la registry ==="
curl -s http://${REGISTRY}/v2/_catalog | jq -r '.repositories[]' | while read repo; do
    echo -e "\n📦 $repo"
    echo "  Tags:"
    curl -s http://${REGISTRY}/v2/${repo}/tags/list | jq -r '.tags[]' | sed 's/^/    - /'
done

