docker stop postgres-container 
docker rm postgres-container
#docker volume create bojemoi
docker run -d \
  --name postgres-container \
  -e POSTGRES_PASSWORD=bojemoi \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_DB=postgres \
  -p 5432:5432 \
  -v bojemoi:/var/lib/postgresql/ \
  -v /opt/bojemoi/dump:/tmp \
   postgres:latest \
   /usr/lib/postgresql/18/bin/pg_resetwal /var/lib/postgresql/18/docker/ \
   tail -f /dev/null
#  'psql -U postgres < /tmp/dump_complet_serveur.sql '
