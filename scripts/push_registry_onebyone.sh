#!/bin/bash
# Push images to local registry
# Usage:
#   ./push_registry_onebyone.sh <image-name>     - Push single image
#   ./push_registry_onebyone.sh --all            - Push all images from list

set -e

# List of images used in stack/01-service-hl.yml
IMAGES=(
    # Database
    "postgres"
    "dpage/pgadmin4"
    "prometheuscommunity/postgres-exporter"

    # Monitoring
    "grafana/grafana"
    "grafana/loki"
    "grafana/alloy"
    "grafana/tempo"
    "prom/prometheus"
    "prom/alertmanager"
    "prom/node-exporter"
    "gcr.io/cadvisor/cadvisor"

    # Security
    "jasonish/suricata"
    "corelight/suricata_exporter"

    # Mail
    "boky/postfix"
    "blackflysolutions/postfix-exporter"
    "shenxn/protonmail-bridge"

    # Custom/Other
    "koursk"
    "koursk-2"
    "provisioning"
)

push_image() {
    local img="$1"
    echo "=== Pushing $img ==="
    docker pull "$img:latest"
    docker tag "$img:latest" "localhost:5000/$img:latest"
    docker push "localhost:5000/$img:latest"
    echo "✓ Done: $img"
    echo ""
}

if [ "$1" == "--all" ]; then
    echo "Pushing all images to local registry..."
    for img in "${IMAGES[@]}"; do
        push_image "$img" || echo "✗ Failed: $img"
    done
    echo "=== All done ==="
elif [ "$1" == "--list" ]; then
    echo "Images in list:"
    for img in "${IMAGES[@]}"; do
        echo "  - $img"
    done
elif [ -n "$1" ]; then
    push_image "$1"
else
    echo "Usage:"
    echo "  $0 <image-name>   - Push single image"
    echo "  $0 --all          - Push all images from list"
    echo "  $0 --list         - Show all images in list"
fi
