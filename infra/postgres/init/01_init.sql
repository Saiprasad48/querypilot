-- Runs once, on first container start, connected to the "warehouse" database as qp_admin.

-- 1. Extensions and schemas for the warehouse
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS raw;      -- untouched CSV loads
CREATE SCHEMA IF NOT EXISTS staging;  -- dbt cleaned views
CREATE SCHEMA IF NOT EXISTS marts;    -- dbt final tables the agent can query
CREATE SCHEMA IF NOT EXISTS meta;     -- schema embeddings and metric metadata

-- 2. Read only role for the agent (LOCAL DEV password only; production uses a secret)
CREATE ROLE qp_reader LOGIN PASSWORD 'reader_local_pw';
GRANT CONNECT ON DATABASE warehouse TO qp_reader;
GRANT USAGE ON SCHEMA marts, meta TO qp_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA marts, meta TO qp_reader;

-- Tables dbt creates later (owned by qp_admin) become readable automatically
ALTER DEFAULT PRIVILEGES FOR ROLE qp_admin IN SCHEMA marts GRANT SELECT ON TABLES TO qp_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE qp_admin IN SCHEMA meta  GRANT SELECT ON TABLES TO qp_reader;

-- Safety limits applied to every qp_reader session
ALTER ROLE qp_reader SET statement_timeout = '5s';
ALTER ROLE qp_reader SET default_transaction_read_only = on;
ALTER ROLE qp_reader SET search_path = marts;

-- 3. Separate application database (chats, runs, evals)
CREATE DATABASE app;
REVOKE CONNECT ON DATABASE app FROM PUBLIC;

\connect app
CREATE EXTENSION IF NOT EXISTS vector;