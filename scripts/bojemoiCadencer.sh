#!/bin/ash
# wget http://bojemoi.me/docker/bojemoiCadencer.sh -O -| ash

if [ -z "$1" ]; then
    commande=$1
else
    echo "Argument reçu : $1"
    commande=$1
fi

su - root -c "apk add py3-docker-py py3-psutil"
cd $HOME
FILENAME="docker_memory_scheduler.py"

wget http://bojemoi.me/docker/usr/local/bin/bojemoi/$FILENAME -O /$HOME/$FILENAME
docker system prune -f
docker volume prune -f
python /$HOME/$FILENAME $commande

