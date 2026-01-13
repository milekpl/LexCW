"""
Conftest for E2E tests using Playwright.

Provides robust test isolation using snapshot/restore pattern for BaseX database.
"""

from __future__ import annotations

import sys
import os
import pytest
import tempfile
import logging
import uuid
import shutil
from typing import Generator
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import safety utilities
from tests.test_db_safety_utils import generate_safe_db_name, is_safe_database_name

# Import fixtures from parent conftest (we'll override flask_test_server with session-scoped version)
from tests.conftest import flask_test_server_info

import socket
import threading
import time
from werkzeug.serving import make_server

logger = logging.getLogger(__name__)

# Tests that don't modify the database - skip snapshot/restore for these
# This significantly speeds up read-only tests by avoiding BaseX EXPORT operations
SNAPSHOT_SKIP_PATTERNS = [
    'test_grammatical_info_dropdown_populated',
    'test_domain_type_dropdown_populated',
    'test_usage_type_dropdown_populated',
    'test_semantic_domain_dropdown_populated',
    'test_relation_type_dropdown_populated',
    'test_variant_type_dropdown_populated',
    'test_all_ranges_api_accessible',
    'test_dynamic_lift_range_initialization',
    'test_ranges_loaded_via_api',
    'test_ranges_ui_populated',
    'test_dropdown_populated',
    # Read-only tests that just verify UI state
]


# Session-scoped Flask server fixture - must be defined before other session fixtures
@pytest.fixture(scope="session", autouse=True)
def flask_test_server(setup_e2e_test_database):
    """Start the Flask app in-process on a free port for the entire test session.

    This is a session-scoped version that starts the server once and reuses it
    across all tests, significantly improving test performance.
    """
    from werkzeug.serving import make_server
    from app import create_app
    import urllib.request

    # Find a free port
    sock = socket.socket()
    sock.bind(("localhost", 0))
    port = sock.getsockname()[1]
    sock.close()

    # Load .env for PostgreSQL settings
    from dotenv import load_dotenv
    load_dotenv('/mnt/d/Dokumenty/slownik-wielki/flask-app/.env', override=True)

    # Create the app with testing config
    app = create_app(os.getenv('FLASK_CONFIG') or 'testing')

    # Force E2E mode - manually create PostgreSQL connection
    import psycopg2
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
        from app.database.workset_db import create_workset_tables
        create_workset_tables(pg_pool)
        print(f"Successfully connected to PostgreSQL at {app.config.get('PG_HOST')}:{app.config.get('PG_PORT')}")
    except Exception as e:
        print(f"Warning: Could not connect to PostgreSQL: {e}")
        app.pg_pool = None

    # Use the database name already set by setup_e2e_test_database
    env_db = os.environ.get('TEST_DB_NAME') or os.environ.get('BASEX_DATABASE')
    if env_db:
        app.config['BASEX_DATABASE'] = env_db
    else:
        app.config['BASEX_DATABASE'] = app.config.get('BASEX_DATABASE', 'test_entries_db')

    # Export to environment
    os.environ['BASEX_DATABASE'] = app.config['BASEX_DATABASE']
    os.environ['TEST_DB_NAME'] = app.config['BASEX_DATABASE']

    # Create default project settings
    project_id = None
    with app.app_context():
        from app.config_manager import ConfigManager
        from app.models.project_settings import ProjectSettings

        existing = ProjectSettings.query.first()
        if existing:
            project_id = existing.id
        else:
            cm = ConfigManager(app.instance_path)
            settings = cm.create_settings(
                project_name="E2E Test Project",
                basex_db_name=app.config['BASEX_DATABASE'],
                settings_json={
                    'source_language': {'code': 'en', 'name': 'English'},
                    'target_languages': [{'code': 'es', 'name': 'Spanish'}]
                }
            )
            project_id = settings.id

    server = make_server('localhost', port, app)
    thread = None
    try:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        base_url = f"http://localhost:{port}"

        # Wait for server to be ready
        for _ in range(30):
            try:
                with urllib.request.urlopen(base_url) as resp:
                    if resp.status in (200, 404):
                        break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError(f"Flask test server did not start on {base_url}")

        # Store for other fixtures
        flask_test_server._project_id = project_id  # type: ignore

        # Set the test app reference
        from tests.test_app_utils import set_test_app
        set_test_app(app)

        print(f"[E2E-SESSION] Flask server started at {base_url}")
        yield base_url

    finally:
        from tests.test_app_utils import reset_test_app
        reset_test_app()

        try:
            server.shutdown()
        except Exception:
            pass
        if thread and thread.is_alive():
            thread.join(timeout=1)
        print(f"[E2E-SESSION] Flask server stopped")


