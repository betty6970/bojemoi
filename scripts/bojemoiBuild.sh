#!/bin/ash
# bojemoiBuild.sh - Bojemoi Docker Stack Builder for Alpine Linux
# Usage: ./bojemoiBuild.sh stack1 [stack2 ...]
# Download: rm bojemoiBuild.sh; wget http://bojemoi.me/docker/bojemoiBuild.sh; chmod +x bojemoiBuild.sh; ./bojemoiBuild.sh base bojemoi
# Copytight 
set -e  # Exit on any error
set -u  # Exit on undefined variables

# Configuration
readonly BOJEMOI_DIR="/opt/bojemoi"
readonly BASE_URL="http://bojemoi.me/docker"
readonly REGISTRY_URL="http://localhost:5000"

# Color codes for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly NC='\033[0m' # No Color

# Logging functions
log_info() {
    printf "${GREEN}[INFO]${NC} %s\n" "$1"
}

log_warn() {
    printf "${YELLOW}[WARN]${NC} %s\n" "$1"
}

log_error() {
    printf "${RED}[ERROR]${NC} %s\n" "$1" >&2
}

# Print usage information
usage() {
    cat << EOF
Usage: $0 stack1 [stack2 ...]

This script builds and deploys Bojemoi Docker stacks.

Arguments:
    stack1, stack2, ...    Names of stacks to deploy

Example:
    $0 base bojemoi

EOF
}

# Check if running as root (inverted logic fixed)
check_root() {
    if [ "$(id -u)" -eq 0 ]; then
        log_error "This script should not be run as root for security reasons."
        exit 1
    fi
    log_info "Running as non-root user: $(whoami)"
}

# Check if required commands exist
check_dependencies() {
    local missing_deps=""
    
    for cmd in docker wget curl mkdir rm; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing_deps="$missing_deps $cmd"
        fi
    done
    
    if [ -n "$missing_deps" ]; then
        log_error "Missing required commands:$missing_deps"
        log_error "Please install the missing dependencies and try again."
        exit 1
    fi
}

