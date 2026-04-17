# Runbook — Proton Mail Bridge re-login

**Symptôme** : Alertmanager échoue à envoyer des mails — logs `454 4.7.0 invalid username or password`

## Procédure

### 1. Stopper le service

```bash
docker service scale base_protonmail-bridge=0
```

### 2. Lancer un conteneur one-shot (bypasser l'entrypoint)

```bash
docker run --rm -it \
  --volume base_protonmail_data:/root \
  --network mail \
  --entrypoint /bin/bash \
  localhost:5000/protonmail-bridge:latest
```

> Ne pas utiliser l'entrypoint normal — `expect` bloque le stdin.

### 3. Login dans le bridge CLI

```bash
protonmail-bridge --cli
```

```
login
> email: <ton-email>
> password: <ton-mot-de-passe>

info
# noter le "SMTP Password" affiché
```

### 4. Mettre à jour le mot de passe SMTP dans alertmanager

```bash
vi /opt/bojemoi/volumes/alertmanager/alertmanager.yml
# modifier : smtp_auth_password: "<nouveau-mot-de-passe>"
```

### 5. Supprimer le lock file laissé par le one-shot

```bash
docker run --rm \
  --volume base_protonmail_data:/root \
  alpine \
  sh -c 'rm -f /root/.cache/protonmail/bridge-v3/bridge-v3.lock'
```

### 6. Redémarrer les services

```bash
docker service update --force base_protonmail-bridge
# Attendre que le bridge soit healthy
docker service update --force base_alertmanager
```

> Le hot-reload alertmanager (`/-/reload`) ne recharge **pas** le mot de passe SMTP en mémoire.
> Un restart complet est nécessaire.

## Réseaux impliqués

`alertmanager` et `protonmail-bridge` sont tous deux sur le réseau overlay `mail`.
