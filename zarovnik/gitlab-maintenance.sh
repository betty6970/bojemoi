#!/bin/bash

# GitLab Backup and Maintenance Script
# Run this regularly to backup GitLab data and perform maintenance

set -e

STACK_NAME="gitlab"
BACKUP_RETENTION_DAYS=7

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=========================================="
echo "GitLab Backup and Maintenance"
echo "=========================================="
echo ""

# Get GitLab container
GITLAB_CONTAINER=$(docker ps --filter "name=${STACK_NAME}_gitlab" --format "{{.ID}}" | head -n 1)

if [ -z "$GITLAB_CONTAINER" ]; then
    echo -e "${RED}Error: GitLab container not found${NC}"
    exit 1
fi

# Function to create backup
create_backup() {
    echo -e "${GREEN}Creating GitLab backup...${NC}"
    docker exec -t $GITLAB_CONTAINER gitlab-backup create SKIP=registry
    
    echo -e "${GREEN}Backup created successfully${NC}"
    
    # List recent backups
    echo ""
    echo "Recent backups:"
    docker exec -t $GITLAB_CONTAINER ls -lh /var/opt/gitlab/backups/ | tail -n 5
}

# Function to restore from backup
restore_backup() {
    local BACKUP_FILE=$1
    
    if [ -z "$BACKUP_FILE" ]; then
        echo -e "${RED}Error: No backup file specified${NC}"
        echo "Usage: $0 restore <backup_timestamp>"
        exit 1
    fi
    
    echo -e "${YELLOW}WARNING: This will restore GitLab from backup${NC}"
    echo "Backup file: $BACKUP_FILE"
    echo ""
    read -p "Are you sure? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo "Restore cancelled"
        exit 0
    fi
    
    echo -e "${GREEN}Stopping GitLab services...${NC}"
    docker exec -t $GITLAB_CONTAINER gitlab-ctl stop puma
    docker exec -t $GITLAB_CONTAINER gitlab-ctl stop sidekiq
    
    echo -e "${GREEN}Restoring from backup...${NC}"
    docker exec -t $GITLAB_CONTAINER gitlab-backup restore BACKUP=$BACKUP_FILE
    
    echo -e "${GREEN}Restarting GitLab...${NC}"
    docker exec -t $GITLAB_CONTAINER gitlab-ctl restart
    
    echo -e "${GREEN}Checking GitLab status...${NC}"
    docker exec -t $GITLAB_CONTAINER gitlab-rake gitlab:check SANITIZE=true
    
    echo -e "${GREEN}Restore completed${NC}"
}

# Function to cleanup old backups
cleanup_old_backups() {
    echo -e "${GREEN}Cleaning up backups older than ${BACKUP_RETENTION_DAYS} days...${NC}"
    docker exec -t $GITLAB_CONTAINER find /var/opt/gitlab/backups/ -type f -name "*.tar" -mtime +${BACKUP_RETENTION_DAYS} -delete
    echo -e "${GREEN}Cleanup completed${NC}"
}

# Function to check GitLab health
check_health() {
    echo -e "${GREEN}Checking GitLab health...${NC}"
    docker exec -t $GITLAB_CONTAINER gitlab-rake gitlab:check SANITIZE=true
    
    echo ""
    echo -e "${GREEN}Checking GitLab environment...${NC}"
    docker exec -t $GITLAB_CONTAINER gitlab-rake gitlab:env:info
}

# Function to reconfigure GitLab
reconfigure() {
    echo -e "${GREEN}Reconfiguring GitLab...${NC}"
    docker exec -t $GITLAB_CONTAINER gitlab-ctl reconfigure
    echo -e "${GREEN}Reconfiguration completed${NC}"
}

# Function to show logs
show_logs() {
    echo -e "${GREEN}Recent GitLab logs:${NC}"
    docker service logs --tail 100 ${STACK_NAME}_gitlab
}

# Function to optimize database
optimize_database() {
    echo -e "${GREEN}Optimizing PostgreSQL database...${NC}"
    docker exec -t $GITLAB_CONTAINER gitlab-rake gitlab:db:reindex
    docker exec -t $GITLAB_CONTAINER gitlab-rake gitlab:db:analyze
    echo -e "${GREEN}Database optimization completed${NC}"
}

# Function to show disk usage
show_disk_usage() {
    echo -e "${GREEN}GitLab disk usage:${NC}"
    echo ""
    docker exec -t $GITLAB_CONTAINER du -sh /var/opt/gitlab/* 2>/dev/null | sort -h
}

# Main menu
case "${1:-menu}" in
    backup)
        create_backup
        cleanup_old_backups
        ;;
    restore)
        restore_backup "$2"
        ;;
    cleanup)
        cleanup_old_backups
        ;;
    health)
        check_health
        ;;
    reconfigure)
        reconfigure
        ;;
    logs)
        show_logs
        ;;
    optimize)
        optimize_database
        ;;
    disk)
        show_disk_usage
        ;;
    menu|*)
        echo "GitLab Maintenance Script"
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "Commands:"
        echo "  backup        Create a new backup"
        echo "  restore       Restore from backup (requires backup timestamp)"
        echo "  cleanup       Remove old backups"
        echo "  health        Check GitLab health"
        echo "  reconfigure   Reconfigure GitLab"
        echo "  logs          Show recent logs"
        echo "  optimize      Optimize database"
        echo "  disk          Show disk usage"
        echo ""
        echo "Examples:"
        echo "  $0 backup"
        echo "  $0 restore 1638360000_2024_11_26"
        echo "  $0 health"
        ;;
esac