# Validate arguments
validate_args() {
    if [ $# -eq 0 ]; then
        log_error "No arguments provided."
        usage
        exit 1
    fi
}

# Create directory structure
setup_directories() {
    log_info "Setting up directory structure..."
    
    # Remove existing directories if they exist
    if [ -d "$BOJEMOI_DIR/berezina" ]; then
        rm -rf "$BOJEMOI_DIR/berezina"
    fi
    if [ -d "$BOJEMOI_DIR/karacho" ]; then
        rm -rf "$BOJEMOI_DIR/karacho"
    fi
    
    # Create directories
    mkdir -p "$BOJEMOI_DIR/berezina/list_vpn"
    mkdir -p "$BOJEMOI_DIR/karacho"
}

# Download required files
download_files() {
    log_info "Downloading required files..."
    
    cd "$BOJEMOI_DIR" || {
        log_error "Failed to change directory to $BOJEMOI_DIR"
        exit 1
    }
    
    # Download berezina files
    if ! wget -r -nH -np --cut-dirs=2 --reject="*.html?C=*;O=*" \
        "$BASE_URL/berezina/" -P berezina; then
        log_error "Failed to download berezina files"
        exit 1
    fi
    
    # Download karacho files
    if ! wget -r -nH -np --cut-dirs=2 --reject="*.html?C=*;O=*" \
        "$BASE_URL/karacho/" -P karacho; then
        log_error "Failed to download karacho files"
        exit 1
    fi
    
    # Download YAML files
    if ! wget -r -nH -np --cut-dirs=1 -A "*.yaml" "$BASE_URL/"; then
        log_error "Failed to download YAML files"
        exit 1
    fi
}

# Initialize Docker Swarm
init_swarm() {
    log_info "Initializing Docker Swarm..."
    
    # Check if already part of a swarm
    if docker swarm init ; then
        log_warn "Already part of a Docker Swarm, continue"
    fi
}

# Deploy stacks
deploy_stacks() {
    log_info "Deploying stacks..."
    
    for stack in "$@"; do
        local stack_file="service-${stack}.yaml"
        
        if [ ! -f "$stack_file" ]; then
            log_warn "Stack file $stack_file not found, skipping..."
            continue
        fi
        
        log_info "Deploying stack: $stack"
        if docker stack deploy -c "$stack_file" "$stack"; then
            log_info "Stack $stack deployed successfully"
            docker stack ps "$stack"
        else
            log_error "Failed to deploy stack: $stack"
        fi
    done
}

# Show cluster status
show_cluster_status() {
    log_info "Cluster Status:"
    echo "===================="
    
    echo "Stacks:"
    echo "===================="
    docker stack ls
    
    echo -e "\nNodes:"
    echo "===================="
    docker node ls
    
    echo -e "\nServices:"
    echo "===================="
    docker service ls
    
    echo -e "\nNetworks:"
    echo "===================="
    docker network ls
}

# Handle local registry creation
handle_local_registry() {
    printf "\nDo you want to create images in the local registry? (y/N): "
    read -r answer
    
    case "$answer" in
        [Yy]|[Yy][Ee][Ss])
            log_info "Creating local registry images..."
            
            # Download and execute cccp.sh script
            if wget -O cccp.sh "$BASE_URL/cccp.sh" && chmod +x cccp.sh; then
                ./cccp.sh berezina || log_warn "Failed to process berezina images"
                ./cccp.sh karacho || log_warn "Failed to process karacho images"
            else
                log_error "Failed to download cccp.sh script"
            fi
            
            # Show registry catalog
            log_info "Local registry catalog:"
            if curl -4 "$REGISTRY_URL/v2/_catalog" 2>/dev/null; then
                echo
            else
                log_warn "Could not connect to local registry at $REGISTRY_URL"
            fi
            ;;
        *)
            log_info "Skipping local registry creation"
            ;;
    esac
}

# Deploy bojemoi stack
deploy_bojemoi() {
    log_info "Deploying bojemoi stack..."
    
    if [ -f "service-bojemoi.yaml" ]; then
        docker stack deploy -c service-bojemoi.yaml bojemoi
    else
        log_warn "service-bojemoi.yaml not found, skipping bojemoi deployment"
    fi
}

# Show final status and tokens
show_final_status() {
    echo -e "\n===================="
    log_info "Final Status:"
    echo "===================="
    
    docker stack ls
    echo "===================="
    docker node ls
    echo "===================="
    docker service ls
    
    echo -e "\nStack Details:"
    docker stack ps base 2>/dev/null || log_warn "Base stack not found"
    docker stack ps bojemoi 2>/dev/null || log_warn "Bojemoi stack not found"
    
    echo -e "\nSwarm Join Tokens:"
    echo "Manager token:"
    docker swarm join-token manager
    
    echo -e "\nWorker token:"
    docker swarm join-token worker
    
    log_info "Setup complete!"
}

# Create monitoring alias
create_monitoring_alias() {
    cat << 'EOF'

# Add this to your shell profile (~/.profile or ~/.ashrc) for stack monitoring:
alias stack-stats='f(){ docker stats $(docker ps --filter "label=com.docker.stack.namespace=$1" --format "{{.Names}}"); }; f'

# Usage example:
# stack-stats bojemoi
EOF
}

# Main execution
main() {
    echo "--------------------------------------------------------------------------------------------------------------------"
    echo " Step 3: Cloud-init installation complete"
    echo ""
    echo " Now installing Metasploit image build and creating bojemoi stack with base services"
    echo "--------------------------------------------------------------------------------------------------------------------"
    
    check_root
    check_dependencies
    validate_args "$@"
    setup_directories
    download_files
    init_swarm
    deploy_stacks "$@"
    show_cluster_status
    handle_local_registry
    deploy_bojemoi
    show_final_status
    create_monitoring_alias
}

# Execute main function with all arguments
main "$@"

