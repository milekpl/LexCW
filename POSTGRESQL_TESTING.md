"""
PostgreSQL Integration Testing Guide

This document explains how to run PostgreSQL integration tests with real
database connections for comprehensive testing coverage.
"""

# PostgreSQL Integration Testing

## Overview

The PostgreSQL integration tests validate:
- Real database connections and schema creation
- Data migration from SQLite to PostgreSQL
- Performance with large datasets
- Advanced features like full-text search and JSONB operations
- Error handling and transaction integrity

## Setup Options

### Option 1: Docker Compose (Recommended)

1. **Start PostgreSQL test container:**
   ```bash
   docker-compose up postgres_test -d
   ```

2. **Verify container is running:**
   ```bash
   docker ps | grep postgres_test
   ```

3. **Run integration tests:**
   ```bash
   # Set environment for Docker PostgreSQL
   $env:POSTGRES_HOST="localhost"
   $env:POSTGRES_PORT="5433"
   $env:POSTGRES_DB="dictionary_test"
   $env:POSTGRES_USER="dict_user" 
   $env:POSTGRES_PASSWORD="dict_pass"
   
   # Run the tests
   pytest tests/test_postgresql_real_integration.py -v --tb=short
   pytest tests/test_migration_real_integration.py -v --tb=short
   ```

### Option 2: Local PostgreSQL Installation

1. **Install PostgreSQL locally (Windows):**
   - Download from: https://www.postgresql.org/download/windows/
   - Install with default settings
   - Remember the password for postgres user

2. **Create test database:**
   ```sql
   -- Connect as postgres user
   CREATE USER dict_user WITH PASSWORD 'dict_pass';
   CREATE DATABASE dictionary_test OWNER dict_user;
   GRANT ALL PRIVILEGES ON DATABASE dictionary_test TO dict_user;
   ```

3. **Set environment variables:**
   ```powershell
   $env:POSTGRES_HOST="localhost"
   $env:POSTGRES_PORT="5432"
   $env:POSTGRES_DB="dictionary_test"
   $env:POSTGRES_USER="dict_user"
   $env:POSTGRES_PASSWORD="dict_pass"
   ```

4. **Run integration tests:**
   ```bash
   pytest tests/test_postgresql_real_integration.py -v
   pytest tests/test_migration_real_integration.py -v
   ```

### Option 3: Remote PostgreSQL (Cloud/Server)

1. **Set environment variables for remote server:**
   ```powershell
   $env:POSTGRES_HOST="your-postgres-server.com"
   $env:POSTGRES_PORT="5432"
   $env:POSTGRES_DB="dictionary_test"
   $env:POSTGRES_USER="your_username"
   $env:POSTGRES_PASSWORD="your_password"
   ```

2. **Run tests:**
   ```bash
   pytest tests/test_postgresql_real_integration.py -v
   pytest tests/test_migration_real_integration.py -v
   ```

## Test Categories

### 1. Connection and Schema Tests
- `test_postgresql_connection()` - Basic connection verification
- `test_create_dictionary_schema()` - Schema creation with proper constraints
- `test_postgresql_schema_creation()` - Advanced schema features

### 2. Migration Tests  
- `test_sqlite_to_postgresql_migration()` - Complete data migration
- `test_migration_with_edge_cases()` - Unicode, special characters, malformed data
- `test_migration_performance()` - Large dataset migration timing

### 3. Advanced Features Tests
- `test_advanced_corpus_features()` - Full-text search, arrays, JSONB
- `test_word_sketch_features()` - Word sketch analytics
- `test_performance_with_large_dataset()` - Performance with 1000+ records

### 4. Error Handling Tests
- `test_migration_error_handling()` - Invalid files, connection failures
- `test_transaction_handling()` - Rollback and consistency

## Performance Benchmarks

The tests include performance assertions:
- Migration: <60 seconds for 500 entries
- Complex queries: <5 seconds on 1000+ records  
- Batch inserts: <10 seconds for 1000 records
- Full-text search: <1 second response time

## Test Data

Tests use realistic data:
- Unicode characters (café, special symbols)
- Complex JSON structures in JSONB fields
- Multi-language content (English/Polish)
- Various grammatical patterns
- Edge cases (NULL values, malformed JSON)

## CI/CD Integration

For continuous integration:

```yaml
# GitHub Actions example
- name: Start PostgreSQL
  run: |
    docker run --name postgres_test -e POSTGRES_PASSWORD=dict_pass -e POSTGRES_USER=dict_user -e POSTGRES_DB=dictionary_test -p 5432:5432 -d postgres:15

- name: Wait for PostgreSQL
  run: |
    until docker exec postgres_test pg_isready -U dict_user -d dictionary_test; do sleep 1; done

- name: Run PostgreSQL integration tests
  env:
    POSTGRES_HOST: localhost
    POSTGRES_PORT: 5432  
    POSTGRES_DB: dictionary_test
    POSTGRES_USER: dict_user
    POSTGRES_PASSWORD: dict_pass
  run: |
    pytest tests/test_postgresql_real_integration.py -v
    pytest tests/test_migration_real_integration.py -v
```

## Troubleshooting

### Common Issues

1. **Connection refused:**
   - Check PostgreSQL is running: `docker ps` or `services.msc`
   - Verify port is not blocked by firewall
   - Check environment variables are set correctly

2. **Authentication failed:**
   - Verify username/password are correct
   - Check pg_hba.conf allows connections (for local install)
   - Ensure user has proper database permissions

3. **Database doesn't exist:**
   - Run setup script: `python setup_postgres_tests.py`
   - Or create manually with psql/pgAdmin

4. **Tests timeout:**
   - Check PostgreSQL performance/resources
   - Reduce test dataset size for slower systems
   - Increase timeout values in test configuration

### Debug Mode

Run tests with detailed output:
```bash
pytest tests/test_postgresql_real_integration.py -v -s --tb=long --log-cli-level=DEBUG
```

## Skipping Integration Tests

If PostgreSQL is not available, tests will automatically skip:
```bash
SKIPPED [1] PostgreSQL not available for integration testing
```

To run only unit tests (no database required):
```bash
pytest tests/ -k "not integration" -v
```

## Expected Coverage

With real PostgreSQL integration tests:
- PostgreSQL connector: 85%+ coverage
- Migration utility: 90%+ coverage  
- Advanced analytics: 80%+ coverage
- Overall project: 90%+ coverage (target)

## Security Notes

- Test databases use non-production credentials
- Always use separate test databases, never production
- Reset/clean test data between test runs
- Use Docker for isolation when possible