@pytest.fixture(scope="session")
def flask_test_server_info(flask_test_server) -> tuple:
    """Provide (base_url, project_id) for tests that need project selection."""
    return (flask_test_server, getattr(flask_test_server, '_project_id', None))


# Content that should always be in the pristine database
PRISTINE_LIFT = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test_entry_1" dateCreated="2024-01-15T10:30:00Z" dateModified="2024-03-20T14:45:00Z">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="test_sense_1">
            <definition>
                <form lang="en"><text>A test entry</text></form>
            </definition>
            <gloss lang="pl"><text>test</text></gloss>
        </sense>
    </entry>
    <entry id="test_entry_2" dateCreated="2024-01-16T11:30:00Z" dateModified="2024-03-21T15:45:00Z">
        <lexical-unit>
            <form lang="en"><text>component</text></form>
        </lexical-unit>
        <sense id="test_sense_2">
            <definition>
                <form lang="en"><text>A component entry</text></form>
            </definition>
            <gloss lang="pl"><text>komponent</text></gloss>
        </sense>
    </entry>
    <entry id="test_entry_3" dateCreated="2024-01-17T12:30:00Z" dateModified="2024-03-22T16:45:00Z">
        <lexical-unit>
            <form lang="en"><text>variant</text></form>
        </lexical-unit>
        <sense id="test_sense_3">
            <definition>
                <form lang="en"><text>A variant entry</text></form>
            </definition>
            <gloss lang="pl"><text>wariant</text></gloss>
        </sense>
    </entry>
</lift>'''

PRISTINE_RANGES = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <range id="grammatical-info" href="http://fieldworks.sil.org/lift/grammatical-info">
        <range-element id="Noun" guid="5049f0e3-12a4-4e9f-97f7-60091082793c">
            <label>
                <form lang="en"><text>Noun</text></form>
            </label>
            <abbrev>
                <form lang="en"><text>n</text></form>
            </abbrev>
        </range-element>
        <range-element id="Verb" guid="5049f0e3-12a4-4e9f-97f7-60091082793d">
            <label>
                <form lang="en"><text>Verb</text></form>
            </label>
            <abbrev>
                <form lang="en"><text>v</text></form>
            </abbrev>
        </range-element>
        <range-element id="Adjective" guid="5049f0e3-12a4-4e9f-97f7-60091082793e">
            <label>
                <form lang="en"><text>Adjective</text></form>
            </label>
            <abbrev>
                <form lang="en"><text>adj</text></form>
            </abbrev>
        </range-element>
    </range>
    <range id="lexical-relation" href="http://fieldworks.sil.org/lift/lexical-relation">
        <range-element id="_component-lexeme" guid="4e1c72b2-7430-4eb9-a9d2-4b31c5620804">
            <label>
                <form lang="en"><text>Component</text></form>
            </label>
        </range-element>
        <range-element id="_main-entry" guid="45e6b7ef-0e55-448a-a7f2-93d485712c54">
            <label>
                <form lang="en"><text>Main Entry</text></form>
            </label>
        </range-element>
    </range>
    <range id="semantic-domain-ddp4" href="http://fieldworks.sil.org/lift/semantic-domain-ddp4">
        <range-element id="1" guid="63403699-07c1-4d82-91ab-f8046c335e11">
            <label>
                <form lang="en"><text>Universe, creation</text></form>
            </label>
        </range-element>
        <range-element id="1.1" guid="999581c4-1611-4acb-ae1b-cc1f7e0e18e5" parent="1">
            <label>
                <form lang="en"><text>Sky</text></form>
            </label>
        </range-element>
    </range>
    <range id="anthro-code" href="http://fieldworks.sil.org/lift/anthro-code">
        <range-element id="1" guid="d12cf2e5-22c8-4826-9d98-8f669f4c5496">
            <label>
                <form lang="en"><text>Social organization</text></form>
            </label>
        </range-element>
    </range>
    <range id="domain-type" href="http://fieldworks.sil.org/lift/domain-type">
        <range-element id="agriculture" guid="0fc97f63-a059-4894-84bf-c29a58f96dc4">
            <label>
                <form lang="en"><text>Agriculture</text></form>
            </label>
        </range-element>
        <range-element id="grammar" guid="56d33d26-e0fb-4840-bea6-e7e1b86f3e95">
            <label>
                <form lang="en"><text>Grammar</text></form>
            </label>
        </range-element>
    </range>
    <range id="usage-type" href="http://fieldworks.sil.org/lift/usage-type">
        <range-element id="archaic" guid="4f845bbd-1bf4-4c8b-9f50-76f1b69e0d3d">
            <label>
                <form lang="en"><text>Archaic</text></form>
            </label>
        </range-element>
        <range-element id="colloquial" guid="cf829d77-cf92-4328-bc86-72a44e42fbf0">
            <label>
                <form lang="en"><text>Colloquial</text></form>
            </label>
        </range-element>
    </range>
    <range id="variant-type" href="http://fieldworks.sil.org/lift/variant-type">
        <range-element id="spelling" guid="a1b2c3d4-e5f6-7890-abcd-ef0123456789">
            <label>
                <form lang="en"><text>Spelling Variant</text></form>
            </label>
        </range-element>
        <range-element id="dialectal" guid="b2c3d4e5-f6a7-8901-bcde-f01234567890">
            <label>
                <form lang="en"><text>Dialectal Variant</text></form>
            </label>
        </range-element>
        <range-element id="free" guid="c3d4e5f6-a7b8-9012-cdef-012345678901">
            <label>
                <form lang="en"><text>Free Variant</text></form>
            </label>
        </range-element>
        <range-element id="irregular" guid="d4e5f6a7-b8c9-0123-defa-123456789012">
            <label>
                <form lang="en"><text>Irregularly Inflected Form</text></form>
            </label>
        </range-element>
    </range>
</lift-ranges>'''


