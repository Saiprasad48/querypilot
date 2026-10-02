-- App role: owns application data (chats, checkpoints, eval runs) in the "app" database.
-- It has no access to warehouse tables. LOCAL DEV password only.
CREATE ROLE qp_app LOGIN PASSWORD 'app_local_pw';
GRANT CONNECT ON DATABASE app TO qp_app;

-- Only roles that were explicitly granted may connect to the warehouse.
REVOKE CONNECT ON DATABASE warehouse FROM PUBLIC;

\connect app
GRANT USAGE, CREATE ON SCHEMA public TO qp_app;