# Guide d'implémentation du Client XenServer

## 🔴 Problème : Le Stub (Code simulé)

Le fichier `app/services/xenserver_client.py` dans l'archive contient un **stub** - un code qui simule les fonctionnalités sans réellement les exécuter.

### Qu'est-ce qu'un stub ?

Un **stub** est un code placeholder qui :
- ✅ A la bonne signature de fonction
- ✅ Retourne le bon type de données
- ❌ Ne fait PAS réellement le travail
- ❌ Retourne des données fictives

### Exemple du stub actuel

```python
async def create_vm(self, name, template, cpu, memory, ...):
    logger.info(f"Creating VM: {name}")
    
    # TODO: Implement actual VM creation using XenAPI
    # ❌ Pas de vraie création de VM !
    
    # ❌ Retourne un faux identifiant
    return f"vm-{name}-ref"
```

**Résultat** : Quand vous appelez l'API pour créer une VM, elle répond "succès" mais **aucune VM n'est créée** sur XenServer !

## ✅ Solutions pour corriger le problème

### Option 1 : Utiliser XenAPI (Recommandé) ⭐

XenAPI est l'API officielle de XenServer/XCP-ng basée sur XML-RPC.

#### Installation

```bash
pip install XenAPI
```

Ou ajoutez dans `requirements.txt` :
```
XenAPI==1.0
```

#### Implémentation complète

J'ai créé `xenserver_client_real.py` qui contient une implémentation complète avec :

1. **Connexion authentifiée** à XenServer
2. **Création de VM** :
   - Clone d'un template
   - Configuration CPU/RAM
   - Redimensionnement du disque
   - Configuration réseau
   - Injection cloud-init
   - Provisioning et démarrage
3. **Suppression de VM** :
   - Arrêt gracieux
   - Destruction des disques (VDI)
   - Destruction de la VM
4. **Récupération d'infos** sur les VMs

#### Fonctionnalités réelles

```python
# Clone un template existant
vm_ref = self.session.xenapi.VM.clone(template_ref, name)

# Configure les CPUs
self.session.xenapi.VM.set_VCPUs_max(vm_ref, str(cpu))

# Configure la mémoire
memory_bytes = str(memory * 1024 * 1024)
self.session.xenapi.VM.set_memory_limits(vm_ref, ...)

# Redimensionne le disque
disk_bytes = disk * 1024 * 1024 * 1024
self.session.xenapi.VDI.resize(vdi_ref, str(disk_bytes))

# Démarre la VM
self.session.xenapi.VM.start(vm_ref, False, False)
```

### Option 2 : Utiliser xe CLI via SSH

Alternative si vous préférez utiliser la ligne de commande.

#### Installation

```bash
pip install paramiko  # Pour SSH
```

#### Exemple d'implémentation

```python
import paramiko

class XenServerCLIClient:
    def __init__(self, host, username, password):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(host, username=username, password=password)
    
    def create_vm(self, name, template, cpu, memory):
        # Clone template
        stdin, stdout, stderr = self.ssh.exec_command(
            f"xe vm-install template={template} new-name-label={name}"
        )
        vm_uuid = stdout.read().decode().strip()
        
        # Set CPUs
        self.ssh.exec_command(f"xe vm-param-set uuid={vm_uuid} VCPUs-max={cpu}")
        
        # Set memory
        memory_bytes = memory * 1024 * 1024
        self.ssh.exec_command(f"xe vm-param-set uuid={vm_uuid} memory-static-max={memory_bytes}")
        
        # Start VM
        self.ssh.exec_command(f"xe vm-start uuid={vm_uuid}")
        
        return vm_uuid
```

### Option 3 : Utiliser Terraform/Ansible (Pour automatisation avancée)

Si vous voulez une solution plus robuste pour la production.

## 🚀 Comment intégrer dans votre orchestrator

### Étape 1 : Remplacer le fichier

Copiez le contenu de `xenserver_client_real.py` dans `app/services/xenserver_client.py`

```bash
cd bojemoi-orchestrator
cp xenserver_client_real.py app/services/xenserver_client.py
```

### Étape 2 : Mettre à jour requirements.txt

Ajoutez :
```
XenAPI==1.0
```

### Étape 3 : Vérifier la configuration