def _get_connected_connector(db_name: str):
    """Create a BaseX connector and open the specified database."""
    from app.database.basex_connector import BaseXConnector
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=db_name,  # Set database BEFORE connecting
    )
    connector.connect()
    return connector


def _log_db_state(label: str, db_name: str, sample_size: int = 10) -> None:
    """Log current database state for debugging isolation issues."""
    if os.getenv('E2E_DEBUG_STATE', 'false').lower() not in ('1', 'true', 'yes', 'on'):
        return

    try:
        connector = _get_connected_connector(db_name)
    except Exception as exc:  # pragma: no cover - defensive debug path
        logger.warning("[E2E-DEBUG] %s: could not connect to DB %s: %s", label, db_name, exc)
        return

    try:
        try:
            count_raw = connector.execute_query(
                f"xquery count(collection('{db_name}')//entry)"
            )
            count = int(count_raw.strip()) if count_raw else 0
        except Exception:
            count = -1

        try:
            ids_raw = connector.execute_query(
                f"xquery for $e in subsequence(collection('{db_name}')//entry/@id, 1, {sample_size}) return string($e)"
            )
            ids = ids_raw.split() if ids_raw else []
        except Exception:
            ids = []

        msg = f"[E2E-DEBUG] {label} | db={db_name} | entry_count={count} | sample_ids={ids}"
        logger.info(msg)
        print(msg)  # Also print to stdout for pytest capture
    finally:
        try:
            connector.disconnect()
        except Exception:
            pass


def _snapshot_database(db_name: str) -> str | None:
    """Export the database to a temporary file and return the file path.

    Uses BaseX EXPORT command to create a full backup of the database.
    Returns None if snapshot cannot be created.

    Note: This function is kept for reference but snapshot/restore via EXPORT/ADD
    is unreliable. Use _ensure_pristine_state instead for test isolation.
    """
    connector = _get_connected_connector(db_name)

    # Generate unique backup file path
    snapshot_id = str(uuid.uuid4())[:8]
    backup_path = f"/tmp/basex_snapshot_{db_name}_{snapshot_id}.xml"

    try:
        # Export entire database to backup file
        connector.execute_command(f"EXPORT {backup_path}")
        logger.debug(f"Snapshot created: {backup_path}")
        return backup_path
    except Exception as e:
        logger.warning(f"Failed to create snapshot (database may be empty or inaccessible): {e}")
        # Try to create an empty snapshot file
        try:
            with open(backup_path, 'w') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?><lift version="0.13"></lift>')
            logger.debug(f"Created empty snapshot fallback: {backup_path}")
            return backup_path
        except Exception:
            pass
        return None
    finally:
        try:
            connector.disconnect()
        except Exception:
            pass


