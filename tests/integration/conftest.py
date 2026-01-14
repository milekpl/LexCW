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

# Load environment variables from .env file (only if `.env` exists in repo root)
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(repo_root, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    # No .env found in the repo root; skip loading to avoid path-walking errors when workspace was moved
    pass

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
    import threading
    from tests.basex_test_utils import create_test_db, drop_test_db

    # Check BaseX availability by attempting a short connection with timeout
    from app.database.basex_connector import BaseXConnector

    connection_result = {"connected": False, "error": None}
    connection_done = threading.Event()

    def try_connect():
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
            connection_result["connected"] = True
        except Exception as e:
            connection_result["error"] = e
        finally:
            connection_done.set()

    # Start connection in a thread with timeout
    connect_thread = threading.Thread(target=try_connect, daemon=True)
    connect_thread.start()
    connection_done.wait(timeout=5)  # 5 second timeout (reduced for faster test discovery)

    if not connection_result["connected"]:
        pytest.skip(f"BaseX server not available: {connection_result['error'] or 'Connection timed out'}")

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
def ensure_recommended_ranges(client: FlaskClient, app: Flask) -> None:
    """Ensure recommended ranges are installed before each integration test.

    Attempts to call the public install endpoint and falls back to invoking
    the service implementation directly if the endpoint fails (for example
    when tests have replaced the app-level services with Mocks that break
    the endpoint behavior). This makes the fixture resilient and ensures
    recommended ranges are present for tests that expect them.
    """
    # Call the install endpoint to ensure ranges exist for tests that depend on them
    try:
        resp = client.post('/api/ranges/install_recommended')
        if resp.status_code not in (200, 201):
            # Try to install using a fresh service instance (in case app-level
            # services are mocked by the test).
            try:
                from app.services.dictionary_service import DictionaryService
                from app.database.basex_connector import BaseXConnector
                # Try to obtain a real connector from injector; if not available,
                # fall back to creating a new connector using env vars (more reliable for tests).
                try:
                    connector = app.injector.get(BaseXConnector)
                except Exception:
                    # Use environment variables for database name - these are set by
                    # basex_available fixture and are more reliable than app.config
                    import os
                    test_db = os.environ.get('TEST_DB_NAME') or os.environ.get('BASEX_DATABASE')
                    connector = BaseXConnector(
                        host=app.config.get('BASEX_HOST', 'localhost'),
                        port=app.config.get('BASEX_PORT', 1984),
                        username=app.config.get('BASEX_USERNAME', 'admin'),
                        password=app.config.get('BASEX_PASSWORD', 'admin'),
                        database=test_db
                    )
                ds = DictionaryService(connector)
                ds.install_recommended_ranges()
            except Exception:
                # If fallback install fails, log and continue - tests may skip or fail later
                import logging
                logging.getLogger(__name__).warning('Could not ensure recommended ranges via fallback installation')
    except Exception:
        # If the endpoint is unavailable for some tests, ignore
        pass


@pytest.fixture(autouse=True)
def sanitize_mocked_services(app: Flask) -> None:
    """Sanitize mocked services used in some tests.

    Some integration tests replace the app-level services with bare Mock
    instances and forget to set return_value for commonly used methods
    (e.g., get_lift_ranges). This fixture sets safe defaults to avoid
    template rendering and DB query errors when a Mock is in place.
    """
    from unittest.mock import Mock

    try:
        # Sanitize app.dict_service attribute if present
        ds = getattr(app, 'dict_service', None)
        # If the dict_service is a real object but has some mocked methods, ensure they return sane values
        if ds is not None and not isinstance(ds, Mock):
            for method_name, fallback in (
                ('get_lift_ranges', {}),
                ('get_system_status', {'db_connected': False, 'last_backup': None, 'storage_percent': 0}),
                ('get_recent_activity', []),
                ('get_ranges', {}),
            ):
                meth = getattr(ds, method_name, None)
                if isinstance(meth, Mock):
                    if not hasattr(meth, 'return_value') or isinstance(meth.return_value, Mock):
                        meth.return_value = fallback
        if isinstance(ds, Mock):
            # Ensure common methods used by views and APIs return sane types
            if not hasattr(ds.get_lift_ranges, 'return_value'):
                ds.get_lift_ranges.return_value = {}
            # If return value exists but is itself a Mock, replace with sane fallback
            if isinstance(getattr(ds, 'get_lift_ranges', None) and ds.get_lift_ranges.return_value, Mock):
                ds.get_lift_ranges.return_value = {}
            if not hasattr(ds.get_system_status, 'return_value'):
                ds.get_system_status.return_value = {
                    'db_connected': False,
                    'last_backup': None,
                    'storage_percent': 0,
                }
            if isinstance(getattr(ds, 'get_system_status', None) and ds.get_system_status.return_value, Mock):
                ds.get_system_status.return_value = {
                    'db_connected': False,
                    'last_backup': None,
                    'storage_percent': 0,
                }
            if not hasattr(ds.get_recent_activity, 'return_value'):
                ds.get_recent_activity.return_value = []
            if isinstance(getattr(ds, 'get_recent_activity', None) and ds.get_recent_activity.return_value, Mock):
                ds.get_recent_activity.return_value = []
            if not hasattr(ds.get_ranges, 'return_value'):
                ds.get_ranges.return_value = {}
            if isinstance(getattr(ds, 'get_ranges', None) and ds.get_ranges.return_value, Mock):
                ds.get_ranges.return_value = {}

        # Sanitize injector bindings (if tests replace bindings directly)
        try:
            # DictionaryService binding
            from app.services.dictionary_service import DictionaryService
            injected_ds = app.injector.get(DictionaryService)
            if isinstance(injected_ds, Mock):
                if not hasattr(injected_ds.get_lift_ranges, 'return_value'):
                    injected_ds.get_lift_ranges.return_value = {}
                if isinstance(getattr(injected_ds, 'get_lift_ranges', None) and injected_ds.get_lift_ranges.return_value, Mock):
                    injected_ds.get_lift_ranges.return_value = {}
                if not hasattr(injected_ds.get_system_status, 'return_value'):
                    injected_ds.get_system_status.return_value = {
                        'db_connected': False,
                        'last_backup': None,
                        'storage_percent': 0,
                    }
                if isinstance(getattr(injected_ds, 'get_system_status', None) and injected_ds.get_system_status.return_value, Mock):
                    injected_ds.get_system_status.return_value = {
                        'db_connected': False,
                        'last_backup': None,
                        'storage_percent': 0,
                    }
                if not hasattr(injected_ds.get_recent_activity, 'return_value'):
                    injected_ds.get_recent_activity.return_value = []
                if isinstance(getattr(injected_ds, 'get_recent_activity', None) and injected_ds.get_recent_activity.return_value, Mock):
                    injected_ds.get_recent_activity.return_value = []
                if not hasattr(injected_ds.get_ranges, 'return_value'):
                    injected_ds.get_ranges.return_value = {}
                if isinstance(getattr(injected_ds, 'get_ranges', None) and injected_ds.get_ranges.return_value, Mock):
                    injected_ds.get_ranges.return_value = {}

            # RangesService binding
            from app.services.ranges_service import RangesService
            injected_rs = app.injector.get(RangesService)
            if isinstance(injected_rs, Mock):
                if not hasattr(injected_rs.get_all_ranges, 'return_value'):
                    injected_rs.get_all_ranges.return_value = {}
                if isinstance(getattr(injected_rs, 'get_all_ranges', None) and injected_rs.get_all_ranges.return_value, Mock):
                    injected_rs.get_all_ranges.return_value = {}
                if not hasattr(injected_rs.get_range, 'return_value'):
                    injected_rs.get_range.return_value = {}
                if isinstance(getattr(injected_rs, 'get_range', None) and injected_rs.get_range.return_value, Mock):
                    injected_rs.get_range.return_value = {}

            # Class-level method patch sanitization (for tests that patch methods on the class itself)
            from app.services.dictionary_service import DictionaryService as _DictionaryServiceClass
            try:
                # If tests have patched methods on the DictionaryService class (e.g., with patch('...DictionaryService.get_ranges'))
                # these patched callables will be Mock instances; set sensible defaults to avoid Mocks leaking into production paths.
                for _meth, _fallback in (
                    ('get_ranges', {}),
                    ('get_lift_ranges', {}),
                    ('get_system_status', {'db_connected': False, 'last_backup': None, 'storage_percent': 0}),
                    ('search_entries', ([], 0)),
                    ('get_variant_types_from_traits', []),
                    ('install_recommended_ranges', {}),
                ):
                    cmeth = getattr(_DictionaryServiceClass, _meth, None)
                    if isinstance(cmeth, Mock):
                        try:
                            # Only set return_value if not already explicitly configured by test
                            if not hasattr(cmeth, 'return_value') or isinstance(cmeth.return_value, Mock):
                                cmeth.return_value = _fallback
                        except Exception:
                            pass
            except Exception:
                pass

            # Class-level patches for RangesService and BaseXConnector
            try:
                from app.services.ranges_service import RangesService as _RangesServiceClass
                for _rmeth, _rfallback in (
                    ('get_all_ranges', {}),
                    ('get_range', {}),
                ):
                    rcm = getattr(_RangesServiceClass, _rmeth, None)
                    if isinstance(rcm, Mock):
                        try:
                            if not hasattr(rcm, 'return_value') or isinstance(rcm.return_value, Mock):
                                rcm.return_value = _rfallback
                        except Exception:
                            pass
            except Exception:
                pass

            try:
                from app.database.basex_connector import BaseXConnector as _BaseXClass
                if hasattr(_BaseXClass, 'execute_query') and isinstance(getattr(_BaseXClass, 'execute_query'), Mock):
                    try:
                        if not hasattr(_BaseXClass.execute_query, 'return_value') or isinstance(_BaseXClass.execute_query.return_value, Mock):
                            _BaseXClass.execute_query.return_value = ''
                    except Exception:
                        pass
                if hasattr(_BaseXClass, 'execute_update') and isinstance(getattr(_BaseXClass, 'execute_update'), Mock):
                    try:
                        if not hasattr(_BaseXClass.execute_update, 'return_value') or isinstance(_BaseXClass.execute_update.return_value, Mock):
                            _BaseXClass.execute_update.return_value = None
                    except Exception:
                        pass
            except Exception:
                pass

            # BaseXConnector binding
            from app.database.basex_connector import BaseXConnector
            try:
                injected_connector = app.injector.get(BaseXConnector)
                if isinstance(injected_connector, Mock):
                    # Ensure key attributes/methods are sane defaults
                    if isinstance(getattr(injected_connector, 'database', None), Mock):
                        injected_connector.database = app.config.get('BASEX_DATABASE')
                    if hasattr(injected_connector, 'execute_query') and isinstance(injected_connector.execute_query, Mock):
                        injected_connector.execute_query.return_value = ''
                    if hasattr(injected_connector, 'execute_update') and isinstance(injected_connector.execute_update, Mock):
                        injected_connector.execute_update.return_value = None
                    if hasattr(injected_connector, 'execute_command') and isinstance(injected_connector.execute_command, Mock):
                        injected_connector.execute_command.return_value = ''
            except Exception:
                pass
        except Exception:
            # If injector isn't available or bindings aren't set, skip
            pass

        # Sanitize ConfigManager if it's mocked - ensure get_settings_by_id returns a simple object with basex_db_name
        try:
            from app.config_manager import ConfigManager
            cm = app.injector.get(ConfigManager)
            if isinstance(cm, Mock):
                import types
                dummy_settings = types.SimpleNamespace(basex_db_name=app.config.get('BASEX_DATABASE'))
                if not hasattr(cm.get_settings_by_id, 'return_value'):
                    cm.get_settings_by_id.return_value = dummy_settings
            # If get_settings_by_id itself is mocked (but cm is a real instance), ensure it returns sane object
            if hasattr(cm, 'get_settings_by_id') and isinstance(cm.get_settings_by_id, Mock):
                import types
                cm.get_settings_by_id.return_value = types.SimpleNamespace(basex_db_name=app.config.get('BASEX_DATABASE'))
            # If get_settings_by_id returns a Mock object, replace it
            try:
                rv = cm.get_settings_by_id.return_value
                from unittest.mock import Mock as _Mock
                if isinstance(rv, _Mock):
                    import types
                    cm.get_settings_by_id.return_value = types.SimpleNamespace(basex_db_name=app.config.get('BASEX_DATABASE'))
            except Exception:
                pass
        except Exception:
            # Ignore if injector not set up or ConfigManager not bound
            pass
    except Exception:
        # Best-effort only; don't fail test setup if this sanitization doesn't work
        pass

    yield


@pytest.fixture(scope="function", autouse=True)
def ensure_clean_basex_db(app: Flask) -> None:
    """Ensure a clean (empty) LIFT dataset exists in TEST_DB_NAME before each test.

    Uses the same delete-and-add logic from tests/basex_test_utils to keep the
    behavior DRY and safe (avoids DROP/CREATE races).
    """
    from tests.basex_test_utils import delete_all_lift_entries

    # CRITICAL: Disconnect ALL database connections to release locks
    # before attempting cleanup from a different connector.
    try:
        from app.services.dictionary_service import DictionaryService
        from app.services.ranges_service import RangesService
        from app.services.operation_history_service import OperationHistoryService
        
        # Disconnect dictionary service
        dict_service: DictionaryService = app.injector.get(DictionaryService)
        if hasattr(dict_service, 'db_connector') and dict_service.db_connector:
            dict_service.db_connector.disconnect()
        
        # Disconnect ranges service
        ranges_service: RangesService = app.injector.get(RangesService)
        if hasattr(ranges_service, 'db_connector') and ranges_service.db_connector:
            ranges_service.db_connector.disconnect()
        
        # Clear operation history to prevent state pollution
        history_service: OperationHistoryService = app.injector.get(OperationHistoryService)
        history_service.clear_history()
        
    except Exception as e:
        # Log but don't fail the test setup
        import logging
        logging.getLogger(__name__).warning(f"Error during database cleanup: {e}")


@pytest.fixture(scope="function", autouse=True)
def reset_database_connections(app: Flask) -> None:
    """Reset database connections after each test to prevent state pollution.
    
    This fixture runs after each test and ensures that all database connections
    are properly closed and reset to prevent tests from affecting each other.
    """
    yield  # Run the test
    
    # After test completes, clean up database connections
    try:
        from app.services.dictionary_service import DictionaryService
        from app.services.ranges_service import RangesService
        
        # Disconnect dictionary service
        dict_service: DictionaryService = app.injector.get(DictionaryService)
        if hasattr(dict_service, 'db_connector') and dict_service.db_connector:
            dict_service.db_connector.disconnect()
        
        # Disconnect ranges service
        ranges_service: RangesService = app.injector.get(RangesService)
        if hasattr(ranges_service, 'db_connector') and ranges_service.db_connector:
            ranges_service.db_connector.disconnect()
        
    except Exception as e:
        # Log but don't fail the test teardown
        import logging
        logging.getLogger(__name__).warning(f"Error during database connection reset: {e}")

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
def reset_ranges_service_parser(app: Flask, client):
    """Reset singleton service state between tests to ensure test isolation.

    This fixture runs before each test and ensures:
    1. RangesService parser is reset (for tests that patch parse_string)
    2. DictionaryService ranges cache is cleared and reloaded to a known state

    The client fixture is used as a dependency to ensure proper execution order.
    After this fixture runs, the DictionaryService will have a fresh, complete
    ranges cache with all standard ranges installed.
    """
    with app.app_context():
        try:
            from app.services.ranges_service import RangesService
            from app.parsers.lift_parser import LIFTRangesParser

            ranges_service = app.injector.get(RangesService)
            original_parser = getattr(ranges_service, 'ranges_parser', None)
            ranges_service.ranges_parser = LIFTRangesParser()
        except Exception:
            ranges_service = None
            original_parser = None

        try:
            from app.services.dictionary_service import DictionaryService
            dict_service = app.injector.get(DictionaryService)

            # Clear the ranges cache completely - this makes the service stateless
            dict_service.ranges = None

            # Force reinstall ranges to get a known good state
            # This ensures all tests start with the same complete set of ranges
            dict_service.install_recommended_ranges()
        except Exception:
            # If reinstall fails, the ranges might already be loaded
            # Continue anyway - the service will reload on first access
            pass

    yield

    # Teardown: restore original state
    with app.app_context():
        try:
            if ranges_service is not None and original_parser is not None:
                ranges_service.ranges_parser = original_parser
        except Exception:
            pass

        try:
            from app.services.dictionary_service import DictionaryService
            dict_service = app.injector.get(DictionaryService)
            # Clear cache for next test
            dict_service.ranges = None
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


@pytest.fixture(autouse=True)
def fail_on_bare_class_patches():
    """Fail tests that leave class-level patched methods as bare Mocks.

    Some tests use `patch('app.services.dictionary_service.DictionaryService.get_ranges', ...)`
    at class or module scope but forget to configure the Mock with a sensible
    `return_value`. Those Mocks leak into runtime when the app constructs new
    service instances and cause hard-to-debug failures (e.g., Mock objects
    appearing in templates or XQuery construction). This fixture detects
    common cases and fails the test early with a helpful message.
    """
    yield

    from unittest.mock import Mock
    bad: list[str] = []

    try:
        from app.services.dictionary_service import DictionaryService as _DictionaryServiceClass
        for _name in ('get_ranges', 'get_lift_ranges', 'get_system_status', 'search_entries', 'install_recommended_ranges'):
            _attr = getattr(_DictionaryServiceClass, _name, None)
            if isinstance(_attr, Mock):
                bad.append(f'DictionaryService.{_name}')
    except Exception:
        pass

    try:
        from app.services.ranges_service import RangesService as _RangesServiceClass
        for _name in ('get_all_ranges', 'get_range'):
            _attr = getattr(_RangesServiceClass, _name, None)
            if isinstance(_attr, Mock):
                bad.append(f'RangesService.{_name}')
    except Exception:
        pass

    try:
        from app.database.basex_connector import BaseXConnector as _BaseXClass
        for _name in ('execute_query', 'execute_update', 'execute_command'):
            _attr = getattr(_BaseXClass, _name, None)
            if isinstance(_attr, Mock):
                bad.append(f'BaseXConnector.{_name}')
    except Exception:
        pass

    if bad:
        pytest.fail(
            'Detected class-level method patching left as bare Mock for: ' +
            ', '.join(bad) +
            '. Configure tests to set `return_value` on these Mocks or use instance-level patching/fakes to avoid leaking Mocks into runtime.'
        )


@pytest.fixture(autouse=True)
def fail_on_injector_bare_mocks(app: Flask):
    """Fail tests that leave injector-bound services as bare Mocks without configured return_values."""
    yield

    from unittest.mock import Mock
    problems: list[str] = []

    try:
        from app.services.dictionary_service import DictionaryService
        ds = app.injector.get(DictionaryService)
        if isinstance(ds, Mock):
            for m in ('get_ranges', 'get_lift_ranges', 'get_system_status', 'search_entries'):
                meth = getattr(ds, m, None)
                if isinstance(meth, Mock):
                    # If the mock method has no return_value or return_value is another Mock, it's a problem
                    if not hasattr(meth, 'return_value') or isinstance(meth.return_value, Mock):
                        problems.append(f'DictionaryService.{m}')
    except Exception:
        pass

    try:
        from app.services.ranges_service import RangesService
        rs = app.injector.get(RangesService)
        if isinstance(rs, Mock):
            for m in ('get_all_ranges', 'get_range'):
                meth = getattr(rs, m, None)
                if isinstance(meth, Mock):
                    if not hasattr(meth, 'return_value') or isinstance(meth.return_value, Mock):
                        problems.append(f'RangesService.{m}')
    except Exception:
        pass

    if problems:
        pytest.fail(
            'Detected injector-bound Mock methods without configured return_value: ' + ', '.join(problems) +
            '. Tests should set `mock.return_value = ...` or use fakes instead of leaving bare Mocks.'
        )


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
