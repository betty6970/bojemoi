#!/bin/ash
set -e

# Création des répertoires nécessaires
mkdir -p /var/lib/nfs/rpc_pipefs
mkdir -p /var/lib/nfs/v4recovery
mkdir -p /run/rpcbind

# Montage du système de fichiers RPC si nécessaire
if ! mountpoint -q /var/lib/nfs/rpc_pipefs; then
    mount -t rpc_pipefs rpc_pipefs /var/lib/nfs/rpc_pipefs
fi

# Démarrage des services en arrière-plan
echo "Démarrage de rpcbind..."
rpcbind -w -f &
RPCBIND_PID=$!

# Attendre que rpcbind soit prêt
sleep 2

echo "Démarrage de rpc.nfsd..."
rpc.nfsd --no-udp  --no-nfs-version 3 8

echo "Démarrage de rpc.mountd..."
rpc.mountd --no-udp  --no-nfs-version 3 -F &
MOUNTD_PID=$!

# Export des partages NFS
echo "Export des partages NFS..."
exportfs -ra

echo "Serveur NFS démarré avec succès"

# Garder le processus principal actif
wait

# Export des partages NFS
echo "Export des partages NFS..."
exportfs -ra

# Vérifier que les services fonctionnent
echo "Vérification des services..."
rpcinfo -p localhost || echo "ATTENTION: rpcinfo échoué"

echo "Serveur NFS démarré avec succès"
echo "Services actifs:"
echo "  - rpcbind PID: $RPCBIND_PID"
echo "  - mountd PID: $MOUNTD_PID"
echo "  - nfsd: $(pgrep nfsd || echo 'non trouvé')"

# Boucle infinie pour maintenir le conteneur actif
# ET surveiller les processus critiques
while true; do
    # Vérifier que rpcbind fonctionne toujours
    if ! kill -0 $RPCBIND_PID 2>/dev/null; then
        echo "ERREUR: rpcbind s'est arrêté, redémarrage..."
        rpcbind -w -f &
        RPCBIND_PID=$!
        sleep 2
    fi
    
    # Vérifier que mountd fonctionne toujours
    if ! kill -0 $MOUNTD_PID 2>/dev/null; then
        echo "ERREUR: mountd s'est arrêté, redémarrage..."
        rpc.mountd --no-udp --no-nfs-version 2 --no-nfs-version 3 -F &
        MOUNTD_PID=$!
        sleep 2
    fi
    
    # Vérifier que nfsd fonctionne
    if ! pgrep -f nfsd > /dev/null; then
        echo "ERREUR: nfsd s'est arrêté, redémarrage..."
        rpc.nfsd --no-udp --no-nfs-version 2 --no-nfs-version 3 8
        sleep 2
    fi
    
    # Attendre 30 secondes avant la prochaine vérification
    sleep 30
done

