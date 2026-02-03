#!/bin/bash
# Database Migration Helper Script for Bojemoi Orchestrator
#
# Usage:
#   ./scripts/migrate.sh [command] [options]
#
# Commands:
#   upgrade     Apply all pending migrations (default)
#   downgrade   Rollback migrations
#   current     Show current revision
#   history     Show migration history
#   generate    Generate new migration
#   sql         Show SQL without executing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to orchestrator directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Load environment variables from .env if exists
if [ -f .env ]; then
    echo -e "${YELLOW}Loading environment from .env${NC}"
    export $(grep -v '^#' .env | xargs)
fi

# Validate required environment variables
check_env() {
    if [ -z "$POSTGRES_PASSWORD" ]; then
        echo -e "${RED}Error: POSTGRES_PASSWORD environment variable is not set${NC}"
        echo "Set it with: export POSTGRES_PASSWORD=your_password"
        exit 1
    fi
}

# Show help
show_help() {
    echo "Bojemoi Database Migration Tool"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  upgrade [revision]    Apply migrations (default: head)"
    echo "  downgrade [revision]  Rollback migrations (default: -1)"
    echo "  current               Show current database revision"
    echo "  history               Show migration history"
    echo "  generate <message>    Generate new migration file"
    echo "  sql [revision]        Show SQL for migrations without executing"
    echo "  stamp <revision>      Stamp database with revision without migrating"
    echo "  check                 Check database connection"
    echo ""
    echo "Options:"
    echo "  --db <name>           Target database (default: deployments)"
    echo "                        Options: deployments, karacho"
    echo ""
    echo "Examples:"
    echo "  $0 upgrade                    # Apply all pending migrations"
    echo "  $0 upgrade 001                # Upgrade to revision 001"
    echo "  $0 downgrade -1               # Rollback one migration"
    echo "  $0 downgrade base             # Rollback all migrations"
    echo "  $0 generate 'add user table'  # Create new migration"
    echo "  $0 sql head                   # Show SQL for all pending"
    echo "  $0 --db karacho upgrade       # Migrate blockchain database"
}

# Check database connection
check_connection() {
    echo -e "${YELLOW}Checking database connection...${NC}"
    python3 -c "
import os
import psycopg2
try:
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=os.getenv('POSTGRES_PORT', 5432),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD'),
        database=os.getenv('POSTGRES_DB', 'deployments')
    )
    print('Connection successful!')
    conn.close()
except Exception as e:
    print(f'Connection failed: {e}')
    exit(1)
"
}

# Parse arguments
DB_NAME="${POSTGRES_DB:-deployments}"
COMMAND="upgrade"
ARGS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --db)
            DB_NAME="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        upgrade|downgrade|current|history|generate|sql|stamp|check)
            COMMAND="$1"
            shift
            ARGS="$@"
            break
            ;;
        *)
            ARGS="$@"
            break
            ;;
    esac
done

# Set database
export POSTGRES_DB="$DB_NAME"
echo -e "${GREEN}Target database: $POSTGRES_DB${NC}"

# Execute command
case $COMMAND in
    upgrade)
        check_env
        REVISION="${ARGS:-head}"
        echo -e "${YELLOW}Upgrading to: $REVISION${NC}"
        alembic upgrade "$REVISION"
        echo -e "${GREEN}Migration complete!${NC}"
        ;;
    downgrade)
        check_env
        REVISION="${ARGS:--1}"
        echo -e "${YELLOW}Downgrading to: $REVISION${NC}"
        read -p "Are you sure you want to rollback? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            alembic downgrade "$REVISION"
            echo -e "${GREEN}Rollback complete!${NC}"
        else
            echo -e "${YELLOW}Rollback cancelled${NC}"
        fi
        ;;
    current)
        check_env
        echo -e "${YELLOW}Current revision:${NC}"
        alembic current
        ;;
    history)
        echo -e "${YELLOW}Migration history:${NC}"
        alembic history --verbose
        ;;
    generate)
        if [ -z "$ARGS" ]; then
            echo -e "${RED}Error: Please provide a message for the migration${NC}"
            echo "Usage: $0 generate 'description of changes'"
            exit 1
        fi
        echo -e "${YELLOW}Generating migration: $ARGS${NC}"
        alembic revision -m "$ARGS"
        echo -e "${GREEN}Migration file created!${NC}"
        ;;
    sql)
        check_env
        REVISION="${ARGS:-head}"
        echo -e "${YELLOW}SQL for upgrade to: $REVISION${NC}"
        echo "----------------------------------------"
        alembic upgrade "$REVISION" --sql
        ;;
    stamp)
        check_env
        if [ -z "$ARGS" ]; then
            echo -e "${RED}Error: Please provide a revision to stamp${NC}"
            exit 1
        fi
        echo -e "${YELLOW}Stamping database with: $ARGS${NC}"
        alembic stamp "$ARGS"
        echo -e "${GREEN}Database stamped!${NC}"
        ;;
    check)
        check_env
        check_connection
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        show_help
        exit 1
        ;;
esac
