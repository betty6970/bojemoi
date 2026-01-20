#!/bin/sh
# Script d'entrée pour le container Alpine

set -e

echo "=========================================="
echo "Démarrage du container Alpine Scanner"
echo "=========================================="


# Attendre que les bases de données soient disponibles
wait_for_db() {
    local host=$1
    local port=$2
    local name=$3
    
    echo "Attente de $name ($host:$port)..."
    
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z $host $port 2>/dev/null; then
            echo "$name est disponible"
            return 0
        fi
        
        echo "Tentative $attempt/$max_attempts - $name non disponible, attente..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    echo "ERREUR: $name non disponible après $max_attempts tentatives"
    exit 2
}
#==============≠
set_openvpn() {
#==============≠

# Configuration de l'IP forwarding
#sysctl -w net.ipv4.ip_forward=1


# Création de la configuration serveur si elle n'existe pas
if [ ! -f /etc/openvpn/server.conf ]; then
    cat > /etc/openvpn/server.conf <<EOF
port 1194
proto udp
dev tun

ca ca.crt
cert server.crt
key server.key
dh dh.pem
tls-auth pki/ta.key 0

server 10.8.0.0 255.255.255.0
ifconfig-pool-persist ipp.txt

push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 8.8.8.8"
push "dhcp-option DNS 8.8.4.4"

keepalive 10 120
cipher AES-256-CBC
user nobody
group nobody
persist-key
persist-tun

status openvpn-status.log
verb 3
EOF
    echo "Configuration serveur créée"
fi

# Configuration du NAT avec iptables
mkdir -p /dev/net
mknod /dev/net/tun c 10 200 2>/dev/null || true 
chmod 600 /dev/net/tun
openvpn --config /etc/openvpn/openvpn.conf --daemon
}
# lancement openvpn
set_openvpn

# Vérifier la connectivité réseau
echo "Test de connectivité réseau..."
if ! ping -c 1 8.8.8.8 >/dev/null 2>&1; then
    echo "ATTENTION: Pas de connectivité Internet détectée"
fi

# Attendre les bases de données
wait_for_db $IP2LOCATION_DB_HOST $IP2LOCATION_DB_PORT "IP2Location Database"
wait_for_db $MSF_DB_HOST $MSF_DB_PORT "Metasploit Database"

# Vérifier que Masscan est disponible
echo "Vérification de Masscan..."
which openvpn > /dev/null 2>&1
if ! which openvpn > /dev/null 2>&1; then
    echo "ERREUR: Masscan non disponible"
    exit 1
fi
echo "Masscan: OK"

# Afficher la configuration
echo "Configuration du scan:"
echo "  Pays cible: ${TARGET_COUNTRY:-Non défini}"
echo "  ISP cible: ${TARGET_ISP:-Non défini}"
echo "  Ports: ${SCAN_PORTS}"
echo "  Taux: ${SCAN_RATE} pps"
echo "  Max CIDR: ${MAX_CIDRS}"
echo "  IP2Location DB: ${IP2LOCATION_DB_HOST}:${IP2LOCATION_DB_PORT}/${IP2LOCATION_DB_NAME}"
echo "  MSF DB: ${MSF_DB_HOST}:${MSF_DB_PORT}/${MSF_DB_NAME}"

# Créer les répertoires nécessaires
mkdir -p /tmp/masscan_results
mkdir -p /var/log

echo "=========================================="
echo "Lancement du script principal..."
echo "=========================================="

# Exécuter la commande
exec "$@"
