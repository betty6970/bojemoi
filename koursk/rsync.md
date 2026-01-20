
lution Rsync Native Docker Swarm (sans NFS)

## Approches pour le stockage sans NFS

### 1. Volumes bind locaux avec contraintes de placement

Cette approche utilise des répertoires locaux sur chaque nœud avec des contraintes de placement pour garantir que les services s'exécutent sur les bons nœuds.

#### Préparation des nœuds

```bash
# Sur chaque nœud du swarm
sudo mkdir -p /opt/rsync/data/{source,replica}
sudo mkdir -p /opt/rsync/logs
sudo chown -R $(id -u):$(id -g) /opt/rsync

# Labelliser le nœud master
docker node update --label-add rsync.master=true <node-id-manager>

# Labelliser les nœuds slaves
docker node update --label-add rsync.slave=true <node-id-worker1>
docker node update --label-add rsync.slave=true <node-id-worker2>
```

### 2. Solution avec volumes Docker distribués

```yaml
# docker-compose-distributed.yml
version: '3.8'

services:
  # Service de distribution des données
  rsync-distributor:
    image: rsync-custom:latest
    deploy:
      mode: global
      placement:
        constraints:
          - node.role == worker
    volumes:
      - replica_data:/data/replica
      - ssh_keys:/root/.ssh:ro
    environment:
      - RSYNC_MODE=distributor
      - MASTER_HOST=rsync-master
    networks:
      - rsync_network
    command: ["/scripts/rsync-distributor.sh"]

  rsync-master:
    image: rsync-custom:latest
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.rsync.role == master
    volumes:
      - source_data:/data/source
      - ssh_keys:/root/.ssh:ro
    environment:
      - RSYNC_MODE=master
      - SYNC_INTERVAL=300
    networks:
      - rsync_network

volumes:
  source_data:
    driver: local
    driver_opts:
      type: none
      device: /opt/rsync/source
      o: bind
  
  replica_data:
    driver: local
    driver_opts:
      type: none  
      device: /opt/rsync/replica
      o: bind

  ssh_keys:
    driver: local

networks:
  rsync_network:
    driver: overlay
    attachable: true
```

### 3. Solution avec GlusterFS intégré

```yaml
# docker-compose-gluster.yml
version: '3.8'

services:
  # Service GlusterFS
  glusterfs:
    image: gluster/gluster-centos:latest
    deploy:
      mode: global
      placement:
        constraints:
          - node.role == worker
    volumes:
      - /opt/gluster/brick:/data/brick
      - /var/lib/glusterd:/var/lib/glusterd
    networks:
      - rsync_network
    privileged: true
    command: glusterd --no-daemon --log-level INFO

  rsync-master:
    image: rsync-custom:latest
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.rsync.role == master
    volumes:
      - gluster_source:/data/source
      - ssh_keys:/root/.ssh:ro
    environment:
      - RSYNC_MODE=master
      - SYNC_INTERVAL=300
    networks:
      - rsync_network
    depends_on:
      - glusterfs

  rsync-slave:
    image: rsync-custom:latest
    deploy:
      replicas: 2
      placement:
        constraints:
          - node.role == worker
    volumes:
      - gluster_replica:/data/replica
      - ssh_keys:/root/.ssh:ro
    environment:
      - RSYNC_MODE=slave
    networks:
      - rsync_network
    depends_on:
      - glusterfs

volumes:
  gluster_source:
    driver: local
    driver_opts:
      type: glusterfs
      o: addr=glusterfs,volname=source_vol
      device: "glusterfs-server:/source_vol"
  
  gluster_replica:
    driver: local
    driver_opts:
      type: glusterfs
      o: addr=glusterfs,volname=replica_vol
      device: "glusterfs-server:/replica_vol"

  ssh_keys:
    driver: local

networks:
  rsync_network:
    driver: overlay
    attachable: true
```

### 4. Solution avec synchronisation P2P

