# Configuration Traefik pour Deployment Orchestrator

## 🔧 Labels Traefik inclus

Le fichier `docker-compose.swarm.yml` contient déjà tous les labels Traefik nécessaires.

### URLs exposées

- **API principale** : `https://orchestrator.bojemoi.lab`
- **Webhook Gitea** : `https://orchestrator.bojemoi.lab/webhook/gitea`
- **Métriques Prometheus** : `https://orchestrator.bojemoi.lab/metrics`
- **Health check** : `https://orchestrator.bojemoi.lab/health`

## 📋 Configuration des labels

### Router principal (API)
```yaml
traefik.http.routers.orchestrator-api.rule=Host(`orchestrator.bojemoi.lab`)
traefik.http.routers.orchestrator-api.entrypoints=websecure
traefik.http.routers.orchestrator-api.tls=true
traefik.http.routers.orchestrator-api.tls.certresolver=letsencrypt
traefik.http.services.orchestrator-api.loadbalancer.server.port=8080
```

### Webhook avec rate limiting
```yaml
# Router webhook
traefik.http.routers.orchestrator-webhook.rule=Host(`orchestrator.bojemoi.lab`) && PathPrefix(`/webhook`)
traefik.http.routers.orchestrator-webhook.middlewares=orchestrator-ratelimit

# Middleware rate limit (10 req/s en moyenne, burst de 20)
traefik.http.middlewares.orchestrator-ratelimit.ratelimit.average=10
traefik.http.middlewares.orchestrator-ratelimit.ratelimit.burst=20
```

### Métriques Prometheus
```yaml
traefik.http.routers.orchestrator-metrics.rule=Host(`orchestrator.bojemoi.lab`) && PathPrefix(`/metrics`)
traefik.http.services.orchestrator-metrics.loadbalancer.server.port=9090
```

## 🔐 Sécurité supplémentaire (optionnelle)

### 1. Authentification Basic pour les métriques

Ajouter ces labels dans `docker-compose.swarm.yml` :

```yaml
# Générer le mot de passe d'abord :
# echo $(htpasswd -nb admin password) | sed -e s/\\$/\\$\\$/g

# Puis ajouter :
- "traefik.http.routers.orchestrator-metrics.middlewares=metrics-auth"
- "traefik.http.middlewares.metrics-auth.basicauth.users=admin:$$apr1$$xyz..."
```

### 2. Whitelist IP pour webhook (si Gitea a IP fixe)

```yaml
- "traefik.http.routers.orchestrator-webhook.middlewares=orchestrator-ratelimit,webhook-whitelist"
- "traefik.http.middlewares.webhook-whitelist.ipwhitelist.sourcerange=10.0.0.0/8,172.16.0.0/12"
```

### 3. Headers de sécurité

```yaml
- "traefik.http.routers.orchestrator-api.middlewares=security-headers"
- "traefik.http.middlewares.security-headers.headers.framedeny=true"
- "traefik.http.middlewares.security-headers.headers.sslredirect=true"
- "traefik.http.middlewares.security-headers.headers.stsSeconds=31536000"
- "traefik.http.middlewares.security-headers.headers.contentTypeNosniff=true"
```

## 🌐 Configuration DNS

Assurez-vous que le DNS pointe vers votre cluster Swarm :

```
orchestrator.bojemoi.lab    A    <IP_MANAGER_NODE>
```

Ou si vous avez un load balancer :

```
orchestrator.bojemoi.lab    A    <IP_LOAD_BALANCER>
```

## 🔍 Vérification Traefik

### Vérifier que Traefik détecte le service

```bash
# Dashboard Traefik (si activé)
https://traefik.bojemoi.lab/dashboard/

# Ou via API
curl https://traefik.bojemoi.lab/api/http/routers | jq '.[] | select(.name | contains("orchestrator"))'
```

### Tester les endpoints

```bash
# API principale
curl https://orchestrator.bojemoi.lab/

# Health check
curl https://orchestrator.bojemoi.lab/health

# Métriques
curl https://orchestrator.bojemoi.lab/metrics

# Webhook (avec payload valide)
curl -X POST https://orchestrator.bojemoi.lab/webhook/gitea \
  -H "Content-Type: application/json" \
  -d '{"ref":"refs/heads/main",...}'
```

