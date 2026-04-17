# Runbook — Rotation d'un secret Docker Swarm

## Contrainte importante

Un secret Docker Swarm **ne peut pas être modifié**. Pour le remplacer :
1. Arrêter **complètement** les services qui l'utilisent (scale 0 ne suffit pas — le secret reste attaché)
2. Supprimer le secret
3. Recréer le secret avec la nouvelle valeur
4. Redéployer les services

## Procédure

```bash
# 1. Identifier les services utilisant le secret
docker service ls --format '{{.Name}}' | while read s; do
  docker service inspect $s --format "{{.Spec.Name}}: {{range .Spec.TaskTemplate.ContainerSpec.Secrets}}{{.SecretName}} {{end}}"
done | grep <nom-du-secret>

# 2. Supprimer les services concernés
docker service rm <service1> <service2>

# 3. Supprimer le secret
docker secret rm <nom-du-secret>

# 4. Recréer le secret
echo -n "<nouvelle-valeur>" | docker secret create <nom-du-secret> -
# ou depuis un fichier :
docker secret create <nom-du-secret> /path/to/file

# 5. Redéployer
docker stack deploy -c stack/<stack>.yml <stack> --prune --resolve-image always
```

## Lire la valeur actuelle d'un secret

Les secrets ne sont lisibles que depuis les conteneurs. Sur le manager :

```bash
# Pour les services qui tournent sur le manager (base stack) :
docker exec $(docker ps -qf "name=base_<service>") cat /run/secrets/<nom-du-secret>

# Pour les services sur les workers :
NODE_IP=$(docker node inspect meta-68 --format '{{.Status.Addr}}')
ssh -p 4422 -i ~/.ssh/meta76_ed25519 docker@$NODE_IP \
  "docker exec \$(docker ps -qf 'name=<service>') cat /run/secrets/<nom-du-secret>"
```

## Récupérer POSTGRES_PASSWORD (cas particulier)

```bash
docker service inspect base_postgres \
  --format '{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{.}}{{"\n"}}{{end}}' \
  | grep POSTGRES_PASSWORD
```
