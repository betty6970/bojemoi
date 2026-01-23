#!/bin/bash


DIR="/opt/bojemoi"

docker stack deploy -c "$DIR/stack/01-service-hl.yml" base
sleep 60
docker stack deploy -c "$DIR/stack/40-service-borodino.yml" borodino
