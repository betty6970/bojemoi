.PHONY: help build up down restart logs shell test clean

help:
	@echo "Bojemoi Orchestrator - Available commands:"
	@echo "  make build      - Build Docker images"
	@echo "  make up         - Start services"
	@echo "  make down       - Stop services"
	@echo "  make restart    - Restart services"
	@echo "  make logs       - View logs"
	@echo "  make shell      - Open shell in orchestrator container"
	@echo "  make test       - Run test deployment script"
	@echo "  make clean      - Clean up containers and volumes"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

shell:
	docker-compose exec orchestrator /bin/bash

test:
	./scripts/test_deploy.sh

clean:
	docker-compose down -v
	docker system prune -f
