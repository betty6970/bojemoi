#!/bin/bash


DIR="/opt/bojemoi"

docker stack deploy -c "${DIR}_boot/stack/01-boot-service.yml" boot
sleep 15
docker stack deploy -c "$DIR/stack/01-service-hl.yml" base
sleep 15
docker stack deploy -c "$DIR/stack/40-service-borodino.yml" borodino
sleep 15
docker stack deploy -c "${DIR}-telegram/telegram/stack/60-service-telegram.yml" telegram
docker service ls