def _restore_database(db_name: str, backup_path: str):
    """Restore the database from a snapshot file.

    Drops the existing database and recreates it from the backup.
    BaseX EXPORT creates a directory, so we need to handle that.

    Note: This method is DEPRECATED because EXPORT/ADD is unreliable for LIFT data.
    Use _ensure_pristine_state instead for reliable test isolation.
    """
    # First connect without a database to run DROP/CREATE commands
    from app.database.basex_connector import BaseXConnector
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=None,
    )
    connector.connect()

    try:
        # Drop existing database if it exists
        try:
            connector.execute_command(f"DROP DB {db_name}")
            logger.debug(f"Dropped database: {db_name}")
        except Exception as e:
            logger.debug(f"Could not drop database {db_name} (may not exist): {e}")

        # Create fresh database
        connector.execute_command(f"CREATE DB {db_name}")
        logger.debug(f"Created database: {db_name}")

        # Disconnect and reconnect with the database opened
        connector.disconnect()
        connector = _get_connected_connector(db_name)

        # Determine if backup_path is a file or directory
        if os.path.isfile(backup_path):
            # It's a single file, add directly
            connector.execute_command(f"ADD {backup_path}")
            logger.debug(f"Restored from file: {backup_path}")
        elif os.path.isdir(backup_path):
            # It's a directory - BaseX EXPORT creates directories with files
            # Use the original EXPORT path for reliable restoration
            # The ADD command needs trailing slash for directories
            add_path = backup_path.rstrip('/') + '/'

            # Try adding the directory contents
            connector.execute_command(f"ADD {add_path}")
            logger.debug(f"Restored from directory: {backup_path}")
        else:
            # Backup path doesn't exist, fall back to pristine state
            logger.warning(f"Backup path does not exist: {backup_path}")
            _ensure_pristine_state(db_name)
    finally:
        try:
            connector.disconnect()
        except Exception:
            pass


def _ensure_pristine_state(db_name: str):
    """Ensure the database has the pristine initial state.

    This is a fallback that restores the hardcoded sample data if the database
    is missing entries or has unknown content.
    """
    # Connect without database first
    from app.database.basex_connector import BaseXConnector
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=None,
    )
    connector.connect()

    try:
        # First, ensure the database exists
        try:
            connector.execute_command(f"CREATE DB {db_name}")
            logger.debug(f"Created database: {db_name}")
        except Exception:
            pass  # Database may already exist

        # Now connect with database opened
        connector.disconnect()
        connector = _get_connected_connector(db_name)

        # Check if test_entry_1 exists
        check_query = f"xquery exists(collection('{db_name}')//entry[@id='test_entry_1'])"
        result = connector.execute_query(check_query)
        entry_exists = result.strip().lower() == 'true' if result else False

        if not entry_exists:
            logger.info("Database not in pristine state, restoring sample data")

            try:
                # Add sample LIFT content
                with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
                    f.write(PRISTINE_LIFT)
                    temp_file = f.name
                try:
                    connector.execute_command(f"ADD {temp_file}")
                    logger.info("Restored sample LIFT entries")
                finally:
                    os.unlink(temp_file)

                # Add comprehensive ranges.xml
                with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
                    f.write(PRISTINE_RANGES)
                    temp_file = f.name
                try:
                    connector.execute_command(f"ADD TO ranges.xml {temp_file}")
                    logger.info("Restored sample ranges.xml")
                finally:
                    os.unlink(temp_file)
            finally:
                connector.disconnect()
    finally:
        try:
            connector.disconnect()
        except Exception:
            pass


