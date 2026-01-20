.PHONY: help build up down restart logs clean scan status

# Variables
COMPOSE_FILE=docker-compose.yml
PROJECT_NAME=faraday-stack

# Couleurs pour l'affichage
BLUE=\033[0;34m
GREEN=\033[0;32m
RED=\033[0;31m
NC=\033[0m # No Color

help: ## Afficher cette aide
	@echo "$(BLUE)Faraday Security Stack - Commandes disponibles:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

build: ## Construire les images Docker
	@echo "$(BLUE)Construction des images Docker...$(NC)"
	docker-compose -f $(COMPOSE_FILE) build

up: ## Démarrer tous les services
	@echo "$(BLUE)Démarrage des services...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)Services démarrés avec succès!$(NC)"
	@echo ""
	@$(MAKE) status

down: ## Arrêter tous les services
	@echo "$(BLUE)Arrêt des services...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down
	@echo "$(GREEN)Services arrêtés$(NC)"

restart: ## Redémarrer tous les services
	@echo "$(BLUE)Redémarrage des services...$(NC)"
	@$(MAKE) down
	@$(MAKE) up

logs: ## Afficher les logs de tous les services
	docker-compose -f $(COMPOSE_FILE) logs -f

logs-faraday: ## Afficher les logs de Faraday
	docker-compose -f $(COMPOSE_FILE) logs -f faraday

logs-zap: ## Afficher les logs de ZAP
	docker-compose -f $(COMPOSE_FILE) logs -f zap

logs-metasploit: ## Afficher les logs de Metasploit
	docker-compose -f $(COMPOSE_FILE) logs -f metasploit

status: ## Afficher le statut des services
	@echo "$(BLUE)Statut des services:$(NC)"
	@docker-compose -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "$(BLUE)URLs d'accès:$(NC)"
	@echo "  - Faraday:     http://localhost:5985"
	@echo "  - ZAP:         http://localhost:8080"
	@echo "  - Burp:        http://localhost:8081"
	@echo "  - Nginx:       http://localhost"
	@echo ""

shell-faraday: ## Ouvrir un shell dans le conteneur Faraday
	docker exec -it faraday-server /bin/bash

shell-zap: ## Ouvrir un shell dans le conteneur ZAP
	docker exec -it faraday-zap /bin/bash

shell-metasploit: ## Ouvrir un shell Metasploit
	docker exec -it faraday-metasploit msfconsole

shell-masscan: ## Ouvrir un shell dans le conteneur Masscan
	docker exec -it faraday-masscan /bin/sh

scan: ## Lancer un scan complet (nécessite TARGET)
	@if [ -z "$(TARGET)" ]; then \
		echo "$(RED)Erreur: TARGET non défini$(NC)"; \
		echo "Usage: make scan TARGET=192.168.1.0/24"; \
		exit 1; \
	fi
	@echo "$(BLUE)Lancement du scan sur $(TARGET)...$(NC)"
	docker exec faraday-masscan /scripts/orchestrator.sh --target $(TARGET) --all --workspace $(WORKSPACE)

scan-masscan: ## Lancer uniquement Masscan
	@if [ -z "$(TARGET)" ]; then \
		echo "$(RED)Erreur: TARGET non défini$(NC)"; \
		echo "Usage: make scan-masscan TARGET=192.168.1.0/24"; \
		exit 1; \
	fi
	@echo "$(BLUE)Lancement de Masscan sur $(TARGET)...$(NC)"
	docker exec faraday-masscan /scripts/orchestrator.sh --target $(TARGET) --masscan --workspace $(WORKSPACE)

scan-zap: ## Lancer uniquement ZAP
	@if [ -z "$(TARGET)" ]; then \
		echo "$(RED)Erreur: TARGET non défini$(NC)"; \
		echo "Usage: make scan-zap TARGET=http://example.com"; \
		exit 1; \
	fi
	@echo "$(BLUE)Lancement de ZAP sur $(TARGET)...$(NC)"
	docker exec faraday-server /scripts/orchestrator.sh --target $(TARGET) --zap --workspace $(WORKSPACE)

scan-metasploit: ## Lancer uniquement Metasploit
	@if [ -z "$(TARGET)" ]; then \
		echo "$(RED)Erreur: TARGET non défini$(NC)"; \
		echo "Usage: make scan-metasploit TARGET=192.168.1.1"; \
		exit 1; \
	fi
	@echo "$(BLUE)Lancement de Metasploit sur $(TARGET)...$(NC)"
	docker exec faraday-metasploit /scripts/orchestrator.sh --target $(TARGET) --metasploit --workspace $(WORKSPACE)

clean: ## Nettoyer les conteneurs et volumes
	@echo "$(RED)Attention: Cette commande supprime tous les conteneurs et volumes!$(NC)"
	@read -p "Êtes-vous sûr? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose -f $(COMPOSE_FILE) down -v; \
		echo "$(GREEN)Nettoyage effectué$(NC)"; \
	fi

backup: ## Créer une sauvegarde de la base de données
	@echo "$(BLUE)Création d'une sauvegarde...$(NC)"
	@mkdir -p backups
	docker exec faraday-postgres pg_dump -U faraday faraday > backups/faraday_backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)Sauvegarde créée dans backups/$(NC)"

restore: ## Restaurer une sauvegarde (nécessite BACKUP_FILE)
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "$(RED)Erreur: BACKUP_FILE non défini$(NC)"; \
		echo "Usage: make restore BACKUP_FILE=backups/faraday_backup_20231201_120000.sql"; \
		exit 1; \
	fi
	@echo "$(BLUE)Restauration de $(BACKUP_FILE)...$(NC)"
	docker exec -i faraday-postgres psql -U faraday faraday < $(BACKUP_FILE)
	@echo "$(GREEN)Restauration terminée$(NC)"

update: ## Mettre à jour les images Docker
	@echo "$(BLUE)Mise à jour des images...$(NC)"
	docker-compose -f $(COMPOSE_FILE) pull
	@$(MAKE) restart
	@echo "$(GREEN)Mise à jour terminée$(NC)"

prune: ## Nettoyer les ressources Docker inutilisées
	@echo "$(BLUE)Nettoyage des ressources Docker...$(NC)"
	docker system prune -af --volumes
	@echo "$(GREEN)Nettoyage terminé$(NC)"

test: ## Tester la connectivité des services
	@echo "$(BLUE)Test de connectivité...$(NC)"
	@echo -n "Faraday:     "
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:5985 && echo " $(GREEN)OK$(NC)" || echo " $(RED)FAIL$(NC)"
	@echo -n "ZAP:         "
	@curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 && echo " $(GREEN)OK$(NC)" || echo " $(RED)FAIL$(NC)"
	@echo -n "Nginx:       "
	@curl -s -o /dev/null -w "%{http_code}" http://localhost/status && echo " $(GREEN)OK$(NC)" || echo " $(RED)FAIL$(NC)"
