# Runbook — Renouvellement certificats PostgreSQL SSL

## Fichiers concernés

```
volumes/postgres/ssl/
├── ca.crt / ca.key / ca.srl   # CA interne du lab
├── server.crt / server.key    # Certificat serveur postgres
└── client-postgres.crt/.key   # Certificat client (mTLS)
```

> Ces fichiers sont dans `.gitignore` — ne jamais committer les clés privées.

## Générer de nouveaux certificats (CA interne)

```bash
cd /opt/bojemoi/volumes/postgres/ssl

# Regénérer la CA (si expirée)
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
  -subj "/CN=BojemoiLab-CA/O=Bojemoi/C=FR"

# Certificat serveur
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
  -subj "/CN=postgres/O=Bojemoi/C=FR"
openssl x509 -req -days 3650 -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt
chmod 600 server.key

# Certificat client
openssl genrsa -out client-postgres.key 2048
openssl req -new -key client-postgres.key -out client.csr \
  -subj "/CN=postgres-client/O=Bojemoi/C=FR"
openssl x509 -req -days 3650 -in client.csr -CA ca.crt -CAkey ca.key \
  -CAserial ca.srl -out client-postgres.crt
```

## Mettre à jour le secret Docker

Le secret `postgres_ssl_key` contient `server.key`. Si renouvellement :

```bash
# Voir runbook docker-secrets.md pour la procédure complète
docker service rm base_postgres
docker secret rm postgres_ssl_key postgres_ssl_cert postgres_ssl_ca
docker secret create postgres_ssl_key volumes/postgres/ssl/server.key
docker secret create postgres_ssl_cert volumes/postgres/ssl/server.crt
docker secret create postgres_ssl_ca volumes/postgres/ssl/ca.crt
# Puis redéployer le stack base
```
