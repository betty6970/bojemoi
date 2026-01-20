# 🚀 Guide de démarrage rapide

Démarrez avec Faraday Security Stack en quelques minutes !

## ⚡ Installation express (5 minutes)

```bash
# 1. Télécharger le projet
git clone <repository-url>
cd faraday-security-stack

# 2. Lancer l'installation automatique
chmod +x install.sh
./install.sh

# 3. C'est fait ! Accédez à Faraday
open http://localhost:5985
```

**Credentials par défaut:**
- Utilisateur: `faraday`
- Mot de passe: `changeme`

## 📝 Premier scan en 3 étapes

### Scan réseau complet

```bash
make scan TARGET=192.168.1.0/24 WORKSPACE=mon-premier-scan
```

### Scan web uniquement

```bash
make scan-zap TARGET=http://example.com WORKSPACE=web-test
```

### Scan de ports rapide

```bash
make scan-masscan TARGET=10.0.0.0/24 WORKSPACE=ports
```

## 🎯 Commandes essentielles

```bash
# Démarrer tout
make up

# Voir le statut
make status

# Voir les logs
make logs

# Arrêter tout
make down

# Aide complète
make help
```

## 📊 Accès aux interfaces

| Service | URL | Port |
|---------|-----|------|
| **Faraday** | http://localhost:5985 | 5985 |
| **ZAP** | http://localhost:8080 | 8080 |
| **Burp** | http://localhost:8081 | 8081 |
| **Nginx** | http://localhost | 80 |

## 🔧 Résolution rapide des problèmes

### Un service ne démarre pas ?

```bash
# Voir les logs du service
make logs-faraday
make logs-zap

# Redémarrer tout
make restart
```

### Base de données corrompue ?

```bash
# Recréer complètement
make clean
make up
```

### Besoin d'aide ?

```bash
# Lancer les tests
./test.sh

# Voir les exemples
./examples.sh

# Consulter la doc complète
cat README.md
```

## ⚙️ Configuration rapide

### Changer les mots de passe

Éditez le fichier `.env`:

```bash
nano .env
# Changez:
# FARADAY_DEFAULT_PASSWORD=votre_mot_de_passe_securise
# POSTGRES_PASSWORD=autre_mot_de_passe_securise
```

### Ajouter une cible permanente

```bash
# Ouvrir Faraday
open http://localhost:5985

# Créer un workspace
# Ajouter vos cibles
# Lancer les scans
```

## 🎓 Exemples d'utilisation

### Workflow complet de pentest

```bash
# 1. Reconnaissance réseau
make scan-masscan TARGET=192.168.1.0/24 WORKSPACE=pentest

# 2. Énumération services
make scan-metasploit TARGET=192.168.1.10 WORKSPACE=pentest

# 3. Scan web
make scan-zap TARGET=http://192.168.1.10 WORKSPACE=pentest

# 4. Consulter les résultats
open http://localhost:5985
```

### Scan automatisé récurrent

```bash
# Créer un cron pour scanner chaque nuit
crontab -e

# Ajouter:
0 2 * * * cd /path/to/stack && make scan TARGET=192.168.1.0/24
```

## 🔐 Sécurité - Points importants

⚠️ **ATTENTION:**
- Changez TOUS les mots de passe par défaut
- N'exposez PAS les ports sur Internet
- Utilisez uniquement sur des systèmes autorisés
- Sauvegardez régulièrement: `make backup`

## 📚 Ressources

- **Documentation complète:** README.md
- **Exemples détaillés:** ./examples.sh
- **Tests:** ./test.sh
- **Contribution:** CONTRIBUTING.md

## 🆘 Support

Problème ? Consultez:
1. Les logs: `make logs`
2. Le statut: `make status`
3. Les tests: `./test.sh`
4. La documentation: README.md

---

**Bon scan ! 🎯**

N'oubliez pas: utilisez ces outils de manière éthique et légale uniquement !
