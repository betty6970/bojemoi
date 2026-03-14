-- Bojemoi Lab — Sentinel
-- Script 03 : Grants pour l'utilisateur sentinel
-- À exécuter en tant que superuser (postgres) connecté à la base sentinel

\c sentinel

-- Droits sur les tables existantes
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO sentinel;

-- Droits sur les séquences (SERIAL = auto-increment)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sentinel;

-- Droits sur les futures tables créées par postgres
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sentinel;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO sentinel;
