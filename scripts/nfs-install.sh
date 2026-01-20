#!/bin/ash

# Script de préparation des nœuds Docker Swarm pour NFS
set -e

echo "=== Préparation du nœud pour NFS Server ==="

# 1. Installation des paquets nécessaires
echo "Installation des paquets NFS..."
if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    apt-get update
    apt-get install -y nfs-kernel-server nfs-common rpcbind
elif command -v yum &> /dev/null; then
    # RHEL/CentOS
    yum install -y nfs-utils rpcbind
elif command -v apk &> /dev/null; then
    # Alpine
    apk add --no-cache nfs-utils
fi

# 2. Chargement des modules kernel
echo "Chargement des modules kernel NFS..."
modprobe nfs
modprobe nfsd 2>/dev/null || true
modprobe lockd
modprobe sunrpc

# 3. Vérification des modules
echo "Vérification des modules chargés :"
lsmod | grep -E "(nfs|lockd|sunrpc)" || echo "Certains modules NFS peuvent ne pas être visibles"

# 4. Configuration pour le démarrage automatique
echo "Configuration des modules pour le démarrage..."
echo "nfs" |  tee -a /etc/modules 2>/dev/null || true
echo "nfsd" | tee -a /etc/modules 2>/dev/null || true
echo "lockd" | tee -a /etc/modules 2>/dev/null || true
echo "sunrpc" | tee -a /etc/modules 2>/dev/null || true

# 5. Création du répertoire de données
echo "Création du répertoire de données NFS..."
mkdir -p /opt/bojemoi/nfs-exports
chmod 755 /opt/bojemoi/nfs-exports 
chown root:root /opt/bojemoi/nfs-exports 

# 6. Configuration des ports fixes pour NFS (optionnel)
echo "Configuration des ports fixes..."
mkdir -p /etc/default
cat | tee /etc/default/nfs-kernel-server <<EOF
# Ports fixes pour NFS (optionnel pour Docker)
RPCMOUNTDOPTS="--port 20048"
RPCNFSDOPTS="-N 2 -N 3"
EOF

# 7. Test des capabilities Docker
echo "Test des capabilities Docker..."
docker --version || { echo "Docker n'est pas installé !"; exit 1; }

# 8. Labellisation du nœud (à exécuter sur le manager)
echo "Pour labelliser ce nœud, exécutez sur un nœud manager :"
echo "docker node update --label-add nfs-capable=true $(hostname)"

echo "=== Préparation terminée ==="
echo "Le nœud est prêt pour héberger des conteneurs NFS."
echo ""
echo "Commandes de vérification :"
echo "  lsmod | grep nfs"
echo "  docker info"
echo "  ls -la /opt/nfs-data"

