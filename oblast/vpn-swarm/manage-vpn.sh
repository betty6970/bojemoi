#!/bin/sh

STACK_NAME="vpn-app"

case "$1" in
    deploy)
        echo "� Déploiement de la stack VPN..."
        docker stack deploy -c docker-stack-vpn-with-configs.yml $STACK_NAME
        ;;
    
    remove)
        echo "�️ Suppression de la stack VPN..."
        docker stack rm $STACK_NAME
        ;;
    
    status)
        echo "� Statut des services VPN:"
        docker stack services $STACK_NAME
        echo ""
        echo "� Logs du VPN Gateway:"
        docker service logs --tail 20 ${STACK_NAME}_vpn-gateway
        ;;
    
    logs)
        service_name=${2:-vpn-gateway}
        echo "� Logs du service $service_name:"
        docker service logs -f ${STACK_NAME}_${service_name}
        ;;
    
    scale)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "Usage: $0 scale <service> <replicas>"
            echo "Exemple: $0 scale web-app 5"
            exit 1
        fi
        echo "⚖️ Scaling du service $2 à $3 replicas..."
        docker service scale ${STACK_NAME}_$2=$3
        ;;
    
    ip)
        echo "� Vérification de l'IP publique via VPN:"
        docker exec $(docker ps -q -f name=${STACK_NAME}_vpn-gateway) \
            curl -s https://ipinfo.io/json 
        ;;
    
    health)
        echo "� Vérification de santé du VPN:"
        docker exec $(docker ps -q -f name=${STACK_NAME}_vpn-gateway) \
            /healthcheck.sh
        ;;
    
    restart-vpn)
        echo "� Redémarrage du service VPN..."
        docker service update --force ${STACK_NAME}_vpn-gateway
        ;;
    
    update)
        echo "� Mise à jour de la stack..."
        docker stack deploy -c docker-stack-vpn.yml $STACK_NAME
        ;;
    
    monitor)
        echo "� Monitoring en temps réel..."
        watch -n 10 "
            echo '=== Services Status ==='
            docker stack services $STACK_NAME
            echo ''
            echo '=== VPN IP ==='
            docker exec \$(docker ps -q -f name=${STACK_NAME}_vpn-gateway) curl -s https://ipinfo.io/ip 2>/dev/null || echo 'N/A'
            echo ''
            echo '=== VPN Interface ==='
            docker exec \$(docker ps -q -f name=${STACK_NAME}_vpn-gateway) ip addr show tun0 2>/dev/null | grep inet || echo 'VPN déconnecté'
        "
        ;;
    
    backup-config)
        echo "� Sauvegarde de la configuration..."
        backup_dir="backup-$(date +%Y%m%d-%H%M%S)"
        mkdir -p $backup_dir
        cp -r secrets config $backup_dir/
        tar -czf ${backup_dir}.tar.gz $backup_dir
        rm -rf $backup_dir
        echo "✅ Sauvegarde créée: ${backup_dir}.tar.gz"
        ;;
    
    *)
        echo "Usage: $0 {deploy|remove|status|logs|scale|ip|health|restart-vpn|update|monitor|backup-config}"
        echo ""
        echo "Commandes disponibles:"
        echo "  deploy        - Déployer la stack VPN"
        echo "  remove        - Supprimer la stack VPN"
        echo "  status        - Afficher le statut des services"
        echo "  logs [service]- Afficher les logs (défaut: vpn-gateway)"
        echo "  scale <svc> <n> - Scaler un service"
        echo "  ip            - Vérifier l'IP publique via VPN"
        echo "  health        - Test de santé du VPN"
        echo "  restart-vpn   - Redémarrer le service VPN"
        echo "  update        - Mettre à jour la stack"
        echo "  monitor       - Monitoring temps réel"
        echo "  backup-config - Sauvegarder la configuration"
        exit 1
        ;;
esac
