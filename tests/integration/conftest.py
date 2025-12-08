"""
Conftest for integration tests.
Imports fixtures from parent conftest.
"""

from __future__ import annotations

import sys
import os
import pytest
from flask import Flask
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import fixtures from parent conftest
from tests.conftest import (
    basex_available,
    test_db_name,
    basex_test_connector,
    dict_service_with_db,
    flask_test_server,
)


@pytest.fixture(scope="session")
def postgres_available() -> bool:
    """Check if PostgreSQL server is configured (not if it's available locally)."""
    return bool(os.getenv('POSTGRES_HOST'))


@pytest.fixture
def app() -> Flask:
    """Create Flask application for integration tests."""
    from app import create_app
    import psycopg2.pool
    from app.database.workset_db import create_workset_tables
    
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    
    # Create application context
    with app.app_context():
        from app.models.project_settings import db
        db.create_all()
        
        # Initialize PostgreSQL pool for workset tests
        # The main app skips this in TESTING mode, but integration tests need it
        postgres_configured = bool(os.getenv('POSTGRES_HOST'))
        if app.pg_pool is None and postgres_configured:
            try:
                pg_pool = psycopg2.pool.SimpleConnectionPool(
                    1, 20,
                    user=app.config.get("PG_USER"),
                    password=app.config.get("PG_PASSWORD"),
                    host=app.config.get("PG_HOST"),
                    port=app.config.get("PG_PORT"),
                    database=app.config.get("PG_DATABASE"),
                    connect_timeout=3
                )
                app.pg_pool = pg_pool
                create_workset_tables(pg_pool)
            except Exception as e:
                app.logger.warning(f"Failed to initialize PostgreSQL pool for tests: {e}")
                app.pg_pool = None
    
    return app


@pytest.fixture
def client(app: Flask):
    """Create Flask test client."""
    return app.test_client()


__all__ = [
    'basex_available',
    'test_db_name',
    'basex_test_connector',
    'dict_service_with_db',
    'flask_test_server',
    'postgres_available',
    'app',
    'client',
]