# Custom marker for destructive database tests that need isolation
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "destructive: marks tests that modify database structure (use separate DB)"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_e2e_test_database(request):
    """Set up a safe, isolated test database for E2E tests with snapshot support.

    This fixture provides stronger isolation guarantees:
    - Uses safe database naming with timestamp and test type
    - Validates database name safety before creation
    - Restores original environment variables after tests
    - Performs atomic cleanup with verification
    - Prevents environment variable leakage
    - Destructive tests (@pytest.mark.destructive) are skipped when mixed with other tests
    """
    print("[E2E-DEBUG] SESSION FIXTURE ENTERED")
    from app.database.basex_connector import BaseXConnector

    # Store original environment variables for restoration
    original_test_db = os.environ.get('TEST_DB_NAME')
    original_basex_db = os.environ.get('BASEX_DATABASE')
    original_aggressive = os.environ.get('BASEX_AGGRESSIVE_DISCONNECT')

    # Check if any tests in this session are marked as destructive
    has_destructive_tests = any(
        test.get_closest_marker("destructive")
        for test in request.session.items
    )

    # Check if there are both destructive and non-destructive tests
    has_normal_tests = any(
        not test.get_closest_marker("destructive")
        for test in request.session.items
    )

    # If we have both destructive and normal tests, skip destructive ones
    # They need to be run separately
    if has_destructive_tests and has_normal_tests:
        for test in request.session.items:
            if test.get_closest_marker("destructive"):
                marker = test.get_closest_marker("destructive")
                if marker:
                    marker.kwargs["reason"] = marker.kwargs.get("reason", "") + " (run separately: pytest tests/e2e/test_database_operations_e2e.py)"
                    test.add_marker(pytest.mark.skip(reason="Destructive tests must run separately"))

    # CRITICAL FIX: Always generate a fresh database name for e2e tests
    # DO NOT use TEST_DB_NAME from parent conftest.py, which creates an empty database
    # at module import time. E2e tests MUST start with pristine data (test_entry_1, test_entry_2, test_entry_3).
    # See E2E_TEST_ISOLATION_ANALYSIS.md for root cause details.
    test_db = generate_safe_db_name('e2e')

    # Validate the generated name
    if not is_safe_database_name(test_db):
        pytest.fail(f"Generated unsafe E2E database name: {test_db}")

    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=None,
    )

    # Store original Redis setting for restoration
    original_redis_enabled = os.environ.get('REDIS_ENABLED')

    try:
        # Set isolated environment for E2E tests
        os.environ['TEST_DB_NAME'] = test_db
        os.environ['BASEX_DATABASE'] = test_db
        os.environ['BASEX_AGGRESSIVE_DISCONNECT'] = 'true'
        # Disable Redis caching for E2E tests to ensure complete isolation
        # Each test must start with fresh data, not cached results from previous tests
        os.environ['REDIS_ENABLED'] = 'false'
        
        # Reset CacheService singleton so it picks up the new REDIS_ENABLED setting
        from app.services.cache_service import CacheService
        CacheService.reset_singleton()

        print(f"[E2E-DEBUG] SESSION SETUP: Creating database {test_db}")
        connector.connect()

        # Drop existing test database if it exists
        try:
            connector.execute_command(f"DROP DB {test_db}")
            logger.info(f"Dropped existing E2E test database: {test_db}")
        except Exception:
            pass  # Database doesn't exist

        # Create new test database
        connector.create_database(test_db)
        connector.database = test_db
        connector.disconnect()
        connector.connect()

        logger.info(f"Created safe E2E test database: {test_db}")

        # Add sample LIFT content with dateCreated and dateModified
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(PRISTINE_LIFT)
            temp_file = f.name

        try:
            connector.execute_command(f"ADD {temp_file}")
            logger.info("Added LIFT data to safe E2E test database")
        finally:
            try:
                os.unlink(temp_file)
            except OSError:
                pass

        # Add comprehensive ranges.xml
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(PRISTINE_RANGES)
            temp_file = f.name

        try:
            connector.execute_command(f"ADD TO ranges.xml {temp_file}")
            logger.info("Added comprehensive ranges.xml to safe E2E test database")
            print(f"[E2E-DEBUG] SESSION SETUP: Added pristine data to {test_db}")
            _log_db_state("SESSION-SETUP-COMPLETE", test_db)
        finally:
            try:
                os.unlink(temp_file)
            except OSError:
                pass

        # CRITICAL: Disconnect setup connector before yielding to tests
        # If we keep this connection open, it will block database updates in the Flask server
        try:
            connector.disconnect()
            logger.info("Disconnected setup connector before tests run")
        except Exception as e:
            logger.warning(f"Failed to disconnect setup connector: {e}")

        yield

    finally:
        # Safe cleanup with environment restoration
        try:
            # Restore original environment variables
            if original_test_db:
                os.environ['TEST_DB_NAME'] = original_test_db
            elif 'TEST_DB_NAME' in os.environ:
                del os.environ['TEST_DB_NAME']

            if original_basex_db:
                os.environ['BASEX_DATABASE'] = original_basex_db
            elif 'BASEX_DATABASE' in os.environ:
                del os.environ['BASEX_DATABASE']

            if original_aggressive:
                os.environ['BASEX_AGGRESSIVE_DISCONNECT'] = original_aggressive
            elif 'BASEX_AGGRESSIVE_DISCONNECT' in os.environ:
                del os.environ['BASEX_AGGRESSIVE_DISCONNECT']

            # Restore Redis setting
            if original_redis_enabled:
                os.environ['REDIS_ENABLED'] = original_redis_enabled
            elif 'REDIS_ENABLED' in os.environ:
                del os.environ['REDIS_ENABLED']

            # Atomic cleanup with verification
            cleanup_connector = BaseXConnector(
                host=os.getenv('BASEX_HOST', 'localhost'),
                port=int(os.getenv('BASEX_PORT', '1984')),
                username=os.getenv('BASEX_USERNAME', 'admin'),
                password=os.getenv('BASEX_PASSWORD', 'admin'),
                database=None,
            )

            try:
                cleanup_connector.connect()
                # Verify database exists before dropping
                try:
                    result = cleanup_connector.execute_query("xquery db:list()")
                    if test_db in result:
                        cleanup_connector.execute_command(f"DROP DB {test_db}")
                        logger.info(f"Successfully dropped safe E2E test database: {test_db}")
                    else:
                        logger.warning(f"E2E test database {test_db} not found during cleanup")
                except Exception as e:
                    logger.warning(f"Could not verify E2E database existence before cleanup: {e}")

            finally:
                try:
                    cleanup_connector.disconnect()
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Failed to clean up E2E test database {test_db}: {e}")
            # Even if cleanup fails, we've restored the environment variables
            raise


