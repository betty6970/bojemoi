# Déployer un container
curl -X POST https://provisioning.bojemoi.lab/api/v1/container/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nginx-proxy",
    "image": "nginx:alpine",
    "replicas": 2,
    "ports": ["80:80", "443:443"]
  }'

