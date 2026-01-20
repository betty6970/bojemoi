#!/bin/sh

set -e

STACK_NAME="vpn-app"
VPN_NODE_LABEL="vpn-node=true"

echo "� Déploiement automatisé de la stack VPN"

# 1. Vérifier les prérequis
echo "� Vérification des prérequis..."

if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q "active"; then
    echo "❌ Docker Swarm n'est pas initialisé"
    echo "Initialisation avec: docker swarm init"
    exit 1
fi

# 2. Identifier ou créer le nœud VPN
echo "� Configuration du nœud VPN..."

# Vérifier si un nœud VPN existe déjà
VPN_NODES=$(docker node ls --filter "label=${VPN_NODE_LABEL}" --format "{{.Hostname}}")

if [ -z "$VPN_NODES" ]; then
    echo "⚙️ Aucun nœud VPN trouvé, configuration du nœud manager..."
    MANAGER_NODE=$(docker node ls --filter "role=manager" --format "{{.ID}}" | head -1)
    docker node update --label-add vpn-node=true $MANAGER_NODE
    echo "✅ Nœud manager configuré comme nœud VPN"
else
    echo "✅ Nœud VPN trouvé: $VPN_NODES"
fi

# 3. Vérifier les fichiers de configuration
echo "� Vérification des fichiers de configuration..."

if [ ! -f "./config/client.ovpn" ]; then
    echo "❌ Fichier client.ovpn manquant dans ./config/"
    echo "Veuillez copier votre fichier de configuration OpenVPN dans ./config/client.ovpn"
    exit 1
fi

if [ ! -f "./secrets/vpn-auth.txt" ]; then
    echo "❌ Fichier vpn-auth.txt manquant dans ./secrets/"
    echo "Créez le fichier avec vos identifiants VPN:"
    echo "username"
    echo "password"
    exit 1
fi

echo "✅ Fichiers de configuration présents"

# 4. Créer une configuration nginx par défaut si manquante
if [ ! -f "./config/nginx.conf" ]; then
    echo "⚙️ Création d'une configuration nginx par défaut..."
    mkdir -p ./config
    cat > ./config/nginx.conf << 'EOF'
events {
    worker_connections 1024;
}
http {
    server {
        listen 80;
        location / {
            return 200 "VPN Gateway OK\n";
            add_header Content-Type text/plain;
        }
        location /health {
            return 200 "OK\n";
            add_header Content-Type text/plain;
        }
    }
}
EOF
    echo "✅ Configuration nginx créée"
fi

# 5. Fonction pour attendre qu'un service soit prêt
wait_for_service() {
    local service_name="$1"
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Attente du service $service_name..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker service ps $service_name --filter "desired-state=running" --format "{{.CurrentState}}" | grep -q "Running"; then
            echo "✅ Service $service_name prêt"
            return 0
        fi
        echo "Tentative $attempt/$max_attempts..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    echo "❌ Timeout: Service $service_name non prêt après $max_attempts tentatives"
    return 1
}

# 6. Déployer la stack
echo "� Déploiement de la stack..."
docker stack deploy -c docker-stack-vpn-with-configs.yml $STACK_NAME

# 7. Attendre que les services soient prêts
wait_for_service "${STACK_NAME}_vpn-gateway"

# 8. Vérifier l'IP VPN
echo "� Vérification de l'IP VPN..."
sleep 10  # Attendre que la connexion VPN s'établisse

VPN_CONTAINER=$(docker ps -q --filter "name=${STACK_NAME}_vpn-gateway")
if [ -n "$VPN_CONTAINER" ]; then
    VPN_IP=$(docker exec $VPN_CONTAINER curl -s --max-time 10 https://ipinfo.io/ip 2>/dev/null || echo "N/A")
    echo "✅ IP via VPN: $VPN_IP"
else
    echo "⚠️ Container VPN non trouvé, vérification manuelle nécessaire"
fi

# 9. Afficher le statut final
echo ""
echo "� Statut final des services:"
docker stack services $STACK_NAME

echo ""
echo "✅ Déploiement terminé!"
echo ""
echo "Commandes utiles:"
echo "  docker stack services $STACK_NAME                    # Voir les services"
echo "  docker service logs ${STACK_NAME}_vpn-gateway        # Logs VPN"
echo "  docker stack rm $STACK_NAME                          # Supprimer la stack"
