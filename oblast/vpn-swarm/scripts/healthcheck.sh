#!/bin/sh

# Script de vérification de santé du VPN
check_vpn_health() {
    local exit_code=0
    
    echo "=== Health Check VPN - $(date) ==="
    
    # 1. Vérifier que l'interface tun0 existe
    if ! ip addr show tun0 >/dev/null 2>&1; then
        echo "❌ Interface VPN (tun0) non trouvée"
        exit_code=1
    else
        echo "✅ Interface VPN active"
        ip addr show tun0 | grep inet
    fi
    
    # 2. Vérifier le processus OpenVPN
    if ! pgrep openvpn >/dev/null; then
        echo "❌ Processus OpenVPN non trouvé"
        exit_code=1
    else
        echo "✅ OpenVPN actif (PID: $(pgrep openvpn))"
    fi
    
    # 3. Test de connectivité via VPN
    if ! curl -s --max-time 10 --interface tun0 https://ipinfo.io/ip >/dev/null 2>&1; then
        echo "❌ Pas de connectivité via VPN"
        exit_code=1
    else
        local vpn_ip=$(curl -s --max-time 5 --interface tun0 https://ipinfo.io/ip 2>/dev/null)
        echo "✅ Connectivité VPN OK - IP: $vpn_ip"
    fi
    
    # 4. Vérifier les DNS
    if ! nslookup google.com >/dev/null 2>&1; then
        echo "❌ Résolution DNS échouée"
        exit_code=1
    else
        echo "✅ DNS fonctionnel"
    fi
    
    # 5. Vérifier les routes
    if ! ip route | grep -q "default dev tun0"; then
        echo "❌ Route par défaut via VPN manquante"
        exit_code=1
    else
        echo "✅ Route par défaut via VPN configurée"
    fi
    
    return $exit_code
}

# Exécuter le check
if check_vpn_health; then
    echo "✅ VPN Health Check: OK"
    exit 0
else
    echo "❌ VPN Health Check: FAILED"
    exit 1
fi