## 📊 Configuration Traefik Stack (référence)

Votre stack Traefik devrait ressembler à ça :

```yaml
version: '3.8'

services:
  traefik:
    image: traefik:v2.10
    command:
      - "--api.dashboard=true"
      - "--providers.docker=true"
      - "--providers.docker.swarmMode=true"
      - "--providers.docker.exposedbydefault=false"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@bojemoi.lab"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - traefik-certificates:/letsencrypt
    networks:
      - bojemoi_network
    deploy:
      placement:
        constraints:
          - node.role == manager
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.dashboard.rule=Host(`traefik.bojemoi.lab`)"
        - "traefik.http.routers.dashboard.service=api@internal"
        - "traefik.http.routers.dashboard.entrypoints=websecure"
        - "traefik.http.routers.dashboard.tls.certresolver=letsencrypt"

networks:
  bojemoi_network:
    external: true

volumes:
  traefik-certificates:
```

## 🔧 Configuration avancée

### Load balancing avec plusieurs réplicas

Si vous scalez l'orchestrator :

```bash
docker service scale deployment-orchestrator_orchestrator=3
```

Traefik gérera automatiquement le load balancing round-robin.

### Sticky sessions (si nécessaire)

```yaml
- "traefik.http.services.orchestrator-api.loadbalancer.sticky.cookie=true"
- "traefik.http.services.orchestrator-api.loadbalancer.sticky.cookie.name=orchestrator_session"
```

### Circuit breaker

```yaml
- "traefik.http.middlewares.orchestrator-cb.circuitbreaker.expression=NetworkErrorRatio() > 0.5"
- "traefik.http.routers.orchestrator-api.middlewares=orchestrator-cb"
```

### Retry policy

```yaml
- "traefik.http.middlewares.orchestrator-retry.retry.attempts=3"
- "traefik.http.routers.orchestrator-api.middlewares=orchestrator-retry"
```

## 🐛 Troubleshooting Traefik

### Service non détecté par Traefik

```bash
# Vérifier les labels du service
docker service inspect deployment-orchestrator_orchestrator --format '{{json .Spec.Labels}}' | jq

# Vérifier que Traefik voit le service
docker service logs traefik | grep orchestrator

# Vérifier le réseau
docker service inspect deployment-orchestrator_orchestrator --format '{{json .Spec.TaskTemplate.Networks}}'
```

### Certificat SSL non généré

```bash
# Vérifier les logs Traefik
docker service logs traefik | grep acme

# Vérifier le resolver
docker service inspect traefik --format '{{json .Spec.TaskTemplate.ContainerSpec.Args}}' | jq
```

### 502 Bad Gateway

```bash
# Vérifier que le service répond
docker service ps deployment-orchestrator_orchestrator

# Tester directement le service
curl http://<CONTAINER_IP>:8080/health

# Vérifier les healthchecks
docker service inspect deployment-orchestrator_orchestrator --format '{{json .Spec.TaskTemplate.ContainerSpec.Healthcheck}}'
```

## 📝 Exemple de configuration complète dans Gitea

Pour configurer le webhook Gitea avec Traefik :

1. **URL du webhook** : `https://orchestrator.bojemoi.lab/webhook/gitea`
2. **Content Type** : `application/json`
3. **Secret** : Votre `GITEA_WEBHOOK_SECRET`
4. **SSL verification** : Activé (si certificat Let's Encrypt valide)

## 🎯 Checklist de déploiement

- [ ] Réseau `bojemoi_network` créé
- [ ] Traefik déployé et fonctionnel
- [ ] DNS `orchestrator.bojemoi.lab` configuré
- [ ] Labels Traefik présents dans docker-compose.swarm.yml
- [ ] Service déployé : `docker stack deploy ...`
- [ ] Certificat SSL généré automatiquement
- [ ] Endpoints accessibles via HTTPS
- [ ] Webhook Gitea configuré avec l'URL HTTPS
- [ ] Rate limiting actif sur /webhook
- [ ] Monitoring Prometheus accessible
