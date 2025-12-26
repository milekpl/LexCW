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
# Override test_db_name to use the session DB for integration tests
# test_db_name = parent_conftest.test_db_name
# Override basex_test_connector to use the session DB without creating/dropping it
# basex_test_connector = parent_conftest.basex_test_connector
dict_service_with_db = parent_conftest.dict_service_with_db
flask_test_server = parent_conftest.flask_test_server

@pytest.fixture(scope="function")
def test_db_name() -> str:
    """Return the shared test database name for integration tests."""
    return os.environ.get('TEST_DB_NAME') or f"test_{importlib.util.sys.modules['uuid'].uuid4().hex[:8]}"

# Ensure TEST_DB_NAME is set early (at import time) so tests that call
# create_app('testing') at module import get the correct DB. This mirrors
# the behavior of the session-scoped fixture but runs earlier to cover
# test modules that instantiate the app at import time.
if os.environ.get('TEST_DB_NAME') is None:
    try:
        import uuid
        from tests.basex_test_utils import create_test_db

        test_db = f"test_{uuid.uuid4().hex[:8]}"
        os.environ['TEST_DB_NAME'] = test_db
        os.environ['BASEX_DATABASE'] = test_db

        # Try to create the DB (best-effort)
        create_test_db(test_db)
    except Exception:
        # If BaseX isn't available here, don't fail import; the session fixture
        # will skip tests or attempt to create a DB later.
        pass


@pytest.fixture(scope="session")
def postgres_available() -> bool:
    """Check if PostgreSQL server is configured (not if it's available locally)."""
    return bool(os.getenv('POSTGRES_HOST'))


@pytest.fixture(scope="session", autouse=True)
def ensure_basex_test_database() -> None:
    """Ensure a single BaseX test database exists for the integration session.

    Uses the shared utilities to create and drop the DB. Sets both
    `TEST_DB_NAME` and `BASEX_DATABASE` environment variables so the Flask
    app and the DB utilities use the same name consistently.
    """
    import uuid
    from tests.basex_test_utils import create_test_db, drop_test_db

    # Check BaseX availability by attempting a short connection
    from app.database.basex_connector import BaseXConnector
    try:
        admin_check = BaseXConnector(
            host=os.getenv('BASEX_HOST', 'localhost'),
            port=int(os.getenv('BASEX_PORT', '1984')),
            username=os.getenv('BASEX_USERNAME', 'admin'),
            password=os.getenv('BASEX_PASSWORD', 'admin'),
            database=None
        )
        admin_check.connect()
        admin_check.disconnect()
    except Exception as e:
        pytest.skip(f"BaseX server not available: {e}")

    # Use provided TEST_DB_NAME if present (useful for CI), otherwise generate one
    test_db = os.environ.get('TEST_DB_NAME') or f"test_{uuid.uuid4().hex[:8]}"

    # Set env vars so app and utilities see the same DB
    os.environ['TEST_DB_NAME'] = test_db
    os.environ['BASEX_DATABASE'] = test_db

    # Create the DB using helper (best-effort, logs failures)
    create_test_db(test_db)

    yield

    # Teardown: drop test DB (best-effort)
    drop_test_db(test_db)


