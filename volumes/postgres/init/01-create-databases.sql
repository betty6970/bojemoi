-- =============================================================================
-- Bojemoi Lab — PostgreSQL initialization
-- Executed once on first container start (docker-entrypoint-initdb.d)
-- =============================================================================

-- Extensions globales
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Metasploit
-- =============================================================================
SELECT 'CREATE DATABASE msf' WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'msf'
)\gexec

-- =============================================================================
-- Grafana
-- =============================================================================
SELECT 'CREATE DATABASE grafana' WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'grafana'
)\gexec

-- =============================================================================
-- IP2Location (géolocalisation CIDRs)
-- =============================================================================
SELECT 'CREATE DATABASE ip2location' WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'ip2location'
)\gexec

-- =============================================================================
-- Karacho (blockchain analytics)
-- =============================================================================
SELECT 'CREATE DATABASE karacho' WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'karacho'
)\gexec

-- =============================================================================
-- ML Threat Intelligence
-- =============================================================================
SELECT 'CREATE DATABASE bojemoi_threat_intel' WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'bojemoi_threat_intel'
)\gexec

-- =============================================================================
-- DefectDojo (vuln management)
-- =============================================================================
SELECT 'CREATE DATABASE defectdojo' WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'defectdojo'
)\gexec

-- =============================================================================
-- Razvedka (CTI)
-- =============================================================================
SELECT 'CREATE DATABASE razvedka' WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'razvedka'
)\gexec

-- =============================================================================
-- Vigie (ANSSI RSS watchlist)
-- =============================================================================
SELECT 'CREATE DATABASE vigie' WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'vigie'
)\gexec

-- =============================================================================
-- Sentinel (IoT/MQTT collector)
-- =============================================================================
SELECT 'CREATE DATABASE sentinel' WHERE NOT EXISTS (
  SELECT FROM pg_database WHERE datname = 'sentinel'
)\gexec

-- =============================================================================
-- Fin
-- =============================================================================
\echo '>>> Bojemoi databases initialized.'
