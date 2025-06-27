-- PostgreSQL setup script for Dictionary Analytics testing
-- Run this as postgres superuser

-- Create test user
DROP USER IF EXISTS dict_user;
CREATE USER dict_user WITH PASSWORD 'dict_pass';

-- Create databases
DROP DATABASE IF EXISTS dictionary_analytics;
DROP DATABASE IF EXISTS dictionary_test;

CREATE DATABASE dictionary_analytics 
    WITH OWNER dict_user 
    ENCODING 'UTF8' 
    LC_COLLATE = 'en_US.UTF-8' 
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE template0;

CREATE DATABASE dictionary_test 
    WITH OWNER dict_user 
    ENCODING 'UTF8' 
    LC_COLLATE = 'en_US.UTF-8' 
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE template0;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE dictionary_analytics TO dict_user;
GRANT ALL PRIVILEGES ON DATABASE dictionary_test TO dict_user;

-- Connect to each database and set up extensions
\c dictionary_analytics
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
GRANT ALL ON SCHEMA public TO dict_user;

\c dictionary_test
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
GRANT ALL ON SCHEMA public TO dict_user;

-- Display confirmation
\c postgres
SELECT 'Database setup completed successfully!' AS status;
