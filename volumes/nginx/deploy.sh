#!/bin/bash

# Nginx Reverse Proxy Deployment Script for Docker Swarm
# Usage: ./deploy-nginx.sh [start|stop|restart|logs|update]

set -e

STACK_NAME="base"
COMPOSE_FILE="01-service-hl.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker Swarm is initialized
check_swarm() {
    if ! docker info | grep -q "Swarm: active"; then
        print_error "Docker Swarm is not active. Please initialize swarm first:"
        echo "  docker swarm init"
        exit 1
    fi
    print_info "Docker Swarm is active"
}

# Function to create necessary networks
create_networks() {
    print_info "Creating Docker networks if they don't exist..."
    
    if ! docker network ls | grep -q "security_net"; then
        docker network create --driver overlay --attachable security_net
        print_info "Created security_net network"
    else
        print_info "security_net network already exists"
    fi
    
    if ! docker network ls | grep -q "monitoring_net"; then
        docker network create --driver overlay --attachable monitoring_net
        print_info "Created monitoring_net network"
    else
        print_info "monitoring_net network already exists"
    fi
}

# Function to create directory structure
create_directories() {
    print_info "Creating directory structure..."
    mkdir -p ssl
    mkdir -p logs
    print_info "Directory structure created"
}

# Function to test Nginx configuration
test_config() {
    print_info "Testing Nginx configuration..."
    docker run --rm -v "$(pwd)/nginx.conf:/etc/nginx/nginx.conf:ro" \
        -v "$(pwd)/upstreams.conf:/etc/nginx/conf.d/upstreams/upstreams.conf:ro" \
        -v "$(pwd)/site-faraday.conf:/etc/nginx/conf.d/sites/faraday.conf:ro" \
        -v "$(pwd)/site-zap.conf:/etc/nginx/conf.d/sites/zap.conf:ro" \
        -v "$(pwd)/site-grafana.conf:/etc/nginx/conf.d/sites/grafana.conf:ro" \
        -v "$(pwd)/site-prometheus.conf:/etc/nginx/conf.d/sites/prometheus.conf:ro" \
        nginx:alpine nginx -t
    
    if [ $? -eq 0 ]; then
        print_info "Nginx configuration is valid"
    else
        print_error "Nginx configuration has errors"
        exit 1
    fi
}

# Function to deploy the stack
deploy_stack() {
    print_info "Deploying Nginx reverse proxy stack..."
    docker stack deploy -c "$COMPOSE_FILE" "$STACK_NAME"
    print_info "Stack deployed successfully"
    
    print_info "Waiting for services to start..."
    sleep 5
    
    docker stack services "$STACK_NAME"
}

# Function to stop the stack
stop_stack() {
    print_info "Stopping Nginx reverse proxy stack..."
    docker service rm $(docker service ls |grep ngi| cut -d ' ' -f 0)
    print_info "Stack stopped. Waiting for cleanup..."
    sleep 10
}

# Function to restart the stack
restart_stack() {
    stop_stack
    deploy_stack
}

# Function to show logs
show_logs() {
    SERVICE_NAME="${STACK_NAME}_nginx"
    print_info "Showing logs for $SERVICE_NAME..."
    docker service logs -f "$SERVICE_NAME"
}

# Function to update the service
update_service() {
    print_info "Updating Nginx service with new configuration..."
    test_config
    docker service update --force "${STACK_NAME}_nginx"
    print_info "Service updated successfully"
}

# Function to show service status
show_status() {
    print_info "Service status:"
    docker stack services "$STACK_NAME"
    echo ""
    print_info "Service tasks:"
    docker service ps "${STACK_NAME}_nginx"
}

# Main script logic
case "${1:-}" in
    start)
        check_swarm
#        create_networks
        create_directories
        test_config
        deploy_stack
        ;;
    stop)
        check_swarm
        stop_stack
        ;;
    restart)
        check_swarm
        test_config
        restart_stack
        ;;
    logs)
        check_swarm
        show_logs
        ;;
    update)
        check_swarm
        update_service
        ;;
    status)
        check_swarm
        show_status
        ;;
    test)
        test_config
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|update|status|test}"
        echo ""
        echo "Commands:"
        echo "  start   - Deploy the Nginx reverse proxy stack"
        echo "  stop    - Remove the Nginx reverse proxy stack"
        echo "  restart - Restart the Nginx reverse proxy stack"
        echo "  logs    - Show logs from Nginx service"
        echo "  update  - Update service with new configuration"
        echo "  status  - Show service status and tasks"
        echo "  test    - Test Nginx configuration without deploying"
        exit 1
        ;;
esac

exit 0

