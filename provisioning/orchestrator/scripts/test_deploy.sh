#!/bin/bash

# Test deployment script for Bojemoi Orchestrator

set -e

API_URL="${API_URL:-http://localhost:8000}"

echo "Testing Bojemoi Orchestrator API..."
echo "API URL: $API_URL"
echo

# Health check
echo "=== Health Check ==="
curl -s "$API_URL/health" | jq .
echo
echo

# Test VM deployment
echo "=== Test VM Deployment ==="
curl -X POST "$API_URL/api/v1/vm/deploy" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-web-01",
    "template": "webserver",
    "os_type": "alpine",
    "cpu": 2,
    "memory": 2048,
    "disk": 20,
    "environment": "staging"
  }' | jq .
echo
echo

# Test container deployment
echo "=== Test Container Deployment ==="
curl -X POST "$API_URL/api/v1/container/deploy" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-nginx",
    "image": "nginx:alpine",
    "replicas": 1,
    "ports": ["8080:80"],
    "networks": ["bojemoi-net"]
  }' | jq .
echo
echo

# List deployments
echo "=== List Deployments ==="
curl -s "$API_URL/api/v1/deployments" | jq .
echo
echo

echo "Tests completed!"
