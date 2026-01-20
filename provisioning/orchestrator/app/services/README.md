# Services - XenServer Client Options

Ce répertoire contient deux implémentations du client XenServer :

## 📁 Fichiers disponibles

### 1. `xenserver_client.py` (STUB - Par défaut)
**⚠️ Ce fichier ne crée PAS réellement de VMs !**

C'est un **stub** (simulacre) qui :
- Simule les appels API
- Retourne des données fictives
- Utile pour le développement sans infrastructure XenServer

### 2. `xenserver_client_real.py` (PRODUCTION - Recommandé)
**✅ Implémentation complète avec XenAPI**

Cette version :
- ✅ Crée vraiment des VMs sur XenServer
- ✅ Utilise l'API officielle XenAPI
- ✅ Gère : clone, CPU, RAM, disque, réseau, cloud-init
- ✅ Démarre automatiquement les VMs

## 🔄 Comment basculer vers la vraie implémentation

### Option 1 : Renommer les fichiers (Recommandé)

```bash
cd app/services/

# Sauvegarder le stub
mv xenserver_client.py xenserver_client_stub.py

# Activer l'implémentation réelle
mv xenserver_client_real.py xenserver_client.py
```

### Option 2 : Remplacer le contenu

Copiez simplement le contenu de `xenserver_client_real.py` dans `xenserver_client.py`.

## 📦 Dépendances requises

Pour utiliser `xenserver_client_real.py`, ajoutez dans `requirements.txt` :

```
XenAPI==1.0
```

Puis reconstruisez le container :
```bash
docker-compose build
docker-compose up -d
```

## ⚙️ Configuration

Assurez-vous que `.env` contient :

```bash
XENSERVER_URL=https://votre-xenserver.local
XENSERVER_USER=root
XENSERVER_PASS=votre_mot_de_passe
```

## 🧪 Tester la connexion

```bash
# Health check (vérifie aussi XenServer)
curl http://localhost:8000/health

# Devrait retourner :
# {
#   "services": {
#     "xenserver": "up",  # ✅ Si connexion OK
#     ...
#   }
# }
```

## 📚 Documentation complète

Voir `docs/XENSERVER_IMPLEMENTATION_GUIDE.md` pour :
- Guide détaillé d'implémentation
- Explications du code
- Personnalisation selon votre environnement
- Gestion des erreurs
- Exemples avancés

## 🎯 Tableau de comparaison

| Fichier | Usage | Crée vraiment des VMs ? | Nécessite XenServer ? |
|---------|-------|-------------------------|----------------------|
| `xenserver_client.py` (stub) | Développement | ❌ Non | ❌ Non |
| `xenserver_client_real.py` | Production | ✅ Oui | ✅ Oui |

## ⚠️ Important

Si vous utilisez l'orchestrator en production, vous **DEVEZ** utiliser `xenserver_client_real.py`, sinon :
- Les API répondront "succès"
- Mais aucune VM ne sera créée
- Les utilisateurs penseront que ça fonctionne alors que non !

## 🆘 Aide

Pour toute question sur l'implémentation XenServer :
1. Consultez `docs/XENSERVER_IMPLEMENTATION_GUIDE.md`
2. Vérifiez les logs : `docker-compose logs -f orchestrator`
3. Testez la connexion manuellement : `curl http://localhost:8000/health`
