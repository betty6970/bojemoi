.PHONY: help build push deploy status logs clean secrets validate

REGISTRY ?= localhost:5000
STACK_DIR  = stack
BUILD_SCRIPT = scripts/build_all.sh

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ─── Build ─────────────────────────────────────────────────────────────────

build: ## Build all custom Docker images
	@echo "[build] Building images..."
	bash scripts/cccp.sh

push: ## Push all images to local registry
	@echo "[push] Pushing to $(REGISTRY)..."
	bash scripts/cccp.sh --push-only

build-push: ## Build then push (shortcut)
	bash scripts/cccp.sh --push

# ─── Deploy ────────────────────────────────────────────────────────────────

deploy: ## Full interactive deploy (runs install.sh)
	bash install.sh

deploy-base: ## Deploy base stack only (monitoring + DB)
	@test -f .env && . ./.env || true
	docker stack deploy -c $(STACK_DIR)/01-service-hl.yml base \
	  --prune --resolve-image always

deploy-borodino: ## Deploy scanning stack
	docker stack deploy -c $(STACK_DIR)/40-service-borodino.yml borodino \
	  --prune --resolve-image always

deploy-dojo: ## Deploy DefectDojo
	docker stack deploy -c $(STACK_DIR)/70-service-defectdojo.yml dojo \
	  --prune --resolve-image always

deploy-all-workers: ## Deploy all worker stacks
	for f in $(STACK_DIR)/4*.yml $(STACK_DIR)/5*.yml $(STACK_DIR)/6*.yml $(STACK_DIR)/7*.yml; do \
	  name=$$(basename $$f | sed 's/^[0-9]*-service-//' | sed 's/\.yml//'); \
	  echo "[deploy] $$name"; \
	  docker stack deploy -c $$f $$name --prune --resolve-image always; \
	done

# ─── Status ────────────────────────────────────────────────────────────────

status: ## Show all stack and service status
	@echo "\n=== Stacks ==="
	@docker stack ls
	@echo "\n=== Services ==="
	@docker service ls

ps: ## Show running tasks (no-trunc)
	@docker stack ps $$(docker stack ls --format '{{.Name}}' | tr '\n' ' ') \
	  --filter "desired-state=running" 2>/dev/null || docker service ls

# ─── Logs ──────────────────────────────────────────────────────────────────

logs-base: ## Tail grafana logs
	docker service logs -f base_grafana

logs-borodino: ## Tail ak47 scanner logs
	docker service logs -f borodino_ak47-service

logs-dojo: ## Tail DefectDojo logs
	docker service logs -f dojo_defectdojo 2>/dev/null || \
	  docker service logs -f $$(docker service ls --format '{{.Name}}' | grep dojo | head -1)

# ─── Secrets ───────────────────────────────────────────────────────────────

secrets: ## Create Docker secrets interactively
	bash scripts/create-secrets.sh

secrets-list: ## List existing Docker secrets
	docker secret ls

# ─── Validate ──────────────────────────────────────────────────────────────

validate: ## Validate all stack YAML files
	@ok=0; fail=0; \
	for f in $(STACK_DIR)/*.yml; do \
	  if docker-compose -f $$f config --quiet 2>/dev/null; then \
	    echo "  ✓ $$f"; ok=$$((ok+1)); \
	  else \
	    echo "  ✗ $$f  ← ERROR"; fail=$$((fail+1)); \
	  fi; \
	done; \
	echo "\n$$ok OK, $$fail failed"

# ─── Clean ─────────────────────────────────────────────────────────────────

clean-images: ## Remove dangling Docker images
	docker image prune -f

clean-registry: ## Clean old images from local registry
	bash scripts/cleaning_registry.sh

nodes: ## Show Swarm node status and IPs
	@docker node ls
	@echo ""
	@for n in meta-68 meta-69 meta-70 meta-76; do \
	  ip=$$(docker node inspect $$n --format '{{.Status.Addr}}' 2>/dev/null); \
	  echo "  $$n → $$ip"; \
	done
