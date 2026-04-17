# Runbook — Rebuild + redéploiement borodino

## Rebuild de l'image

```bash
cd /opt/bojemoi

docker build -f borodino/Dockerfile.borodino -t localhost:5000/borodino:latest borodino/
docker push localhost:5000/borodino:latest
```

## Redéploiement complet du stack

```bash
docker stack deploy -c stack/40-service-borodino.yml borodino --prune --resolve-image always
```

## Forcer un rolling update sans changer le tag

Quand le tag `:latest` n'a pas changé, `docker stack deploy` ne déclenche pas de mise à jour.
Utiliser le digest de l'image :

```bash
DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' localhost:5000/borodino:latest | cut -d@ -f2)

docker service update \
  --image localhost:5000/borodino:latest@${DIGEST} \
  --force \
  --detach \
  --update-parallelism 5 \
  borodino_ak47-service
```

## Contraintes de placement

- `max_replicas_per_node: 5` avec 2 workers actifs = 10 replicas max (pas 15)
- `borodino_uzi-service` nécessite `msfrpc` actif sur `192.168.1.47:55553`

## Vérification post-deploy

```bash
docker service ls | grep borodino
docker service logs -f borodino_ak47-service --tail 20
```