Dans `.env` :
```bash
# URL doit pointer vers XenServer
XENSERVER_URL=https://votre-xenserver.local

# Credentials valides
XENSERVER_USER=root
XENSERVER_PASS=votre_mot_de_passe
```

### Étape 4 : Préparer XenServer

Sur votre serveur XenServer, assurez-vous d'avoir :

1. **Des templates disponibles** :
```bash
xe template-list name-label=alpine-template
```

2. **Des réseaux configurés** :
```bash
xe network-list
```

3. **XenAPI accessible** (port 443 HTTPS)

### Étape 5 : Tester

```bash
# Reconstruire avec la vraie implémentation
docker-compose build

# Redémarrer
docker-compose up -d

# Tester la connexion
curl http://localhost:8000/health

# Créer une vraie VM !
curl -X POST http://localhost:8000/api/v1/vm/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-vm-01",
    "template": "alpine-template",
    "os_type": "alpine",
    "cpu": 2,
    "memory": 2048,
    "disk": 20
  }'
```

## 🔧 Personnalisation selon votre environnement

### Adapter les noms de templates

Dans votre code, les templates sont cherchés par nom :

```python
# Ligne actuelle
templates = self.session.xenapi.VM.get_by_name_label(template)

# Si vos templates ont un préfixe
templates = self.session.xenapi.VM.get_by_name_label(f"tpl-{template}")
```

### Gérer les Storage Repositories (SR)

Pour choisir où créer les disques :

```python
# Lister les SRs disponibles
srs = self.session.xenapi.SR.get_all()

# Utiliser un SR spécifique
sr_ref = self.session.xenapi.SR.get_by_name_label("Local storage")[0]
```

### Gérer les VLANs

Pour des configurations réseau avancées :

```python
# Créer une VIF sur un VLAN spécifique
network_ref = self.session.xenapi.network.get_by_name_label("VLAN100")[0]
vif_record = {
    'device': '0',
    'network': network_ref,
    'VM': vm_ref,
    ...
}
```

## 📚 Documentation XenAPI

Pour aller plus loin :

- **XenAPI Documentation** : https://docs.xenserver.com/
- **Python XenAPI Guide** : https://github.com/xapi-project/xen-api
- **XenServer Developer Guide** : https://docs.xenserver.com/en-us/developer/

## ⚠️ Points importants

1. **Certificats SSL** : XenServer utilise souvent des certificats auto-signés. Vous devrez peut-être désactiver la vérification SSL en développement.

2. **Timeouts** : La création de VM peut prendre du temps. Augmentez les timeouts si nécessaire.

3. **Gestion d'erreurs** : XenAPI lance des exceptions `XenAPI.Failure` - gérez-les correctement.

4. **Sessions** : Réutilisez les sessions pour éviter trop de connexions.

5. **Cloud-init** : La méthode d'injection de cloud-init peut varier selon la version de XenServer.

## 🧪 Mode de développement sans XenServer

Si vous n'avez pas encore accès à XenServer mais voulez tester :

### Option A : Créer un mock (simulateur amélioré)

```python
class XenServerMockClient:
    """Mock pour développement sans XenServer"""
    
    def __init__(self, *args, **kwargs):
        self.vms = {}  # Stocke les VMs en mémoire
    
    async def create_vm(self, name, **kwargs):
        vm_uuid = f"mock-{uuid.uuid4()}"
        self.vms[vm_uuid] = {
            "name": name,
            "state": "running",
            **kwargs
        }
        logger.info(f"MOCK: Created VM {name} with UUID {vm_uuid}")
        return vm_uuid
```

### Option B : Utiliser XCP-ng dans une VM

XCP-ng est la version open source de XenServer :
1. Télécharger XCP-ng : https://xcp-ng.org/
2. Installer dans VirtualBox/VMware
3. Tester votre orchestrator contre XCP-ng

## 🎯 Résumé

| Approche | Avantages | Inconvénients |
|----------|-----------|---------------|
| **XenAPI** (Recommandé) | API officielle, complète, bien documentée | Nécessite bibliothèque Python |
| **xe CLI** | Simple, pas de dépendances spéciales | Moins flexible, gestion d'erreurs limitée |
| **Mock** | Développement sans infrastructure | Ne teste pas la vraie intégration |

**Recommandation** : Utilisez l'implémentation XenAPI fournie dans `xenserver_client_real.py` !
