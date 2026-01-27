#!/bin/sh
# Script pour afficher et gérer les configurations clients WireGuard
# Usage: ./show-clients.sh [list|show|qr|export]

CONFIG_DIR="."

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Fonction pour lister tous les clients
list_clients() {
    echo "${BLUE}=== Clients WireGuard disponibles ===${NC}"
    echo ""
    
    for peer_dir in "$CONFIG_DIR"/peer*; do
        if [ -d "$peer_dir" ]; then
            peer_name=$(basename "$peer_dir")
            conf_file="$peer_dir/$peer_name.conf"
            png_file="$peer_dir/$peer_name.png"
            
            if [ -f "$conf_file" ]; then
                echo "${GREEN}✓${NC} $peer_name"
                echo "  Config: $conf_file"
                echo "  QR PNG: $png_file"
                
                # Extraire l'IP du client
                ip=$(grep "Address = " "$conf_file" | cut -d'=' -f2 | tr -d ' ')
                echo "  IP VPN: $ip"
                echo ""
            fi
        fi
    done
}

# Fonction pour afficher la config d'un client spécifique
show_client() {
    peer_name="$1"
    
    if [ -z "$peer_name" ]; then
        echo "${YELLOW}Usage: $0 show <peer_name>${NC}"
        echo "Exemple: $0 show peer1"
        exit 1
    fi
    
    conf_file="$CONFIG_DIR/$peer_name/$peer_name.conf"
    
    if [ ! -f "$conf_file" ]; then
        echo "${YELLOW}Erreur: Client $peer_name introuvable${NC}"
        echo "Clients disponibles:"
        ls -d "$CONFIG_DIR"/peer* 2>/dev/null | xargs -n1 basename
        exit 1
    fi
    
    echo "${BLUE}=== Configuration de $peer_name ===${NC}"
    echo ""
    cat "$conf_file"
}

# Fonction pour afficher le QR code d'un client
show_qr() {
    peer_name="$1"
    
    if [ -z "$peer_name" ]; then
        echo "${YELLOW}Usage: $0 qr <peer_name>${NC}"
        echo "Exemple: $0 qr peer1"
        exit 1
    fi
    
    conf_file="$CONFIG_DIR/$peer_name/$peer_name.conf"
    png_file="$CONFIG_DIR/$peer_name/$peer_name.png"
    
    if [ ! -f "$conf_file" ]; then
        echo "${YELLOW}Erreur: Client $peer_name introuvable${NC}"
        exit 1
    fi
    
    echo "${BLUE}=== QR Code pour $peer_name ===${NC}"
    echo ""
    
    # Vérifier si qrencode est installé
    if command -v qrencode >/dev/null 2>&1; then
        qrencode -t ansiutf8 < "$conf_file"
    else
        echo "${YELLOW}qrencode n'est pas installé.${NC}"
        echo "Pour l'installer sur Alpine: apk add qrencode"
        echo ""
        echo "QR code PNG disponible à: $png_file"
        echo ""
        echo "Ou scannez le QR code depuis les logs:"
        echo "docker service logs wireguard_wireguard 2>&1 | grep -A 50 '$peer_name'"
    fi
}

# Fonction pour exporter un client
export_client() {
    peer_name="$1"
    output_dir="${2:-.}"
    
    if [ -z "$peer_name" ]; then
        echo "${YELLOW}Usage: $0 export <peer_name> [output_dir]${NC}"
        echo "Exemple: $0 export peer1 /tmp"
        exit 1
    fi
    
    conf_file="$CONFIG_DIR/$peer_name/$peer_name.conf"
    png_file="$CONFIG_DIR/$peer_name/$peer_name.png"
    
    if [ ! -f "$conf_file" ]; then
        echo "${YELLOW}Erreur: Client $peer_name introuvable${NC}"
        exit 1
    fi
    
    mkdir -p "$output_dir"
    
    cp "$conf_file" "$output_dir/"
    if [ -f "$png_file" ]; then
        cp "$png_file" "$output_dir/"
    fi
    
    echo "${GREEN}✓${NC} Client exporté vers: $output_dir"
    echo "  - $output_dir/$peer_name.conf"
    [ -f "$png_file" ] && echo "  - $output_dir/$peer_name.png"
}

# Fonction pour afficher tous les QR codes
show_all_qr() {
    echo "${BLUE}=== QR Codes de tous les clients ===${NC}"
    echo ""
    
    for peer_dir in "$CONFIG_DIR"/peer*; do
        if [ -d "$peer_dir" ]; then
            peer_name=$(basename "$peer_dir")
            conf_file="$peer_dir/$peer_name.conf"
            
            if [ -f "$conf_file" ]; then
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                echo "${GREEN}$peer_name${NC}"
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                
                if command -v qrencode >/dev/null 2>&1; then
                    qrencode -t ansiutf8 < "$conf_file"
                else
                    echo "QR PNG: $peer_dir/$peer_name.png"
                fi
                
                echo ""
            fi
        fi
    done
    
    if ! command -v qrencode >/dev/null 2>&1; then
        echo "${YELLOW}Astuce: Installez qrencode pour afficher les QR codes dans le terminal${NC}"
        echo "apk add qrencode"
    fi
}

# Fonction pour afficher les clients connectés
show_connected() {
    echo "${BLUE}=== Clients actuellement connectés ===${NC}"
    echo ""
    
    if ! docker ps -q -f name=wireguard >/dev/null 2>&1; then
        echo "${YELLOW}Le container WireGuard n'est pas en cours d'exécution${NC}"
        exit 1
    fi
    
    docker exec $(docker ps -q -f name=wireguard) wg show
}

# Menu principal
case "${1:-help}" in
    list)
        list_clients
        ;;
    
    show)
        show_client "$2"
        ;;
    
    qr)
        if [ -z "$2" ]; then
            show_all_qr
        else
            show_qr "$2"
        fi
        ;;
    
    export)
        export_client "$2" "$3"
        ;;
    
    connected|status)
        show_connected
        ;;
    
    help|--help|-h|*)
        echo "Usage: $0 <commande> [options]"
        echo ""
        echo "Commandes disponibles:"
        echo "  list              - Liste tous les clients disponibles"
        echo "  show <peer>       - Affiche la configuration d'un client"
        echo "  qr [peer]         - Affiche le QR code (tous ou un spécifique)"
        echo "  export <peer> [dir] - Exporte la config vers un répertoire"
        echo "  connected         - Affiche les clients actuellement connectés"
        echo ""
        echo "Exemples:"
        echo "  $0 list"
        echo "  $0 show peer1"
        echo "  $0 qr peer1"
        echo "  $0 qr              # Tous les QR codes"
        echo "  $0 export peer1 /tmp"
        echo "  $0 connected"
        exit 0
        ;;
esac

