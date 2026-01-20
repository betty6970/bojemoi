#!/bin/bash
set -e

echo "======================================"
echo "Bojemoi Orchestrator - Installation"
echo "======================================"

# Check dependencies
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is required"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "Error: Docker Compose is required"
    exit 1
fi

# Create directories
mkdir -p logs data config backups

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env with your configuration before continuing!"
    echo "Then run this script again."
    exit 0
fi

# Build
echo "Building images..."
docker compose build

# Start database
echo "Starting PostgreSQL..."
docker compose up -d postgres
sleep 10

# Start all services
echo "Starting all services..."
docker compose up -d

# Wait for API
echo "Waiting for API..."
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ API is ready"
        break
    fi
    attempt=$((attempt + 1))
    sleep 2
done

echo ""
echo "======================================"
echo "✅ Installation Complete!"
echo "======================================"
echo ""
echo "Services:"
echo "  API:        http://localhost:8000"
echo "  Prometheus: http://localhost:9090"
echo "  Grafana:    http://localhost:3000"
echo ""
echo "Next steps:"
echo "  make logs    # View logs"
echo "  make status  # Check status"
echo "  python cli.py --help  # Use CLI"
echo ""

