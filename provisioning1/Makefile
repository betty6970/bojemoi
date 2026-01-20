.PHONY: help install start stop logs health

help:
	@echo "Bojemoi Orchestrator - Commands"
	@echo ""
	@echo "  make install  - Install orchestrator"
	@echo "  make start    - Start services"
	@echo "  make stop     - Stop services"
	@echo "  make logs     - View logs"
	@echo "  make health   - Health check"

install:
	@bash scripts/install.sh

start:
	@bash scripts/start.sh

stop:
	@bash scripts/stop.sh

logs:
	@docker compose logs -f orchestrator

health:
	@bash scripts/health-check.sh

