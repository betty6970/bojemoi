#!/bin/bash
# CLI pour interagir avec l'orchestrateur
# Usage: ./orchestrator-cli.sh [command] [options]

set -e

# Configuration
ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-https://orchestrator.bojemoi.lab}"

# Couleurs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Fonction d'aide
show_help() {
    cat << EOF
🤖 Orchestrator CLI - Bojemoi Lab

Usage: $0 [command] [options]

Commands:
    health                          Check orchestrator health
    list [limit]                    List recent deployments (default: 10)
    get <id>                        Get deployment details
    logs <id>                       Get deployment logs
    watch                           Watch deployments in real-time
    filter <status> [env]           Filter deployments by status/environment
    metrics                         Show Prometheus metrics
    webhook-test                    Test webhook endpoint

Environment Variables:
    ORCHESTRATOR_URL                Base URL (default: https://orchestrator.bojemoi.lab)

Examples:
    $0 health
    $0 list 20
    $0 get 123
    $0 logs 123
    $0 filter failed production
    $0 watch

EOF
}

# Fonctions API
api_call() {
    local endpoint=$1
    shift
    curl -sf "$ORCHESTRATOR_URL$endpoint" "$@"
}

cmd_health() {
    echo -e "${BLUE}🔍 Checking orchestrator health...${NC}"
    response=$(api_call "/health")
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Orchestrator is healthy${NC}"
        echo "$response" | jq
    else
        echo -e "${RED}❌ Orchestrator is not responding${NC}"
        exit 1
    fi
}

cmd_list() {
    local limit=${1:-10}
    echo -e "${BLUE}📋 Listing last $limit deployments...${NC}"
    
    response=$(api_call "/deployments?limit=$limit")
    
    if [ $? -eq 0 ]; then
        echo "$response" | jq -r '.deployments[] | 
            "\(.id)\t\(.name)\t\(.status)\t\(.environment)\t\(.created_at)"' |
            column -t -s $'\t' -N "ID,NAME,STATUS,ENV,CREATED"
    else
        echo -e "${RED}❌ Failed to fetch deployments${NC}"
        exit 1
    fi
}

cmd_get() {
    local id=$1
    
    if [ -z "$id" ]; then
        echo -e "${RED}❌ Deployment ID required${NC}"
        echo "Usage: $0 get <id>"
        exit 1
    fi
    
    echo -e "${BLUE}📊 Fetching deployment $id...${NC}"
    
    response=$(api_call "/deployments/$id")
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Deployment details:${NC}"
        echo "$response" | jq '.deployment'
    else
        echo -e "${RED}❌ Deployment not found${NC}"
        exit 1
    fi
}

cmd_logs() {
    local id=$1
    
    if [ -z "$id" ]; then
        echo -e "${RED}❌ Deployment ID required${NC}"
        echo "Usage: $0 logs <id>"
        exit 1
    fi
    
    echo -e "${BLUE}📝 Fetching logs for deployment $id...${NC}"
    
    response=$(api_call "/deployments/$id")
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Deployment logs:${NC}"
        echo "$response" | jq -r '.logs[] | 
            "[\(.timestamp)] \(.level | ascii_upcase): \(.message)"'
    else
        echo -e "${RED}❌ Failed to fetch logs${NC}"
        exit 1
    fi
}

cmd_watch() {
    echo -e "${BLUE}👀 Watching deployments (Ctrl+C to stop)...${NC}"
    
    while true; do
        clear
        echo -e "${BLUE}=== Deployments (refreshing every 5s) ===${NC}"
        cmd_list 10
        sleep 5
    done
}

cmd_filter() {
    local status=$1
    local env=$2
    
    if [ -z "$status" ]; then
        echo -e "${RED}❌ Status required${NC}"
        echo "Usage: $0 filter <status> [environment]"
        echo "Status: pending, in_progress, completed, failed"
        exit 1
    fi
    
    local query="status=$status"
    if [ -n "$env" ]; then
        query="$query&environment=$env"
    fi
    
    echo -e "${BLUE}🔍 Filtering deployments: $query${NC}"
    
    response=$(api_call "/deployments?$query")
    
    if [ $? -eq 0 ]; then
        echo "$response" | jq -r '.deployments[] | 
            "\(.id)\t\(.name)\t\(.status)\t\(.environment)\t\(.created_at)"' |
            column -t -s $'\t' -N "ID,NAME,STATUS,ENV,CREATED"
    else
        echo -e "${RED}❌ Failed to fetch deployments${NC}"
        exit 1
    fi
}

cmd_metrics() {
    echo -e "${BLUE}📊 Fetching metrics...${NC}"
    
    response=$(api_call "/metrics")
    
    if [ $? -eq 0 ]; then
        echo "$response" | grep -E "^(webhook_received_total|deployments_total|deployment_duration)" | head -20
    else
        echo -e "${RED}❌ Failed to fetch metrics${NC}"
        exit 1
    fi
}

cmd_webhook_test() {
    echo -e "${BLUE}🧪 Testing webhook endpoint...${NC}"
    
    response=$(curl -sf -X POST "$ORCHESTRATOR_URL/webhook/gitea" \
        -H "Content-Type: application/json" \
        -d '{
            "ref": "refs/heads/main",
            "repository": {
                "name": "test-repo",
                "owner": {"username": "test"}
            },
            "commits": [{"id": "test123", "message": "test"}]
        }' 2>&1)
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Webhook endpoint is working${NC}"
        echo "$response" | jq
    else
        echo -e "${RED}❌ Webhook test failed${NC}"
        echo "$response"
        exit 1
    fi
}

# Main
case "${1:-help}" in
    health)
        cmd_health
        ;;
    list|ls)
        cmd_list "${2:-10}"
        ;;
    get|show)
        cmd_get "$2"
        ;;
    logs)
        cmd_logs "$2"
        ;;
    watch)
        cmd_watch
        ;;
    filter)
        cmd_filter "$2" "$3"
        ;;
    metrics)
        cmd_metrics
        ;;
    webhook-test)
        cmd_webhook_test
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac

