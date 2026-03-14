-- Bojemoi Lab — Sentinel
-- Script 01 : Création base de données + utilisateur
-- À exécuter en tant que superuser (postgres) sur le serveur PostgreSQL

-- Créer l'utilisateur sentinel (si inexistant)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sentinel') THEN
    CREATE USER sentinel WITH ENCRYPTED PASSWORD 'CHANGE_ME';
  END IF;
END
$$;

-- Créer la base de données
CREATE DATABASE sentinel
  OWNER sentinel
  ENCODING 'UTF8'
  LC_COLLATE 'en_US.UTF-8'
  LC_CTYPE 'en_US.UTF-8'
  TEMPLATE template0;

-- Donner tous les droits sur la base
GRANT ALL PRIVILEGES ON DATABASE sentinel TO sentinel;

-- Se connecter à la base pour finir les grants
\c sentinel

GRANT ALL ON SCHEMA public TO sentinel;