@pytest.fixture(autouse=True)
def check_db_config_matches_env(app: Flask):
    """Ensure that the Flask app config BASEX_DATABASE matches TEST_DB_NAME env var.

    This catches cases where parts of the app are still using the default 'dictionary'
    database and helps surface misconfiguration early.
    """
    db_from_app = app.config.get('BASEX_DATABASE')
    env_db = os.environ.get('TEST_DB_NAME') or os.environ.get('BASEX_DATABASE')
    # If the environment DB differs from app config, synchronize the app config.
    # Some tests may change TEST_DB_NAME mid-session for specific scenarios; ensure
    # the Flask app uses the same database name.
    if db_from_app and env_db and db_from_app != env_db:
        import logging
        logging.getLogger(__name__).warning(
            "App BASEX_DATABASE '%s' does not match TEST_DB_NAME '%s' - synchronizing app config",
            db_from_app, env_db
        )
        app.config['BASEX_DATABASE'] = env_db

        # Also update any already-created connector instances so they use the
        # correct database. This prevents singleton connectors created earlier
        # (before env var was set) from continuing to point at the wrong DB.
        try:
            from app.services.dictionary_service import DictionaryService
            dict_service: DictionaryService = app.injector.get(DictionaryService)
            if hasattr(dict_service, 'db_connector') and getattr(dict_service, 'db_connector') is not None:
                dict_service.db_connector.database = env_db
                # force reconnection on next operation
                try:
                    dict_service.db_connector.disconnect()
                except Exception:
                    pass
        except Exception:
            # If injector isn't ready or dictionary service isn't bound yet,
            # that's OK; the change above to app.config is sufficient for later
            # connector creations.
            pass

    yield



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
def test_project(app: Flask, test_db_name: str):
    """Create a project setting that points to the test database."""
    unique_name = f"Integration Test Project {test_db_name}"
    project_id = None
    
    with app.app_context():
        from app.config_manager import ConfigManager
        from app.models.project_settings import ProjectSettings, db
        
        # Cleanup any existing collision
        existing = ProjectSettings.query.filter_by(project_name=unique_name).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()

        cm = ConfigManager(app.instance_path)
        settings = cm.create_settings(
            project_name=unique_name,
            basex_db_name=test_db_name,
            settings_json={'source_language': {'code': 'en', 'name': 'English'}}
        )
        project_id = settings.id
        # Expunge to keep the object available detached, preventing refresh error
        db.session.expunge(settings)
        
    yield settings
    
    # Teardown
    if project_id:
        with app.app_context():
            from app.models.project_settings import ProjectSettings, db
            s = ProjectSettings.query.get(project_id)
            if s:
                db.session.delete(s)
                db.session.commit()

@pytest.fixture(scope="function")
def client(app: Flask, test_project):
    """Create Flask test client (function-scoped for fresh context per test)."""
    with app.app_context():
        client = app.test_client()
        with client.session_transaction() as sess:
            # test_project is detached but id should be available if we expunged it correctly
            # or we can rely on it not being expired if we didn't access it?
            # Safest is to just access .id if it's loaded, or use the one we captured?
            # We yielded 'settings'.
            sess['project_id'] = test_project.id
        yield client


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
def ensure_clean_basex_db(app: Flask) -> None:
    """Ensure a clean (empty) LIFT dataset exists in TEST_DB_NAME before each test.

    Uses the same delete-and-add logic from tests/basex_test_utils to keep the
    behavior DRY and safe (avoids DROP/CREATE races).
    """
    from tests.basex_test_utils import delete_all_lift_entries

    # CRITICAL: Disconnect the session-scoped app's dictionary service to release locks
    # before attempting cleanup from a different connector.
    try:
        from app.services.dictionary_service import DictionaryService
        dict_service: DictionaryService = app.injector.get(DictionaryService)
        if hasattr(dict_service, 'db_connector') and dict_service.db_connector:
            dict_service.db_connector.disconnect()
    except Exception:
        pass

    db_name = os.environ.get('TEST_DB_NAME') or os.environ.get('BASEX_DATABASE') or 'dictionary_test'

    try:
        delete_all_lift_entries(db_name)
    except Exception:
        # If BaseX isn't available, skip resetting the DB; tests will skip later if needed
        pass


@pytest.fixture(scope="function", autouse=True)
def app_context(app: Flask):
    """Provide application context for each test (autouse, function-scoped)."""
    with app.app_context():
        from app.models.project_settings import db
        db.session.rollback()  # Clean up any previous transactions
        yield app
        db.session.rollback()  # Clean up after test


@pytest.fixture(scope="function", autouse=True)
def reset_ranges_service_parser(app: Flask):
    """Reset the singleton RangesService parser between tests.

    Some integration tests monkeypatch RangesService.ranges_parser.parse_string
    and expect the API layer to observe that patch. Because the app injector
    is session-scoped, we must restore the parser after each test to avoid
    cross-test contamination.
    """
    with app.app_context():
        try:
            from app.services.ranges_service import RangesService
            from app.parsers.lift_parser import LIFTRangesParser

            service = app.injector.get(RangesService)
            original_parser = getattr(service, 'ranges_parser', None)
            service.ranges_parser = LIFTRangesParser()
        except Exception:
            service = None
            original_parser = None

    yield

    with app.app_context():
        try:
            if service is not None:
                from app.parsers.lift_parser import LIFTRangesParser

                service.ranges_parser = LIFTRangesParser()
        except Exception:
            pass


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