@pytest.fixture(scope="function", autouse=True)
def _db_snapshot_restore(request):
    """Snapshot/restore fixture for test isolation.

    This fixture ensures each test starts with a clean database state,
    fixing test pollution issues where earlier tests leave entries or
    modified ranges that break subsequent tests.

    IMPORTANT: This fixture has priority over other restore fixtures.
    It runs FIRST during teardown to preserve the snapshot for restoration.

    Order of operations:
    1. Before test: Create snapshot of current database state
    2. After test: Restore from snapshot (preserves test modifications for debugging)
       Fall back to pristine state if snapshot restore fails
    """
    # Store the request for use in finally block
    request_fixture = request
    test_db = os.environ.get('TEST_DB_NAME')
    if not test_db:
        yield
        return

    # Check if this test should skip snapshot/restore (read-only test)
    test_name = request.node.name
    should_skip = any(pattern in test_name for pattern in SNAPSHOT_SKIP_PATTERNS)

    if should_skip:
        # Skip snapshot for read-only tests that don't modify the database
        yield
        return

    backup_path = None
    backup_is_dir = False

    try:
        _log_db_state("before-snapshot", test_db)
        # Create snapshot BEFORE test
        backup_path = _snapshot_database(test_db)
        if backup_path and os.path.isdir(backup_path):
            backup_is_dir = True
        elif backup_path and not os.path.isfile(backup_path):
            # Path exists but is neither file nor directory - shouldn't happen
            backup_path = None

        yield

    except Exception as e:
        logger.warning(f"Test failed with exception: {e}")
        raise
    finally:
        # Restore AFTER test (always)
        if test_db:
            _log_db_state("after-test-before-restore", test_db)
            # Priority 1: Restore from snapshot if available
            if backup_path and backup_is_dir:
                try:
                    _restore_database(test_db, backup_path)
                    logger.debug("Restored database from snapshot")
                except Exception as restore_error:
                    logger.warning(f"Failed to restore from snapshot: {restore_error}")
                    # Fall back to pristine state
                    try:
                        _ensure_pristine_state(test_db)
                    except Exception:
                        pass
                finally:
                    # Cleanup backup directory
                    try:
                        if os.path.isdir(backup_path):
                            shutil.rmtree(backup_path)
                    except OSError:
                        pass
            elif backup_path and os.path.isfile(backup_path):
                # Cleanup backup file
                try:
                    os.unlink(backup_path)
                except OSError:
                    pass
            else:
                # No valid snapshot, ensure pristine state
                try:
                    _ensure_pristine_state(test_db)
                except Exception:
                    pass

            # CRITICAL: Invalidate all caches after database restore
            # This ensures subsequent tests get fresh data instead of stale cache
            try:
                from tests.test_app_utils import invalidate_all_caches
                invalidate_all_caches()
                logger.debug("Invalidated all caches after database restore")
            except Exception as cache_error:
                logger.warning(f"Failed to invalidate caches: {cache_error}")

            _log_db_state("after-restore", test_db)


