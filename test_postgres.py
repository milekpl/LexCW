#!/usr/bin/env python3
"""Minimal test to isolate the encoding issue."""

import logging
from app.database.postgresql_connector import PostgreSQLConnector, PostgreSQLConfig

def test_postgres():
    """Test PostgreSQL connection."""
    try:
        print("Testing PostgreSQL connection...")
        
        postgres_config = PostgreSQLConfig(
            host='localhost',
            port=5432,
            database='para_crawl',
            username='postgres',
            password='dict_pass'
        )
        
        connector = PostgreSQLConnector(postgres_config)
        
        print("✓ Connector created")
        
        # Test database creation
        db_created = connector.ensure_database_exists()
        print(f"✓ Database creation: {db_created}")
        
        # Test simple query
        result = connector.fetch_one("SELECT version()")
        print(f"✓ PostgreSQL version: {result}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Disable logging to isolate encoding issues
    logging.getLogger().setLevel(logging.CRITICAL)
    test_postgres()
