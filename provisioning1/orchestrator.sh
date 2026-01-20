#!/bin/bash
# generate-project.sh
# Script pour générer la structure complète du projet Bojemoi Orchestrator

set -e

PROJECT_NAME="bojemoi-orchestrator"
VERSION="1.0.0"
OUTPUT_FILE="${PROJECT_NAME}-${VERSION}.tar.gz"

echo "======================================"
echo "Bojemoi Orchestrator Project Generator"
echo "Version: ${VERSION}"
echo "======================================"
echo ""

# Créer le répertoire temporaire
TEMP_DIR=$(mktemp -d)
PROJECT_DIR="${TEMP_DIR}/${PROJECT_NAME}"

echo "Creating project structure in: ${PROJECT_DIR}"
mkdir -p "${PROJECT_DIR}"

# Créer la structure de répertoires
echo "Creating directory structure..."
mkdir -p "${PROJECT_DIR}"/{orchestrator,tests,scripts,config,examples,docs,grafana,logs,data}
mkdir -p "${PROJECT_DIR}/orchestrator"/{managers,models,validators}
mkdir -p "${PROJECT_DIR}/examples"/{vms,containers,services,cloud-init}
mkdir -p "${PROJECT_DIR}/grafana"/{dashboards,provisioning/datasources,provisioning/dashboards}
mkdir -p "${PROJECT_DIR}/.github"/{ISSUE_TEMPLATE,PULL_REQUEST_TEMPLATE,workflows}

# Fonction pour créer un fichier
create_file() {
    local filepath="$1"
    local content="$2"
    echo "${content}" > "${PROJECT_DIR}/${filepath}"
}

echo "Generating files..."

# ============================================
# Fichiers racine
# ============================================

# README.md
create_file "README.md" '# Bojemoi Orchestrator

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.11+-yellow.svg)

Orchestrateur de déploiement unifié pour gérer l'\''infrastructure Bojemoi : VMs XenServer, containers Docker et services Docker Swarm.

## 🚀 Installation Rapide
```bash
# Cloner le repository
git clone https://github.com/bojemoi/orchestrator.git
cd orchestrator

# Installation
chmod +x scripts/*.sh
./scripts/install.sh
```

## 📚 Documentation

- [Guide de Contribution](CONTRIBUTING.md)
- [Code de Conduite](CODE_OF_CONDUCT.md)
- [Roadmap](ROADMAP.md)
- [Sécurité](SECURITY.md)

## 📄 License

MIT License - voir [LICENSE](LICENSE)
'

# LICENSE
create_file "LICENSE" 'MIT License

Copyright (c) 2024 Bojemoi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'

