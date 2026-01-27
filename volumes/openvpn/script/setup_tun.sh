#!/bin/ash
# setup-vm-routing.sh

# Créer un bridge pour Docker qui utilise automatiquement le VPN
docker network create --driver bridge \
  --subnet=172.30.0.0/16 \
  --gateway=172.30.0.1 \
  --opt "com.docker.network.bridge.name"="vpn-bridge" \
  vpn-net

# Router tout le trafic du bridge Docker vers le VPN
ip route add 172.30.0.0/16 via 10.8.0.1 dev tun0
iptables -t nat -A POSTROUTING -s 172.30.0.0/16 -o tun0 -j MASQUERADE

# Bloquer l'accès direct à Internet (optionnel)
iptables -A FORWARD -s 172.30.0.0/16 -o eth0 -j DROP

