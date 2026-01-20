# Structure Gitea attendue

Ce document décrit la structure de repository Gitea attendue par l'orchestrator.

## Repository: bojemoi-configs

```
bojemoi-configs/
├── cloud-init/
│   ├── alpine/
│   │   ├── webserver.yaml
│   │   ├── database.yaml
│   │   └── minimal.yaml
│   ├── ubuntu/
│   │   ├── webserver.yaml
│   │   ├── database.yaml
│   │   └── default.yaml
│   ├── debian/
│   │   ├── webserver.yaml
│   │   └── default.yaml
│   └── common/
│       ├── setup_monitoring.sh
│       ├── setup_docker.sh
│       └── hardening.sh
├── templates/
│   └── vm-defaults.yaml
└── README.md
```

## Structure des templates cloud-init

### 1. Templates par OS (alpine/, ubuntu/, debian/)

Chaque OS a ses propres templates qui peuvent utiliser des variables Jinja2:

**Variables disponibles:**
- `{{ vm_name }}` - Nom de la VM
- `{{ hostname }}` - Hostname (identique à vm_name)
- `{{ fqdn }}` - FQDN complet
- `{{ environment }}` - Environment (production, staging, dev)
- Toutes variables additionnelles passées dans la requête

**Exemple: alpine/webserver.yaml**
```yaml
#cloud-config
hostname: {{ hostname }}
fqdn: {{ fqdn }}

packages:
  - nginx
  - docker

runcmd:
  - echo "Environment: {{ environment }}" > /etc/environment
  - rc-update add nginx default
  - rc-service nginx start
```

### 2. Scripts communs (common/)

Scripts réutilisables qui peuvent être référencés dans les templates:

**Exemple: common/setup_monitoring.sh**
```bash
#!/bin/bash
# Setup Prometheus node exporter

wget https://github.com/prometheus/node_exporter/releases/download/v1.7.0/node_exporter-1.7.0.linux-amd64.tar.gz
tar xvfz node_exporter-*.tar.gz
mv node_exporter-*/node_exporter /usr/local/bin/
```

Pour utiliser dans un template cloud-init:
```yaml
runcmd:
  - curl -o /tmp/setup_monitoring.sh https://gitea.bojemoi.me/bojemoi/bojemoi-configs/raw/branch/main/cloud-init/common/setup_monitoring.sh
  - chmod +x /tmp/setup_monitoring.sh
  - /tmp/setup_monitoring.sh
```

### 3. Templates par défaut (templates/)

Templates de configuration par défaut pour différents types de VMs:

**vm-defaults.yaml** - Configuration par défaut pour toutes les VMs
```yaml
default_user:
  name: admin
  sudo: ALL=(ALL) NOPASSWD:ALL
  shell: /bin/bash

timezone: Europe/Paris

package_update: true
package_upgrade: true
```

## Création de nouveaux templates

### 1. Template minimal

```yaml
#cloud-config
hostname: {{ hostname }}
fqdn: {{ fqdn }}

users:
  - name: admin
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - YOUR_SSH_KEY

packages:
  - curl
  - git

runcmd:
  - echo "{{ environment }}" > /etc/environment
```

### 2. Template avec variables custom

```yaml
#cloud-config
hostname: {{ hostname }}

# Variables custom passées dans la requête
{% if app_port %}
write_files:
  - path: /etc/app.conf
    content: |
      PORT={{ app_port }}
      DOMAIN={{ domain | default('localhost') }}
{% endif %}

runcmd:
  - echo "Application will run on port {{ app_port | default('8080') }}"
```

### 3. Utilisation dans l'API

```bash
curl -X POST http://localhost:8000/api/v1/vm/deploy \
  -H "Content-Type: application/json" \
  -d '{
    "name": "web-prod-01",
    "template": "webserver",
    "os_type": "alpine",
    "cpu": 4,
    "memory": 4096,
    "environment": "production",
    "variables": {
      "app_port": 8080,
      "domain": "example.com"
    }
  }'
```

## Bonnes pratiques

1. **Organisation**: Séparez les templates par OS
2. **Réutilisation**: Utilisez le répertoire `common/` pour les scripts partagés
3. **Variables**: Utilisez Jinja2 pour la flexibilité
4. **Validation**: Testez vos templates avant de les commiter
5. **Documentation**: Commentez vos templates
6. **Versioning**: Utilisez des branches Git pour différentes versions

## Validation des templates

Vous pouvez valider un template localement:

```bash
# Installer yamllint
pip install yamllint

# Valider un fichier
yamllint cloud-init/alpine/webserver.yaml
```

## Exemples complets

Voir le répertoire `examples/cloud-init/` pour des exemples complets de:
- Serveur web (nginx)
- Serveur de base de données (PostgreSQL)
- Configuration minimale
