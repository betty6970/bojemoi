# Database Migrations

This directory contains Alembic database migrations for the Bojemoi Orchestrator.

## Overview

The orchestrator uses multiple PostgreSQL databases:

| Database | Purpose | Tables |
|----------|---------|--------|
| `deployments` | Main deployment tracking | `deployments`, `alembic_version` |
| `karacho` | Blockchain audit trail | `deployment_blocks` |
| `ip2location` | IP geolocation data | (managed separately) |

## Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r ../requirements.txt

# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password
export POSTGRES_DB=deployments
```

### Common Commands

```bash
# Check current migration status
alembic current

# View migration history
alembic history

# Apply all pending migrations
alembic upgrade head

# Apply migrations to specific revision
alembic upgrade 001

# Rollback one migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base

# Generate new migration (after model changes)
alembic revision -m "description_of_changes"

# Show SQL without executing (dry run)
alembic upgrade head --sql
```

## Migration Files

Migrations are stored in `versions/` directory:

```
versions/
├── 20260129_0001_001_initial_schema.py  # Initial tables
└── ...
```

### Naming Convention

Migration files follow the pattern:
```
YYYYMMDD_HHMM_XXX_description.py
```

- `YYYYMMDD_HHMM`: Timestamp
- `XXX`: Sequential revision ID
- `description`: Brief description (snake_case)

## Creating New Migrations

### Manual Migration

```bash
# Create empty migration
alembic revision -m "add_new_column"
```

Then edit the generated file in `versions/`.

### Auto-generate Migration (if using SQLAlchemy models)

```bash
# Generate migration from model changes
alembic revision --autogenerate -m "add_new_column"
```

## Multi-Database Setup

The orchestrator uses separate databases. To run migrations on different databases:

```bash
# Main deployments database (default)
export POSTGRES_DB=deployments
alembic upgrade head

# Blockchain database
export POSTGRES_DB=karacho
alembic upgrade head
```

**Note**: The `deployment_blocks` table is created by the BlockchainService on startup,
but the migration is provided for consistency and manual database setup.

## Production Deployment

### Pre-deployment Checklist

1. Backup the database
2. Test migrations on staging first
3. Review migration SQL with `--sql` flag
4. Schedule maintenance window if needed

### Running Migrations

```bash
# 1. Set production credentials
export POSTGRES_HOST=postgres.production
export POSTGRES_PASSWORD=$PRODUCTION_DB_PASSWORD

# 2. Check current state
alembic current

# 3. Preview changes
alembic upgrade head --sql > migration.sql
cat migration.sql

# 4. Apply migrations
alembic upgrade head

# 5. Verify
alembic current
```

### Rollback Procedure

```bash
# Rollback last migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade 001

# Rollback all (use with caution!)
alembic downgrade base
```

## Troubleshooting

### "Target database is not up to date"

```bash
# Stamp the database with current revision without running migrations
alembic stamp head
```

### "Can't locate revision"

```bash
# List all revisions
alembic history --verbose

# Check for orphaned revisions
alembic branches
```

### Connection Issues

```bash
# Test database connection
python -c "
import os
import psycopg2
conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST', 'localhost'),
    port=os.getenv('POSTGRES_PORT', 5432),
    user=os.getenv('POSTGRES_USER', 'postgres'),
    password=os.getenv('POSTGRES_PASSWORD'),
    database=os.getenv('POSTGRES_DB', 'deployments')
)
print('Connection successful')
conn.close()
"
```

## Schema Reference

### deployments Table

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| type | VARCHAR(50) | vm, container |
| name | VARCHAR(255) | Deployment name |
| config | JSONB | Configuration data |
| resource_ref | VARCHAR(255) | XenServer/Docker reference |
| status | VARCHAR(50) | pending, running, success, failed |
| error | TEXT | Error message |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update time |

### deployment_blocks Table (Blockchain)

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| block_number | BIGINT | Block number (0 = genesis) |
| previous_hash | VARCHAR(64) | SHA-256 of previous block |
| current_hash | VARCHAR(64) | SHA-256 of this block |
| deployment_type | VARCHAR(50) | genesis, vm, container |
| name | VARCHAR(255) | Deployment name |
| config | JSONB | Configuration snapshot |
| resource_ref | VARCHAR(255) | Resource reference |
| status | VARCHAR(50) | Deployment status |
| error | TEXT | Error message |
| source_ip | VARCHAR(45) | Request source IP |
| source_country | VARCHAR(10) | ISO country code |
| created_at | TIMESTAMP | Block creation time |