```bash
# Script rsync-p2p.sh pour synchronisation peer-to-peer
cat > /scripts/rsync-p2p.sh << 'EOF'
#!/bin/bash
set -e

LOG_FILE="/var/log/rsync/rsync-p2p.log"
NODE_ID=$(docker info --format '{{.Swarm.NodeID}}')
MASTER_NODE=${MASTER_NODE:-""}

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [P2P-$NODE_ID] $1" | tee -a "$LOG_FILE"
}

# Découverte des nœuds peers
discover_peers() {
    docker service ps rsync-stack_rsync-slave --format "{{.Node}}" | grep -v "$NODE_ID" | head -5
}

# Synchronisation multi-directionnelle
sync_with_peers() {
    local peers=$(discover_peers)
    
    for peer in $peers; do
        log "Synchronisation avec peer: $peer"
        
        # Pull depuis le peer
        if rsync -avz --timeout=30 \
           root@$peer:/data/replica/ \
           /data/replica-temp/; then
            
            # Merge des données
            rsync -avz --ignore-existing \
                  /data/replica-temp/ \
                  /data/replica/
            
            log "Synchronisation depuis $peer: OK"
        else
            log "Synchronisation depuis $peer: ÉCHEC"
        fi
        
        # Push vers le peer
        rsync -avz --timeout=30 \
              /data/replica/ \
              root@$peer:/data/replica/ && \
        log "Push vers $peer: OK" || \
        log "Push vers $peer: ÉCHEC"
    done
}

# Boucle principale
while true; do
    sync_with_peers
    sleep ${SYNC_INTERVAL:-300}
done
EOF
```

## Scripts de déploiement simplifiés

```bash
#!/bin/bash
# deploy-rsync-native.sh

set -e

echo "� Déploiement de la solution Rsync native Docker Swarm"

# Vérification du swarm
if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q active; then
    echo "❌ Docker Swarm non initialisé"
    exit 1
fi

# Préparation des répertoires sur tous les nœuds
echo "� Initialisation des répertoires..."
docker service create --name init-dirs --mode global \
    --mount type=bind,source=/opt,target=/host \
    --restart-condition none \
    alpine:3.18 sh -c "
    mkdir -p /host/rsync/data/{source,replica} /host/rsync/logs
    chmod 755 /host/rsync/data/*
    echo 'Init complete on \$(hostname)' > /host/rsync/init.log
    "

# Attendre la fin de l'initialisation
echo "⏳ Attente de l'initialisation..."
sleep 10
docker service rm init-dirs

# Génération des clés SSH
echo "� Génération des clés SSH..."
mkdir -p keys
if [ ! -f keys/id_rsa ]; then
    ssh-keygen -t rsa -b 4096 -f keys/id_rsa -N ""
fi

# Création du volume pour les clés
docker volume create rsync_ssh_keys
docker run --rm -v rsync_ssh_keys:/keys -v $(pwd)/keys:/host_keys alpine:3.18 \
    sh -c "cp /host_keys/* /keys/ && chmod 600 /keys/id_rsa && chmod 644 /keys/id_rsa.pub"

# Construction des images
echo "�️  Construction des images..."
docker build -f Dockerfile.rsync -t rsync-custom:latest .

# Labellisation des nœuds
echo "�️  Configuration des labels de nœuds..."
MANAGER_NODE=$(docker node ls --filter role=manager --format "{{.ID}}" | head -1)
docker node update --label-add rsync.master=true $MANAGER_NODE

# Déploiement de la stack
echo "� Déploiement de la stack..."
docker stack deploy -c docker-compose-rsync-swarm.yml rsync-stack

echo "✅ Déploiement terminé !"
echo "� Vérification des services:"
docker service ls | grep rsync

echo ""
echo "� Commandes utiles:"
echo "  docker service logs rsync-stack_rsync-master"
echo "  docker service logs rsync-stack_rsync-slave"
echo "  docker stack ps rsync-stack"
```

## Comparaison des approches

| Approche | Avantages | Inconvénients | Cas d'usage |
|----------|-----------|---------------|-------------|
| **Bind mounts** | Simple, rapide, pas de dépendances | Données liées aux nœuds | Environnements stables |
| **GlusterFS** | Vraie réplication, haute disponibilité | Complexité, overhead réseau | Production critique |
| **P2P Sync** | Résilience, pas de point unique de défaillance | Complexité de synchronisation | Environnements distribués |
| **Volumes Docker** | Intégration native, simplicité | Limitée aux capacités du driver | Développement/test |

## Recommandation

Pour une solution **purement native Docker Swarm**, je recommande l'approche avec **bind mounts + contraintes de placement** car elle :

- ✅ N'a aucune dépendance externe
- ✅ Utilise uniquement les fonctionnalités natives de Docker Swarm  
- ✅ Est simple à maintenir et déboguer
- ✅ Offre de bonnes performances
- ✅ Permet un contrôle fin du placement des données

Cette solution est idéale pour la plupart des cas d'usage de réplication avec rsync sous Docker Swarm.