# .gitignore
create_file ".gitignore" '# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Logs
*.log
logs/*.log

# Environment
.env
.env.local

# Docker
*.pid

# Database
*.db
*.sqlite

# OS
.DS_Store
Thumbs.db

# Backups
backups/*.sql
backups/*.sql.gz

# Data
data/*
!data/.gitkeep
'

# .env.example
create_file ".env.example" '# Database
POSTGRES_PASSWORD=change_me_in_production

# Gitea
GITEA_URL=https://your-gitea-instance.com
GITEA_TOKEN=your_gitea_token_here
GITEA_REPO_OWNER=bojemoi
GITEA_REPO_NAME=infrastructure

# XenServer
XENSERVER_HOST=your-xenserver-host
XENSERVER_USER=root
XENSERVER_PASSWORD=your_xenserver_password

# Docker Swarm
DOCKER_SWARM_MANAGER=tcp://swarm-manager:2375

# Scheduler
CHECK_INTERVAL_MINUTES=5
ENABLE_SCHEDULER=true

# Monitoring
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin

# Misc
DEBUG=false
LOG_LEVEL=INFO
'

# requirements.txt
create_file "requirements.txt" '# FastAPI et dépendances
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
sqlalchemy==2.0.25
psycopg2-binary==2.9.9
alembic==1.13.1

# Docker
docker==7.0.0

# HTTP Client
httpx==0.26.0

# Scheduling
apscheduler==3.10.4
croniter==2.0.1

# Monitoring
prometheus-client==0.19.0

# Logging
python-json-logger==2.0.7

# CLI
click==8.1.7
rich==13.7.0

# Configuration
pyyaml==6.0.1
python-dotenv==1.0.0

# Validation
email-validator==2.1.0

# Utils
tenacity==8.2.3
'

# requirements-dev.txt
create_file "requirements-dev.txt" '# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
pytest-mock==3.12.0

# Linting
flake8==7.0.0
black==23.12.1
isort==5.13.2
mypy==1.8.0

# Security
bandit==1.7.6

# Pre-commit
pre-commit==3.6.0
'

# Dockerfile
create_file "Dockerfile" 'FROM python:3.11-slim

LABEL maintainer="bojemoi@example.com"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY orchestrator/ ./orchestrator/
COPY cli.py .

RUN mkdir -p /app/logs /app/data

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["python", "-m", "orchestrator.main"]
'

# docker-compose.yml
create_file "docker-compose.yml" 'version: "3.8"

services:
  orchestrator:
    build: .
    container_name: bojemoi-orchestrator
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - GITEA_URL=${GITEA_URL}
      - GITEA_TOKEN=${GITEA_TOKEN}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./logs:/app/logs
      - ./data:/app/data
    networks:
      - orchestrator-net
    depends_on:
      - postgres

  postgres:
    image: postgres:15-alpine
    container_name: orchestrator-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_DB=orchestrator
      - POSTGRES_USER=orchestrator
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - orchestrator-net
    ports:
      - "5432:5432"

  prometheus:
    image: prom/prometheus:latest
    container_name: orchestrator-prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    networks:
      - orchestrator-net
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    container_name: orchestrator-grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    networks:
      - orchestrator-net
    ports:
      - "3000:3000"

volumes:
  postgres-data:
  prometheus-data:
  grafana-data:

networks:
  orchestrator-net:
    driver: bridge
'

# Makefile
create_file "Makefile" '.PHONY: help install start stop restart logs backup health

help:
	@echo "Commands disponibles:"
	@echo "  make install    - Installation"
	@echo "  make start      - Démarrer"
	@echo "  make stop       - Arrêter"
	@echo "  make logs       - Voir les logs"
	@echo "  make health     - Health check"

install:
	@bash scripts/install.sh

start:
	@docker compose up -d

stop:
	@docker compose down

logs:
	@docker compose logs -f orchestrator

health:
	@bash scripts/health-check.sh
'

# prometheus.yml
create_file "prometheus.yml" 'global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "orchestrator"
    static_configs:
      - targets: ["orchestrator:8000"]
'

# CONTRIBUTING.md (version courte)
create_file "CONTRIBUTING.md" '# Guide de Contribution

Merci de contribuer à Bojemoi Orchestrator !

## Quick Start
```bash
git clone https://github.com/bojemoi/orchestrator.git
cd orchestrator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Conventions

- Suivre PEP 8
- Tests obligatoires
- Messages de commit: `type(scope): description`

## Process

1. Fork le projet
2. Créer une branche: `git checkout -b feature/ma-feature`
3. Commit: `git commit -m "feat: add feature"`
4. Push: `git push origin feature/ma-feature`
5. Créer une Pull Request

Pour plus de détails, voir la documentation complète.
'

# CODE_OF_CONDUCT.md (version courte)
create_file "CODE_OF_CONDUCT.md" '# Code de Conduite

## Notre Engagement

Nous nous engageons à faire de la participation à notre projet une expérience sans harcèlement pour tous.

## Standards

✅ Être respectueux
✅ Accepter les critiques constructives
❌ Harcèlement interdit
❌ Attaques personnelles interdites

## Application

Signaler à: conduct@bojemoi.com

Version complète: https://www.contributor-covenant.org/version/2/1/code_of_conduct/
'

# SECURITY.md (version courte)
create_file "SECURITY.md" '# Politique de Sécurité

## Signaler une Vulnérabilité

**Email**: security@bojemoi.com

## Informations à Inclure

- Type de vulnérabilité
- Étapes pour reproduire
- Impact potentiel

## Timeline

- Accusé de réception: 24h
- Évaluation: 72h
- Fix: Selon criticité

Merci de nous aider à garder Bojemoi sécurisé ! 🛡️
'

# ============================================
# Scripts
# ============================================

create_file "scripts/install.sh" '#!/bin/bash
set -e

echo "Installing Bojemoi Orchestrator..."

# Check dependencies
command -v docker >/dev/null 2>&1 || { echo "Docker required"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "Docker Compose required"; exit 1; }

# Create directories
mkdir -p logs data config

# Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Please edit .env with your configuration"
    exit 0
fi

# Build and start
docker compose build
docker compose up -d postgres
sleep 10
docker compose up -d

echo "Installation complete!"
echo "API: http://localhost:8000"
echo "Grafana: http://localhost:3000"
'

chmod +x "${PROJECT_DIR}/scripts/install.sh"

create_file "scripts/start.sh" '#!/bin/bash
echo "Starting Bojemoi Orchestrator..."
docker compose up -d
docker compose logs -f orchestrator
'

chmod +x "${PROJECT_DIR}/scripts/start.sh"

create_file "scripts/stop.sh" '#!/bin/bash
echo "Stopping Bojemoi Orchestrator..."
docker compose down
'

chmod +x "${PROJECT_DIR}/scripts/stop.sh"

# ============================================
# Orchestrator (code Python principal)
# ============================================

create_file "orchestrator/__init__.py" '"""Bojemoi Orchestrator - Infrastructure deployment orchestrator."""

__version__ = "1.0.0"
'

create_file "orchestrator/main.py" '"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from .config import settings

app = FastAPI(
    title="Bojemoi Orchestrator",
    version="1.0.0",
    description="Infrastructure deployment orchestrator"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/")
async def root():
    return {"message": "Bojemoi Orchestrator API", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'

create_file "orchestrator/config.py" '"""Configuration management."""

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Bojemoi Orchestrator"
    DEBUG: bool = False
    
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "orchestrator"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "orchestrator"
    
    class Config:
        env_file = ".env"

settings = Settings()
'

# ============================================
# Examples
# ============================================

create_file "examples/vms/web-server-01.yaml" 'name: web-server-01
template: "Ubuntu 22.04"
vcpus: 4
memory_gb: 8
disk_gb: 100
cloud_init: base-ubuntu
network:
  network_name: "Production"
  ip_address: "192.168.1.100"
tags:
  environment: production
  role: web-server
'

create_file "examples/containers/nginx-proxy.yaml" 'name: nginx-proxy
image: nginx:alpine
ports:
  80/tcp: 80
  443/tcp: 443
networks:
  - frontend
restart_policy: unless-stopped
'

create_file "examples/services/api-service.yaml" 'name: api-service
image: myregistry.local/api:v1.0.0
mode: replicated
replicas: 3
ports:
  8080: 8080
networks:
  - backend
'

# ============================================
# CLI
# ============================================

create_file "cli.py" '#!/usr/bin/env python3
"""CLI for Bojemoi Orchestrator."""

import click

@click.group()
def cli():
    """Bojemoi Orchestrator CLI."""
    pass

@cli.command()
def status():
    """Check orchestrator status."""
    click.echo("Orchestrator status: OK")

if __name__ == "__main__":
    cli()
'

chmod +x "${PROJECT_DIR}/cli.py"

# ============================================
# Tests
# ============================================

create_file "tests/__init__.py" ''

create_file "tests/conftest.py" 'import pytest

@pytest.fixture
def test_config():
    return {"test": True}
'

create_file "tests/test_basic.py" 'def test_basic():
    assert True
'

# ============================================
# Documentation
# ============================================

create_file "docs/README.md" '# Documentation

## Installation

Voir le [README.md](../README.md) principal.

## Architecture

À documenter...

## API

Voir http://localhost:8000/docs
'

# ============================================
# .gitkeep files
# ============================================

touch "${PROJECT_DIR}/logs/.gitkeep"
touch "${PROJECT_DIR}/data/.gitkeep"

# ============================================
# Compression
# ============================================

echo ""
echo "Creating tar.gz archive..."
cd "${TEMP_DIR}"
tar -czf "${OUTPUT_FILE}" "${PROJECT_NAME}"

# Déplacer dans le répertoire courant
mv "${OUTPUT_FILE}" "${OLDPWD}/"
cd "${OLDPWD}"

# Nettoyer
rm -rf "${TEMP_DIR}"

echo ""
echo "======================================"
echo "✅ Project generated successfully!"
echo "======================================"
echo ""
echo "Archive: ${OUTPUT_FILE}"
echo "Size: $(du -h "${OUTPUT_FILE}" | cut -f1)"
echo ""
echo "To extract:"
echo "  tar -xzf ${OUTPUT_FILE}"
echo "  cd ${PROJECT_NAME}"
echo "  ./scripts/install.sh"
echo ""

