.PHONY: help build up down restart logs shell db-shell test clean

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build l'image Docker
	docker-compose build

up: ## Démarre les services
	docker-compose up -d
	@echo "✅ Services démarrés"
	@echo "📍 API: http://localhost:8080"
	@echo "📊 Metrics: http://localhost:9090/metrics"
	@echo "💚 Health: http://localhost:8080/health"

down: ## Arrête les services
	docker-compose down

restart: down up ## Redémarre les services

logs: ## Affiche les logs
	docker-compose logs -f orchestrator

shell: ## Ouvre un shell dans le container
	docker-compose exec orchestrator bash

db-shell: ## Ouvre un shell PostgreSQL
	docker-compose exec postgres psql -U deployment_user -d deployments

test-webhook: ## Teste le webhook (nécessite jq)
	@curl -X POST http://localhost:8080/webhook/gitea \
		-H "Content-Type: application/json" \
		-d '{"ref":"refs/heads/main","repository":{"name":"test-repo","owner":{"username":"betty"}},"commits":[{"id":"abc123","message":"test"}]}'

health: ## Vérifie le health check
	@curl -s http://localhost:8080/health | jq

deployments: ## Liste les déploiements récents
	@curl -s http://localhost:8080/deployments | jq

metrics: ## Affiche les métriques
	@curl -s http://localhost:9090/metrics

clean: ## Nettoie les volumes et containers
	docker-compose down -v
	rm -rf logs/* cache/*

init-db: ## Initialise la base de données
	docker-compose exec postgres psql -U deployment_user -d deployments -c "\dt"

backup-db: ## Backup de la base de données
	docker-compose exec postgres pg_dump -U deployment_user deployments > backup_$(shell date +%Y%m%d_%H%M%S).sql

status: ## Affiche le statut des services
	@docker-compose ps

dev: ## Mode développement avec rechargement automatique
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
