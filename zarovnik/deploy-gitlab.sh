#!/bin/bash

set -e

# GitLab Stack Deployment Script for bojemoi.lab.local
# This script deploys GitLab CE with integrated CI/CD runner to Docker Swarm

echo "=========================================="
echo "GitLab Stack Deployment for Docker Swarm"
echo "=========================================="
echo ""

# Configuration
STACK_NAME="gitlab"
STACK_FILE="stack/70-service-zarovnik.yml"
GITLAB_URL="https://gitlab.bojemoi.lab.local"
REGISTRY_URL="https://registry.bojemoi.lab.local"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running on swarm manager
if ! docker node ls &> /dev/null; then
    echo -e "${RED}Error: This script must be run on a Docker Swarm manager node${NC}"
    exit 1
fi

# Check if traefik_public network exists
if ! docker network ls | grep -q proxy; then
    echo -e "${YELLOW}Warning: traefik proxy network not found. Creating it...${NC}"
    docker network create --driver=overlay --attachable proxy
fi

echo -e "${GREEN}Step 1: Deploying GitLab stack...${NC}"
docker stack deploy -c $STACK_FILE $STACK_NAME

echo ""
echo -e "${YELLOW}Waiting for GitLab to start (this may take 3-5 minutes)...${NC}"
echo "You can monitor the logs with: docker service logs -f ${STACK_NAME}_gitlab"
echo ""

# Wait for GitLab to be healthy
TIMEOUT=600
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if docker service ps ${STACK_NAME}_gitlab --filter "desired-state=running" --format "{{.CurrentState}}" | grep -q "Running"; then
        echo -e "${GREEN}GitLab service is running!${NC}"
        break
    fi
    sleep 10
    ELAPSED=$((ELAPSED + 10))
    echo "Waiting... ($ELAPSED seconds)"
done

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo -e "${RED}Timeout waiting for GitLab to start${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Waiting an additional 2 minutes for GitLab to fully initialize...${NC}"
sleep 120

echo ""
echo -e "${GREEN}Step 2: Retrieving initial root password...${NC}"
echo ""

# Get the container ID
CONTAINER_ID=$(docker ps --filter "name=${STACK_NAME}_gitlab" --format "{{.ID}}" | head -n 1)

if [ -z "$CONTAINER_ID" ]; then
    echo -e "${RED}Error: Could not find GitLab container${NC}"
    exit 1
fi

echo "Attempting to retrieve initial root password..."
ROOT_PASSWORD=$(docker exec $CONTAINER_ID cat /etc/gitlab/initial_root_password 2>/dev/null | grep "Password:" | awk '{print $2}' || echo "")

if [ -n "$ROOT_PASSWORD" ]; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "GitLab Initial Root Password"
    echo "==========================================${NC}"
    echo ""
    echo "Username: root"
    echo "Password: $ROOT_PASSWORD"
    echo ""
    echo -e "${YELLOW}IMPORTANT: Save this password! It will be deleted after 24 hours.${NC}"
    echo ""
else
    echo -e "${YELLOW}Could not retrieve password automatically. It may have already been deleted.${NC}"
    echo "If this is a fresh installation, wait a few more minutes and check:"
    echo "  docker exec \$(docker ps -qf \"name=${STACK_NAME}_gitlab\") cat /etc/gitlab/initial_root_password"
    echo ""
fi

echo -e "${GREEN}Step 3: GitLab Runner registration instructions${NC}"
echo ""
echo "After logging into GitLab, register the runner:"
echo ""
echo "1. Get a registration token from GitLab:"
echo "   - Navigate to: $GITLAB_URL/admin/runners"
echo "   - Click 'Register an instance runner'"
echo "   - Copy the registration token"
echo ""
echo "2. Register the runner with this command:"
echo ""
echo "docker exec -it \$(docker ps -qf \"name=${STACK_NAME}_gitlab-runner\") \\"
echo "  gitlab-runner register \\"
echo "  --non-interactive \\"
echo "  --url \"$GITLAB_URL\" \\"
echo "  --registration-token \"YOUR_TOKEN_HERE\" \\"
echo "  --executor \"docker\" \\"
echo "  --docker-image \"alpine:latest\" \\"
echo "  --description \"swarm-runner\" \\"
echo "  --tag-list \"docker,swarm\" \\"
echo "  --docker-privileged \\"
echo "  --docker-volumes /var/run/docker.sock:/var/run/docker.sock \\"
echo "  --docker-network-mode \"${STACK_NAME}_gitlab_internal\""
echo ""

echo -e "${GREEN}Step 4: DNS configuration${NC}"
echo ""
echo "Add these entries to your dnsmasq configuration:"
echo ""
echo "address=/gitlab.bojemoi.lab.local/YOUR_SWARM_IP"
echo "address=/registry.bojemoi.lab.local/YOUR_SWARM_IP"
echo ""

echo -e "${GREEN}Step 5: Docker registry authentication${NC}"
echo ""
echo "After creating a personal access token in GitLab with 'read_registry' and 'write_registry' scopes:"
echo ""
echo "docker login $REGISTRY_URL"
echo "Username: your_gitlab_username"
echo "Password: your_personal_access_token"
echo ""

echo -e "${GREEN}=========================================="
echo "Deployment Summary"
echo "==========================================${NC}"
echo ""
echo "GitLab URL:       $GITLAB_URL"
echo "Registry URL:     $REGISTRY_URL"
echo "Stack name:       $STACK_NAME"
echo ""
echo "Useful commands:"
echo "  docker stack ps $STACK_NAME                    # Check service status"
echo "  docker service logs -f ${STACK_NAME}_gitlab    # View GitLab logs"
echo "  docker service logs -f ${STACK_NAME}_gitlab-runner  # View runner logs"
echo "  docker stack rm $STACK_NAME                    # Remove the stack"
echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo ""