@pytest.fixture(scope="function", autouse=True)
def _verify_db_isolation(request):
    """Optional fixture to verify database state hasn't changed unexpectedly.

    This is a development tool - it can be enabled to catch tests that
    modify the database without proper cleanup.

    To enable: set BASEX_VERIFY_ISOLATION=true environment variable.
    """
    if os.environ.get('BASEX_VERIFY_ISOLATION') != 'true':
        yield
        return

    test_db = os.environ.get('TEST_DB_NAME')
    if not test_db:
        yield
        return

    try:
        # Get list of all documents in database (before state)
        connector = _get_connected_connector(test_db)
        try:
            before_result = connector.execute_query(
                f"xquery for $doc in collection('{test_db}') return document-uri($doc)"
            )
            before_state = before_result or "empty"
        finally:
            connector.disconnect()

        yield

        # Get after state
        connector = _get_connected_connector(test_db)
        try:
            after_result = connector.execute_query(
                f"xquery for $doc in collection('{test_db}') return document-uri($doc)"
            )
            after_state = after_result or "empty"
        finally:
            connector.disconnect()

        if before_state != after_state:
            logger.warning(
                f"DB state changed during test '{request.node.name}'. "
                f"Before: {len(before_state)} chars, After: {len(after_state)} chars. "
                f"Consider using snapshot/restore or fixing the test."
            )
    except Exception as e:
        logger.warning(f"Could not verify DB isolation: {e}")
        yield


@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Create a browser instance for the session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


# Session-scoped browser context and page fixtures for performance
_session_project_selected = False


@pytest.fixture(scope="session", autouse=True)
def _setup_session_browser_context(request):
    """Ensure project selection happens once per session."""
    global _session_project_selected
    _session_project_selected = False
    yield request


