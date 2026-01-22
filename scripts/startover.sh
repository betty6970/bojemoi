#!/bin/bash


DIR="/opt/bojemoi"

docker stack deploy -c "$DIR/stack/01-service-hl.yml" base
sleep 60
docker stack deploy -c "$DIR/stack/10-service-oblast.yml" zap 
sleep 60
#docker stack deploy -c "$DIR/stack/11-service-zaproxy.yml"
#sleep 60
docker stack deploy -c "$DIR/stack/20-service-kyiv.yml" burp
sleep 60
docker stack deploy -c "$DIR/stack/50-service-borodino.yml" armement
sleep 60
docker stack deploy -c "$DIR/stack/50-service-tsushima.yml" masscan
sleep 60
docker stack deploy -c "$DIR/stack/55-service-nuclei.yml" nuclei
sleep 60
docker stack deploy -c "$DIR/stack/56-service-vulnx.yml" vulnx
sleep 60
docker stack deploy -c "$DIR/stack/60-service-samsonov.yml" samsonov
sleep 60
docker stack deploy -c "$DIR/stack/70-service-zarovnik.yml" gitlab
