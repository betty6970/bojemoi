# Runbook — Accès SSH aux nœuds workers

## IPs dynamiques (DHCP)

Les IPs des workers changent au redémarrage. Toujours les résoudre via Swarm :

```bash
docker node inspect meta-68 --format '{{.Status.Addr}}'
docker node inspect meta-69 --format '{{.Status.Addr}}'
docker node inspect meta-70 --format '{{.Status.Addr}}'
```

## Connexion SSH

```bash
NODE_IP=$(docker node inspect <node> --format '{{.Status.Addr}}')
ssh -p 4422 -i /home/docker/.ssh/meta76_ed25519 -o StrictHostKeyChecking=no docker@$NODE_IP
```

## Aliases utiles

```bash
ssh-68() { ssh -p 4422 -i ~/.ssh/meta76_ed25519 -o StrictHostKeyChecking=no docker@$(docker node inspect meta-68 --format '{{.Status.Addr}}') "$@"; }
ssh-69() { ssh -p 4422 -i ~/.ssh/meta76_ed25519 -o StrictHostKeyChecking=no docker@$(docker node inspect meta-69 --format '{{.Status.Addr}}') "$@"; }
ssh-70() { ssh -p 4422 -i ~/.ssh/meta76_ed25519 -o StrictHostKeyChecking=no docker@$(docker node inspect meta-70 --format '{{.Status.Addr}}') "$@"; }
```

## Règles d'exécution des conteneurs

| Stack | Nœud | Remarque |
|-------|------|----------|
| `base`, `boot` | meta-76 (manager) | `docker exec` fonctionne depuis le manager |
| Tous les autres | workers uniquement | Doit SSH pour `docker exec` + lire `/run/secrets/*` |

## Lire un secret sur un worker

```bash
NODE_IP=$(docker node inspect meta-68 --format '{{.Status.Addr}}')
ssh -p 4422 -i ~/.ssh/meta76_ed25519 docker@$NODE_IP \
  "docker exec \$(docker ps -qf 'name=borodino_uzi') cat /run/secrets/telegram_bot_token"
```

## Labels des nœuds

```
meta-68 : rsync.slave=true, pentest=true, faraday=true, storage=true, nvidia.vgpu=true
meta-69 : rsync.slave=true, pentest=true, faraday=true
meta-70 : rsync.slave=true, pentest=true, storage=true
```
