-- PostgreSQL initialization script for dictionary analytics
-- This script sets up the database for development and testing

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create development schema
CREATE SCHEMA IF NOT EXISTS dictionary;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS corpus;

-- Grant permissions to dictionary user
GRANT ALL PRIVILEGES ON SCHEMA dictionary TO dict_user;
GRANT ALL PRIVILEGES ON SCHEMA analytics TO dict_user;
GRANT ALL PRIVILEGES ON SCHEMA corpus TO dict_user;

-- Set default search path
ALTER USER dict_user SET search_path = dictionary, analytics, corpus, public;

-- Create indexes for performance
-- Note: Actual tables will be created by the migration script or application
