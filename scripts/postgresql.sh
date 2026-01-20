docker run --name postgres-container \
  -e POSTGRES_PASSWORD=bojemoi \
  -e POSTGRES_DB=podtgres \
  -e POSTGRES_USER=postgres \
  -p 5432:5432 \
  -v bojemoi:/var/lib/postgresql/data \
  -d postgres:latest