@pytest.fixture(scope="session")
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Create a single browser context for the entire test session."""
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        java_script_enabled=True,
    )
    yield context
    context.close()


def _ensure_project_selected(page: Page, base_url: str):
    """Select project once per session, not per test."""
    global _session_project_selected

    if _session_project_selected:
        return

    try:
        page.goto(f"{base_url}/settings/projects", timeout=10000)
        select_button = page.locator("a.btn-success:has-text('Select')").first

        if select_button.count() > 0:
            select_button.click()
            page.wait_for_load_state("networkidle")
            # Close any wizard modals
            page.evaluate("""() => {
                const m1 = document.getElementById('projectSetupModal');
                if (m1) { const inst = bootstrap.Modal.getInstance(m1); if (inst) inst.hide(); }
                const m2 = document.getElementById('projectSetupModalSettings');
                if (m2) { const inst = bootstrap.Modal.getInstance(m2); if (inst) inst.hide(); }
            }""")
            _session_project_selected = True
    except Exception as e:
        pass


@pytest.fixture(scope="session")
def page(context: BrowserContext, flask_test_server) -> Generator[Page, None, None]:
    """Create a single page for the entire test session."""
    page = context.new_page()
    page.set_default_timeout(30000)
    page.set_default_navigation_timeout(30000)

    base_url = flask_test_server

    # Select project ONCE per session
    _ensure_project_selected(page, base_url)

    # Clear field visibility localStorage once
    page.evaluate("""() => {
        Object.keys(localStorage).forEach(key => {
            if (key.includes('fieldVisibility') || key.includes('Visibility')) {
                localStorage.removeItem(key);
            }
        });
    }""")
    page.reload(wait_until="networkidle")

    page._base_url = base_url
    yield page
    page.close()


@pytest.fixture(scope="function")
def app_url(flask_test_server) -> str:
    """Provide application base URL for tests."""
    return flask_test_server


@pytest.fixture(scope="function")
def app_with_project(flask_test_server_info) -> tuple:
    """Provide (base_url, project_id) for tests that need project selection.

    Tests should navigate to /settings/projects/{project_id}/select before
    accessing pages that require a project to be selected.
    """
    return flask_test_server_info


@pytest.fixture(scope="function")
def e2e_dict_service():
    """Create a DictionaryService that uses the E2E test database (dictionary_test)."""
    from app.database.basex_connector import BaseXConnector
    from app.services.dictionary_service import DictionaryService

    test_db = os.environ.get('TEST_DB_NAME', 'dictionary_test')

    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=test_db,  # Use the E2E test database
    )
    connector.connect()

    service = DictionaryService(db_connector=connector)
    yield service

    # Cleanup
    connector.disconnect()


@pytest.fixture
def app():
    """Create Flask application for E2E tests with default project settings."""
    from app import create_app
    app = create_app('testing')
    app.config['TESTING'] = True

    # Set default project settings if not already configured
    if not app.config.get('PROJECT_SETTINGS'):
        app.config['PROJECT_SETTINGS'] = [{
            'project_name': 'test_project',
            'source_language': {'code': 'en', 'name': 'English'},
            'target_languages': [{'code': 'pl', 'name': 'Polish'}]
        }]

    return app


@pytest.fixture(autouse=True)
def shorten_playwright_timeouts(page):
    """Reduce Playwright default timeouts for faster failures in E2E.

    Many tests previously waited the default 30s for fills/selectors which
    makes the whole suite slow when elements are not present. This fixture
    shortens timeouts so failures surface quickly and tests run faster.
    """
    # 5 seconds is a reasonable balance between flakiness and speed
    page.set_default_timeout(5000)
    page.set_default_navigation_timeout(5000)
    yield


@pytest.fixture(autouse=True)
def _clear_browser_state_between_tests(page):
    """Clear accumulated browser state between tests to prevent pollution.

    Even with a session-scoped page, we need to clear state that accumulates
    from JavaScript modifications, localStorage changes, and DOM mutations.
    """
    # Store the initial URL so we can return to it after cleanup
    initial_url = page.url

    yield

    # Clear any modals that might be open
    try:
        page.evaluate("""() => {
            // Close any Bootstrap modals
            document.querySelectorAll('.modal.show').forEach(modal => {
                const inst = bootstrap.Modal.getInstance(modal);
                if (inst) inst.hide();
            });
            // Dismiss any toast notifications
            document.querySelectorAll('.toast.show, .toast:not(.hide)').forEach(toast => {
                toast.classList.add('hide');
            });
        }""")
    except Exception:
        pass

    # Clear localStorage for app-specific keys that might accumulate state
    try:
        page.evaluate("""() => {
            // Clear field visibility settings that might interfere
            Object.keys(localStorage).forEach(key => {
                if (key.includes('fieldVisibility') || key.includes('Visibility')) {
                    localStorage.removeItem(key);
                }
            });
        }""")
    except Exception:
        pass

    # Return to a clean state - navigate to about:blank briefly
    try:
        page.goto('about:blank', wait_until='domcontentloaded', timeout=5000)
    except Exception:
        pass


@pytest.fixture
def ensure_sense():
    """Helper that ensures the entry form has at least one real sense (not the template).

    Usage: call ensure_sense(page) in tests before filling sense-level fields.
    """
    def _ensure(page):
        # If a VISIBLE definition textarea is present, we assume a sense exists
        if page.locator('textarea[name*="definition"]:visible').count() == 0:
            # Try the explicit first-sense button first
            if page.locator('#add-first-sense-btn').count() > 0 and page.locator('#add-first-sense-btn').first.is_visible():
                page.click('#add-first-sense-btn')
            # Fallback to generic add-sense button
            elif page.locator('#add-sense-btn').count() > 0 and page.locator('#add-sense-btn').first.is_visible():
                page.click('#add-sense-btn')
            else:
                # Try some generic selectors used in older UIs
                generic = page.locator('.add-sense-btn, button:has-text("Add Another Sense"), button:has-text("Add Sense")')
                if generic.count() > 0 and generic.first.is_visible():
                    generic.first.click()
                else:
                    raise RuntimeError('Could not find any Add Sense button on page to create a sense')

            # Wait for a VISIBLE definition textarea to appear
            for _ in range(50):
                if page.locator('textarea[name*="definition"]:visible').count() > 0:
                    break
                page.wait_for_timeout(100)
            else:
                raise RuntimeError('Timed out waiting for visible definition textarea to appear')

    return _ensure


__all__ = [
    'browser',
    'context',
    'page',
    'flask_test_server',
    'app_url',
    'app',
    'setup_e2e_test_database',
]
