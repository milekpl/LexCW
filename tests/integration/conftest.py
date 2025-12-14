"""
Conftest for integration tests.
Imports fixtures from parent conftest.
"""

from __future__ import annotations

import sys
import os
import pytest
from flask import Flask
from flask.testing import FlaskClient
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import fixtures from parent conftest - use relative import
parent_conftest_path = os.path.join(os.path.dirname(__file__), '..', 'conftest.py')
import importlib.util
spec = importlib.util.spec_from_file_location("parent_conftest", parent_conftest_path)
parent_conftest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent_conftest)

basex_available = parent_conftest.basex_available
test_db_name = parent_conftest.test_db_name
basex_test_connector = parent_conftest.basex_test_connector
dict_service_with_db = parent_conftest.dict_service_with_db
flask_test_server = parent_conftest.flask_test_server


@pytest.fixture(scope="session")
def postgres_available() -> bool:
    """Check if PostgreSQL server is configured (not if it's available locally)."""
    return bool(os.getenv('POSTGRES_HOST'))


@pytest.fixture(scope="session")
def app() -> Flask:
    """Create Flask application for integration tests (session-scoped for persistence)."""
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


@pytest.fixture(scope="function")
def client(app: Flask):
    """Create Flask test client (function-scoped for fresh context per test)."""
    with app.app_context():
        yield app.test_client()


@pytest.fixture(autouse=True)
def ensure_recommended_ranges(client: FlaskClient) -> None:
    """Ensure recommended ranges are installed before each integration test."""
    # Call the install endpoint to ensure ranges exist for tests that depend on them
    try:
        client.post('/api/ranges/install_recommended')
    except Exception:
        # If the endpoint is unavailable for some tests, ignore
        pass


@pytest.fixture(scope="function", autouse=True)
def app_context(app: Flask):
    """Provide application context for each test (autouse, function-scoped)."""
    with app.app_context():
        from app.models.project_settings import db
        db.session.rollback()  # Clean up any previous transactions
        yield app
        db.session.rollback()  # Clean up after test


@pytest.fixture(scope="session", autouse=True)
def cleanup_display_profiles():
    """Clean up display profile storage before and after test session."""
    from pathlib import Path
    import tempfile
    
    # Use a common instance path pattern
    instance_path = Path(tempfile.gettempdir()) / "flask_test_instance"
    storage_path = instance_path / "display_profiles.json"
    
    # Clean up before tests
    if storage_path.exists():
        storage_path.unlink()
    
    yield
    
    # Clean up after tests
    if storage_path.exists():
        storage_path.unlink()


@pytest.fixture
def cleanup_profile_db(app: Flask):
    """Clean up display profiles from database before each test.
    
    This fixture is NOT autouse - tests that need it should explicitly request it.
    """
    with app.app_context():
        from app.models.display_profile import DisplayProfile, ProfileElement
        from app.models.project_settings import db
        
        # Clear all elements first (foreign key dependencies)
        try:
            ProfileElement.query.delete()
            db.session.commit()
            
            # Clear all profiles
            DisplayProfile.query.delete()
            db.session.commit()
        except Exception:
            # If tables don't exist or app doesn't have proper DB, skip cleanup
            pass
        
        yield
        
        # Clean up after test
        try:
            ProfileElement.query.delete()
            db.session.commit()
            
            DisplayProfile.query.delete()
            db.session.commit()
        except Exception:
            pass


@pytest.fixture
def sample_entry_xml() -> str:
    """Sample LIFT XML entry for preview tests."""
    return """
    <entry id="test-entry-1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <pronunciation>
            <form lang="en-fonipa"><text>tɛst</text></form>
        </pronunciation>
        <sense id="sense-1">
            <grammatical-info value="Noun"/>
            <definition>
                <form lang="en"><text>A procedure for testing something</text></form>
            </definition>
        </sense>
    </entry>
    """


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
