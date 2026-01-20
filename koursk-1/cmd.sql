-- 1. Se connecter en tant que superutilisateur PostgreSQL
-- psql -U postgres

-- 2. Arrêter Grafana avant de manipuler la base de données
-- sudo systemctl stop grafana-server

-- 3. Sauvegarder la base existante (optionnel mais recommandé)
-- pg_dump -U postgres -h localhost grafana > grafana_backup_$(date +%Y%m%d_%H%M%S).sql

-- 4. Terminer toutes les connexions actives à la base Grafana
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'grafana' AND pid <> pg_backend_pid();

-- 5. Supprimer la base de données existante
DROP DATABASE IF EXISTS grafana;

-- 6. Supprimer l'utilisateur Grafana (si vous voulez le recréer)
DROP USER IF EXISTS grafana;

-- 7. Recréer l'utilisateur Grafana avec un mot de passe sécurisé
CREATE USER grafana WITH PASSWORD 'grafana';

-- 8. Créer la nouvelle base de données
CREATE DATABASE grafana
    WITH OWNER = postgres 
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE = template0;

-- 9. Accorder tous les privilèges sur la base à l'utilisateur grafana
GRANT ALL PRIVILEGES ON DATABASE grafana TO grafana;

-- 10. Se connecter à la base grafana pour configurer les permissions
\c grafana;

-- 11. Accorder les privilèges sur le schéma public
GRANT ALL ON SCHEMA public TO grafana;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO grafana;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO grafana;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO grafana;

-- 12. Configurer les privilèges par défaut pour les futurs objets
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO grafana;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO grafana;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO grafana;

-- 13. Optionnel: Créer une extension si nécessaire (pour certaines fonctionnalités)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 14. Vérifier la création
\l grafana
\du grafana

-- =====================================
-- ALTERNATIVE: SUPPRIMER SEULEMENT LES TABLES
-- (Si vous ne voulez pas supprimer toute la base)
-- =====================================

-- 1. Se connecter à la base grafana
-- \c grafana;

-- 2. Lister toutes les tables Grafana
-- \dt

-- 3. Supprimer toutes les tables Grafana une par une
-- DROP TABLE IF EXISTS migration_log CASCADE;
-- DROP TABLE IF EXISTS user CASCADE;
-- DROP TABLE IF EXISTS user_auth CASCADE;
-- DROP TABLE IF EXISTS temp_user CASCADE;
-- DROP TABLE IF EXISTS org CASCADE;
-- DROP TABLE IF EXISTS org_user CASCADE;
-- DROP TABLE IF EXISTS team CASCADE;
-- DROP TABLE IF EXISTS team_member CASCADE;
-- DROP TABLE IF EXISTS dashboard CASCADE;
-- DROP TABLE IF EXISTS dashboard_version CASCADE;
-- DROP TABLE IF EXISTS dashboard_tag CASCADE;
-- DROP TABLE IF EXISTS dashboard_acl CASCADE;
-- DROP TABLE IF EXISTS data_source CASCADE;
-- DROP TABLE IF EXISTS api_key CASCADE;
-- DROP TABLE IF EXISTS user_auth_token CASCADE;
-- DROP TABLE IF EXISTS server_lock CASCADE;
-- DROP TABLE IF EXISTS user_role CASCADE;
-- DROP TABLE IF EXISTS role CASCADE;
-- DROP TABLE IF EXISTS builtin_role CASCADE;
-- DROP TABLE IF EXISTS permission CASCADE;
-- DROP TABLE IF EXISTS alert CASCADE;
-- DROP TABLE IF EXISTS alert_notification CASCADE;
-- DROP TABLE IF EXISTS alert_notification_state CASCADE;
-- DROP TABLE IF EXISTS annotation CASCADE;
-- DROP TABLE IF EXISTS annotation_tag CASCADE;
-- DROP TABLE IF EXISTS test_data CASCADE;
-- DROP TABLE IF EXISTS plugin_setting CASCADE;
-- DROP TABLE IF EXISTS session CASCADE;
-- DROP TABLE IF EXISTS playlist CASCADE;
-- DROP TABLE IF EXISTS playlist_item CASCADE;
-- DROP TABLE IF EXISTS preferences CASCADE;
-- DROP TABLE IF EXISTS alert_rule CASCADE;
-- DROP TABLE IF EXISTS alert_rule_version CASCADE;
-- DROP TABLE IF EXISTS alert_instance CASCADE;
-- DROP TABLE IF EXISTS alert_configuration CASCADE;
-- DROP TABLE IF EXISTS ngalert_configuration CASCADE;
-- DROP TABLE IF EXISTS provenance_type CASCADE;
-- DROP TABLE IF EXISTS alert_image CASCADE;
-- DROP TABLE IF EXISTS library_element CASCADE;
-- DROP TABLE IF EXISTS library_element_connection CASCADE;
-- DROP TABLE IF EXISTS folder CASCADE;
-- DROP TABLE IF EXISTS folder_acl CASCADE;
-- DROP TABLE IF EXISTS dashboard_public CASCADE;
-- DROP TABLE IF EXISTS query_history CASCADE;
-- DROP TABLE IF EXISTS short_url CASCADE;
-- DROP TABLE IF EXISTS tag CASCADE;
-- DROP TABLE IF EXISTS login_attempt CASCADE;
-- DROP TABLE IF EXISTS user_stats CASCADE;
-- DROP TABLE IF EXISTS admin_stats CASCADE;
-- DROP TABLE IF EXISTS system_stats CASCADE;
-- DROP TABLE IF EXISTS quota CASCADE;
-- DROP TABLE IF EXISTS cache_data CASCADE;
-- DROP TABLE IF EXISTS kv_store CASCADE;
-- DROP TABLE IF EXISTS secrets CASCADE;
-- DROP TABLE IF EXISTS correlation CASCADE;

-- 4. Supprimer toutes les tables en une seule commande (plus efficace)
-- DO $$ 
-- DECLARE 
--     r RECORD;
-- BEGIN
--     FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') 
--     LOOP
--         EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
--     END LOOP;
-- END $$;

-- 5. Supprimer toutes les séquences
-- DO $$ 
-- DECLARE 
--     r RECORD;
-- BEGIN
--     FOR r IN (SELECT sequencename FROM pg_sequences WHERE schemaname = 'public') 
--     LOOP
--         EXECUTE 'DROP SEQUENCE IF EXISTS ' || quote_ident(r.sequencename) || ' CASCADE';
--     END LOOP;
-- END $$;

-- 6. Vérifier que toutes les tables ont été supprimées
-- \dt

-- 7. Redémarrer Grafana pour recréer les tables
-- sudo systemctl restart grafana-server
