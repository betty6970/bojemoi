#!/bin/bash

echo "Health Check..."

curl -s http://localhost:8000/health | jq .

echo ""
echo "Services status:"
docker compose ps

