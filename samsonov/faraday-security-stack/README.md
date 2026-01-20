# Faraday Security Stack

Stack complète de sécurité avec Faraday, ZAP, Metasploit, Masscan et Burp Suite en mode Docker.

## 📋 Table des matières

- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Intégrations](#intégrations)
- [Scripts disponibles](#scripts-disponibles)
- [Commandes Make](#commandes-make)
- [Workflows](#workflows)
- [Troubleshooting](#troubleshooting)
- [Sécurité](#sécurité)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Nginx (Port 80)                       │
│                    Reverse Proxy / Load Balancer             │
└─────────────────┬───────────────────────────────┬───────────┘
                  │                               │
          ┌───────▼────────┐             ┌───────▼────────┐
          │  Faraday       │             │  OWASP ZAP     │
          │  (Port 5985)   │             │  (Port 8080)   │
          └───────┬────────┘             └────────────────┘
                  │
          ┌───────▼────────┐
          │  PostgreSQL    │
          │  Database      │
          └────────────────┘

┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  Metasploit    │  │  Masscan       │  │  Burp Suite    │
│  Framework     │  │  (Network)     │  │  (Port 8081)   │
└────────────────┘  └────────────────┘  └────────────────┘
```

## 📦 Composants

- **Faraday** : Plateforme de gestion de vulnérabilités
- **PostgreSQL** : Base de données pour Faraday
- **OWASP ZAP** : Scanner de sécurité pour applications web
- **Metasploit Framework** : Framework de tests de pénétration
- **Masscan** : Scanner de ports ultra-rapide
- **Burp Suite** : Proxy d'interception pour applications web
- **Nginx** : Reverse proxy pour centraliser l'accès

## 🔧 Prérequis

- Docker Engine 20.10+
- Docker Compose 2.0+
- 8 GB RAM minimum
- 20 GB d'espace disque
- Linux (recommandé) ou macOS

## 📥 Installation

### Installation rapide

```bash
# Cloner le projet
git clone <repository-url>
cd faraday-security-stack

# Démarrer tous les services
make up

# Vérifier le statut
make status
```

### Installation manuelle

```bash
# Construire les images
docker-compose build

# Démarrer les services
docker-compose up -d

# Vérifier les logs
docker-compose logs -f
```

## ⚙️ Configuration

### Variables d'environnement

Modifiez le fichier `.env` pour personnaliser la configuration :

```bash
# Configuration Faraday
FARADAY_DATABASE_HOST=postgres
FARADAY_DATABASE_NAME=faraday
FARADAY_DATABASE_USER=faraday
FARADAY_DATABASE_PASSWORD=changeme123

# Credentials Faraday (CHANGEZ EN PRODUCTION!)
FARADAY_DEFAULT_USER=faraday
FARADAY_DEFAULT_PASSWORD=changeme

# Workspace par défaut
DEFAULT_WORKSPACE=security-scan
```

### Configuration Faraday

1. Accédez à http://localhost:5985
2. Connectez-vous avec les credentials par défaut
3. Créez un nouveau workspace ou utilisez le workspace par défaut

### Configuration ZAP

```bash
# Accéder au conteneur ZAP
docker exec -it faraday-zap bash

# Générer une clé API ZAP
zap-cli --zap-url http://localhost:8080 status
```

## 🚀 Utilisation

### Commandes Make disponibles

```bash
# Aide
make help

# Gestion des services
make up                # Démarrer tous les services
make down              # Arrêter tous les services
make restart           # Redémarrer tous les services
make status            # Afficher le statut

# Logs
make logs              # Logs de tous les services
make logs-faraday      # Logs Faraday uniquement
make logs-zap          # Logs ZAP uniquement

# Shells interactifs
make shell-faraday     # Shell Faraday
make shell-zap         # Shell ZAP
make shell-metasploit  # Console Metasploit
make shell-masscan     # Shell Masscan

# Scans
make scan TARGET=192.168.1.0/24 WORKSPACE=my-scan    # Scan complet
make scan-masscan TARGET=192.168.1.0/24              # Masscan uniquement
make scan-zap TARGET=http://example.com              # ZAP uniquement
make scan-metasploit TARGET=192.168.1.1              # Metasploit uniquement

# Maintenance
make backup            # Sauvegarder la base de données
make restore BACKUP_FILE=backups/file.sql  # Restaurer
make clean             # Nettoyer (avec confirmation)
make update            # Mettre à jour les images
```

### Scans automatisés

#### Scan complet d'un réseau

```bash
make scan TARGET=192.168.1.0/24 WORKSPACE=network-scan
```

#### Scan web avec ZAP

```bash
make scan-zap TARGET=http://example.com WORKSPACE=web-scan
```

#### Scan de ports avec Masscan

```bash
make scan-masscan TARGET=10.0.0.0/24 WORKSPACE=port-scan
```

## 🔗 Intégrations

### Script ZAP → Faraday

```bash
docker exec faraday-server python3 /scripts/zap_to_faraday.py \
  --faraday-url http://faraday:5985 \
  --faraday-user faraday \
  --faraday-pass changeme \
  --zap-url http://zap:8080 \
  --workspace my-scan \
  --target-url http://example.com
```

### Script Metasploit → Faraday

```bash
docker exec faraday-server python3 /scripts/msf_to_faraday.py \
  --faraday-url http://faraday:5985 \
  --faraday-user faraday \
  --faraday-pass changeme \
  --msf-xml /path/to/metasploit_results.xml \
  --workspace my-scan
```

### Script Masscan → Faraday

```bash
docker exec faraday-server python3 /scripts/masscan_to_faraday.py \
  --faraday-url http://faraday:5985 \
  --faraday-user faraday \
  --faraday-pass changeme \
  --masscan-json /results/masscan_output.json \
  --workspace my-scan
```

### Script d'orchestration

```bash
docker exec faraday-masscan /scripts/orchestrator.sh \
  --target 192.168.1.0/24 \
  --workspace full-scan \
  --all
```

## 📜 Scripts disponibles

| Script | Description |
|--------|-------------|
| `orchestrator.sh` | Orchestration de tous les outils |
| `zap_to_faraday.py` | Import ZAP → Faraday |
| `msf_to_faraday.py` | Import Metasploit → Faraday |
| `masscan_to_faraday.py` | Import Masscan → Faraday |

## 🔄 Workflows

### Workflow de reconnaissance

```bash
# 1. Scan de ports avec Masscan
make scan-masscan TARGET=192.168.1.0/24 WORKSPACE=recon

# 2. Énumération avec Metasploit
make scan-metasploit TARGET=192.168.1.1 WORKSPACE=recon

# 3. Scan web avec ZAP
make scan-zap TARGET=http://192.168.1.1 WORKSPACE=recon
```

### Workflow d'audit web complet

```bash
# 1. Lancer ZAP en mode passif
make shell-zap
# Dans le shell ZAP
zap-cli --zap-url http://localhost:8080 open-url http://example.com

# 2. Configurer Burp pour l'analyse manuelle
# Accéder à http://localhost:8081

# 3. Importer les résultats dans Faraday
docker exec faraday-server python3 /scripts/zap_to_faraday.py \
  --target-url http://example.com \
  --workspace web-audit
```

## 🔐 URLs d'accès

- **Faraday** : http://localhost:5985
- **ZAP** : http://localhost:8080
- **Burp Suite** : http://localhost:8081
- **Nginx** : http://localhost

## 🛠️ Troubleshooting

### Faraday ne démarre pas

```bash
# Vérifier les logs
make logs-faraday

# Vérifier la base de données
docker exec -it faraday-postgres psql -U faraday -d faraday

# Recréer la base de données
docker-compose down -v
docker-compose up -d
```

### ZAP ne répond pas

```bash
# Redémarrer ZAP
docker restart faraday-zap

# Vérifier l'API
curl http://localhost:8080/JSON/core/view/version/
```

### Problèmes de permissions

```bash
# Corriger les permissions des scripts
chmod +x scripts/*.sh
chmod +x scripts/*.py
```

### Erreurs réseau pour Masscan

```bash
# Masscan nécessite les privilèges réseau
# Vérifier la configuration network_mode: host
docker-compose down
docker-compose up -d masscan
```

## 🔒 Sécurité

### Recommendations de production

1. **Changez tous les mots de passe par défaut**
   ```bash
   # Éditez .env
   FARADAY_DEFAULT_PASSWORD=VotreMotDePasseSecurise
   POSTGRES_PASSWORD=MotDePassePostgresSecurise
   ```

2. **Utilisez HTTPS**
   ```bash
   # Configurez des certificats SSL dans nginx
   # Ajoutez les certificats dans configs/nginx/certs/
   ```

3. **Limitez l'accès réseau**
   ```bash
   # Configurez un firewall
   # Limitez les ports exposés dans docker-compose.yml
   ```

4. **Sauvegardes régulières**
   ```bash
   # Créez un cron pour les sauvegardes
   0 2 * * * cd /path/to/stack && make backup
   ```

5. **Mettez à jour régulièrement**
   ```bash
   make update
   ```

## 📊 Sauvegarde et restauration

### Sauvegarde

```bash
# Sauvegarde complète
make backup

# Sauvegarde manuelle
docker exec faraday-postgres pg_dump -U faraday faraday > backup.sql
```

### Restauration

```bash
# Restauration
make restore BACKUP_FILE=backups/faraday_backup_20231201.sql

# Restauration manuelle
docker exec -i faraday-postgres psql -U faraday faraday < backup.sql
```

## 📝 Licence

Ce projet est fourni à des fins éducatives et de test de sécurité uniquement.

## ⚠️ Avertissement

**IMPORTANT** : Ces outils sont destinés uniquement à des fins légitimes de test de sécurité sur des systèmes dont vous avez l'autorisation. L'utilisation non autorisée de ces outils peut être illégale.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## 📧 Support

Pour toute question ou problème :
- Consultez la documentation de chaque outil
- Vérifiez les logs avec `make logs`
- Ouvrez une issue sur le repository

## 📚 Ressources

- [Documentation Faraday](https://docs.faradaysec.com/)
- [Documentation ZAP](https://www.zaproxy.org/docs/)
- [Documentation Metasploit](https://docs.metasploit.com/)
- [Documentation Masscan](https://github.com/robertdavidgraham/masscan)
- [Documentation Burp Suite](https://portswigger.net/burp/documentation)
