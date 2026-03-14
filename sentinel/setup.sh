#!/bin/sh
# Bojemoi Lab — Sentinel initial setup
# À exécuter UNE FOIS sur le manager (meta-76)
set -e

echo "=== Sentinel setup ==="

# 1. Réseau IoT overlay
docker network create --driver overlay --attachable iot_network 2>/dev/null || echo "iot_network already exists"

# 2. Secrets MQTT + PostgreSQL
echo "MQTT password sentinel :"
read -s MQTT_PASS
echo "$MQTT_PASS" | docker secret create sentinel_mqtt_pass - 2>/dev/null || echo "secret already exists"

echo "PostgreSQL password sentinel :"
read -s PG_PASS
echo "$PG_PASS" | docker secret create sentinel_pg_pass - 2>/dev/null || echo "secret already exists"

# 3. Créer le fichier de mots de passe Mosquitto
# (à adapter avec mosquitto_passwd ou générer manuellement)
echo "Génération passwd Mosquitto..."
docker run --rm eclipse-mosquitto:2.0 mosquitto_passwd -b -c /tmp/passwd sentinel "$MQTT_PASS"
echo "Copier /tmp/passwd dans le volume mosquitto_config"

# 4. Créer la base de données sentinel dans PostgreSQL
echo "Création DB sentinel..."
POSTGRES_ID=$(docker ps -q --filter "name=base_postgres")
docker exec -i "$POSTGRES_ID" psql -U postgres <<SQL
CREATE DATABASE sentinel;
CREATE USER sentinel WITH ENCRYPTED PASSWORD '$PG_PASS';
GRANT ALL PRIVILEGES ON DATABASE sentinel TO sentinel;
\c sentinel
GRANT ALL ON SCHEMA public TO sentinel;
SQL

# 5. Build + push image collector
echo "Build sentinel-collector..."
cd "$(dirname "$0")/collector"
docker build -t localhost:5000/sentinel-collector:latest .
docker push localhost:5000/sentinel-collector:latest

# 6. Deploy stack
echo "Deploy sentinel stack..."
cd /opt/bojemoi
docker stack deploy -c stack/55-service-sentinel.yml sentinel --prune --resolve-image always

echo "=== Setup done ==="
echo "Vérifier : docker service ls | grep sentinel"
echo "Métriques : curl -4 http://localhost:9101/metrics"
