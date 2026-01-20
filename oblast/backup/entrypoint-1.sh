#!/bin/ash

set -e

echo "Démarrage du client OpenVPN pour Proton VPN..."

# Vérification des variables d'environnement
if [ -z "$PROTON_USERNAME" ] || [ -z "$PROTON_PASSWORD" ]; then
    echo "Erreur: PROTON_USERNAME et PROTON_PASSWORD doivent être définis"
    exit 1
fi

# Téléchargement des configurations Proton VPN si elles n'existent pas
if [ ! -d "/etc/openvpn/configs" ]; then
    echo "Téléchargement des configurations Proton VPN..."
    mkdir -p /etc/openvpn/configs
    
    # URL publique pour les configurations OpenVPN de Proton VPN
    curl -L -o /etc/openvpn/proton-configs.zip "https://downloads.protonvpn.com/openvpn-configs.zip"
    
    # Extraction des configurations
    cd /etc/openvpn
    unzip -o proton-configs.zip -d configs/
    rm proton-configs.zip
    
    # Les fichiers sont généralement dans un sous-dossier
    if [ -d "/etc/openvpn/configs/ProtonVPN_server_configs" ]; then
        mv /etc/openvpn/configs/ProtonVPN_server_configs/* /etc/openvpn/configs/
        rmdir /etc/openvpn/configs/ProtonVPN_server_configs
    fi
fi

# Création du fichier d'authentification
cat > /etc/openvpn/auth.txt << EOF
${PROTON_USERNAME}
${PROTON_PASSWORD}
EOF

chmod 600 /etc/openvpn/auth.txt

# Détermination du fichier de configuration à utiliser
if [ -n "$PROTON_SERVER" ]; then
    CONFIG_FILE=$(find /etc/openvpn/configs -name "*${PROTON_SERVER}*${PROTON_PROTOCOL}*.ovpn" | head -1)
    if [ -z "$CONFIG_FILE" ]; then
        echo "Erreur: Serveur $PROTON_SERVER non trouvé"
        echo "Serveurs disponibles:"
        find /etc/openvpn/configs -name "*.ovpn" | grep -o '[^/]*\.ovpn$' | sort
        exit 1
    fi
else
    # Utilisation du premier serveur disponible si aucun serveur spécifié
    CONFIG_FILE=$(find /etc/openvpn/configs -name "*${PROTON_PROTOCOL}*.ovpn" | head -1)
fi

echo "Utilisation du fichier de configuration: $(basename $CONFIG_FILE)"

# Modification du fichier de configuration pour utiliser l'authentification
sed -i '/auth-user-pass/c\auth-user-pass /etc/openvpn/auth.txt' "$CONFIG_FILE"

# Configuration des routes et DNS (optionnel)
cat >> "$CONFIG_FILE" << EOF

# Rediriger tout le trafic via le VPN
redirect-gateway def1

# Utiliser les DNS de Proton
dhcp-option DNS 10.2.0.1
dhcp-option DNS 8.8.8.8

# Script pour gérer les routes
up /etc/openvpn/up.sh
down /etc/openvpn/down.sh
EOF

# Création des scripts up/down
cat > /etc/openvpn/up.sh << 'EOF'
#!/bin/bash
echo "VPN connecté - Interface: $dev, IP: $ifconfig_local"
EOF

cat > /etc/openvpn/down.sh << 'EOF'
#!/bin/bash
echo "VPN déconnecté"
EOF

chmod +x /etc/openvpn/up.sh /etc/openvpn/down.sh

echo "Connexion au serveur Proton VPN..."
exec openvpn --config "$CONFIG_FILE" --verb 3
