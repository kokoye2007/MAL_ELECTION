-- PostgreSQL Initialization Script
-- This runs automatically when the database container starts for the first time

-- Create the election user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'election_user') THEN
        CREATE USER election_user WITH PASSWORD 'election_dev_2025';
    END IF;
END
$$;

-- Create the database if it doesn't exist
-- Note: This runs in the default postgres database, so we need to be careful
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'myanmar_election') THEN
        PERFORM dblink_exec('host=localhost user=postgres dbname=postgres', 
                           'CREATE DATABASE myanmar_election OWNER election_user');
    END IF;
EXCEPTION WHEN OTHERS THEN
    -- Database might already exist or we might not have dblink
    -- This is fine for development
    NULL;
END
$$;

-- Grant necessary privileges
GRANT ALL PRIVILEGES ON DATABASE myanmar_election TO election_user;

-- Connect to the myanmar_election database for the rest of the setup
\c myanmar_election

-- Continue with schema setup (this will be handled by the main schema file)