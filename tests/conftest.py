import pytest
import uuid
import tempfile
import os
import sys
from typing import Generator

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set testing config by default so create_app() uses in-memory SQLite and test DB
os.environ.setdefault('FLASK_CONFIG', 'testing')

# Import safety utilities
from tests.test_db_safety_utils import generate_safe_db_name, is_safe_database_name

# Ensure TEST_DB_NAME is set at import time for any tests that call create_app()
# at module import time. This avoids race conditions where some test modules
# instantiate the Flask app before session fixtures run.
if os.environ.get('TEST_DB_NAME') is None:
    try:
        # Generate a safe database name instead of a random one
        test_db = generate_safe_db_name('session')
        os.environ['TEST_DB_NAME'] = test_db
        # Also set BASEX_DATABASE so create_app('testing') picks the same name
        os.environ['BASEX_DATABASE'] = test_db

        from tests.basex_test_utils import create_test_db
        # Try to create the DB (best-effort)
        create_test_db(test_db)
    except Exception:
        # If BaseX isn't available now, continue; the fixtures will skip tests that require it
        pass

from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
import logging
import subprocess
import socket
import time

logger = logging.getLogger(__name__)


@pytest.fixture(scope="class")
def basex_available() -> bool:
    """Check if BaseX server is available."""
    try:
        connector = BaseXConnector(
            host=os.getenv('BASEX_HOST', 'localhost'),
            port=int(os.getenv('BASEX_PORT', '1984')),
            username=os.getenv('BASEX_USERNAME', 'admin'),
            password=os.getenv('BASEX_PASSWORD', 'admin'),
            database=None,  # Don't try to open a specific database
        )
        # Just test the session creation without opening a database
        from BaseXClient.BaseXClient import Session as BaseXSession
        session = BaseXSession(connector.host, connector.port, connector.username, connector.password)
        session.close()
        return True
    except Exception as e:
        logger.warning(f"BaseX server not available: {e}")
        return False


@pytest.fixture(scope="function")
def test_db_name() -> str:
    """
    Generate a unique test database name.

    Uses TEST_DB_NAME if already set (e.g., by Flask app initialization at import time),
    otherwise generates a new unique name. This ensures consistency between the Flask app
    and test fixtures.
    """
    # Use TEST_DB_NAME if already set (set at module import time for Flask compatibility)
    if os.environ.get('TEST_DB_NAME'):
        return os.environ['TEST_DB_NAME']
    return generate_safe_db_name('unit')


@pytest.fixture(scope="function")
def safe_test_db_name(request) -> str:
    """
    Generate a safe, unique test database name.

    Determines test type from the request path and generates
    an appropriate safe database name. Uses TEST_DB_NAME if already set
    to ensure consistency with Flask app initialization.
    """
    # Use TEST_DB_NAME if already set (set at module import time for Flask compatibility)
    if os.environ.get('TEST_DB_NAME'):
        db_name = os.environ['TEST_DB_NAME']
    else:
        # Determine test type from request
        test_path = str(request.fspath).replace('\\', '/')  # Normalize path separators
        if "e2e" in test_path:
            test_type = "e2e"
        elif "integration" in test_path:
            test_type = "integration"
        else:
            test_type = "unit"

        db_name = generate_safe_db_name(test_type)

    # Validate safety
    if not is_safe_database_name(db_name):
        pytest.fail(f"Generated unsafe database name: {db_name}")

    return db_name


@pytest.fixture(scope="function")
def basex_test_connector(basex_available: bool, test_db_name: str):
    """Create BaseX connector with isolated test database.

    For integration tests that set TEST_DB_NAME (session-scoped), this fixture
    uses the shared database name. For unit tests, it creates an isolated database.
    """
    if not basex_available:
        pytest.skip("BaseX server not available")

    # Check if we should use a shared database (set by session-scoped fixture for integration tests)
    shared_db_name = os.environ.get('TEST_DB_NAME')
    use_shared_db = shared_db_name is not None

    # Use shared DB name if available, otherwise use the function-scoped test_db_name
    db_name = shared_db_name if use_shared_db else test_db_name

    # First create connector without database to create the database
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=None,  # No database initially
    )

    try:
        # Connect without opening a database
        connector.connect()

        # Create the test database
        if use_shared_db:
            # For shared DB, try to create but ignore if it exists or is locked
            # (another fixture or process may have already created it)
            try:
                connector.create_database(db_name)
            except Exception:
                # Assuming it exists or is in use, which is fine for shared DB
                pass
        else:
            # For isolated DB, explicit creation is expected to succeed
            connector.create_database(db_name)

        # Now set the database name and reconnect
        connector.database = db_name
        connector.disconnect()
        connector.connect()  # Reconnect with the database

        # Check if test_entry_1 already exists to avoid duplicates
        try:
            check_query = "xquery exists(collection('" + db_name + "')//*:entry[@id='test_entry_1'])"
            entry_exists = connector.execute_query(check_query)
            if entry_exists and entry_exists.strip().lower() == 'true':
                logger.info("test_entry_1 already exists, skipping ADD")
            else:
                # Add sample LIFT content using BaseX command
                # For shared DB, we add data every time because other fixtures may have cleared it
                with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
                    sample_lift = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
    <entry id="test_entry_1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="test_sense_1">
            <definition>
                <form lang="en"><text>A test entry</text></form>
            </definition>
            <gloss lang="pl"><text>test</text></gloss>
        </sense>
        <variant type="spelling">
            <form lang="en"><text>teest</text></form>
            <trait name="type" value="spelling"/>
        </variant>
        <relation type="_component-lexeme" ref="other">
            <trait name="variant-type" value="dialectal"/>
        </relation>
    </entry>
</lift>'''
                    f.write(sample_lift)
                    temp_file = f.name

                # Add sample data - for shared DB always add, for isolated DB add once
                try:
                    connector.execute_command(f"ADD {temp_file}")
                    logger.info(f"Added LIFT data to {'shared' if use_shared_db else 'isolated'} test database")
                except Exception as e:
                    logger.warning(f"Failed to add data with ADD command: {e}")

                # Clean up temp file (always)
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass
        except Exception as e:
            logger.warning(f"Failed to check for existing entries: {e}")

        # Add ranges.xml similarly
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            ranges_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <range id="grammatical-info">
        <range-element id="Noun" label="Noun" abbrev="n"/>
        <range-element id="Verb" label="Verb" abbrev="v"/>
        <range-element id="Adjective" label="Adjective" abbrev="adj"/>
    </range>
    <range id="usage-type">
        <range-element id="dialect" label="Dialect"/>
        <range-element id="register" label="Register"/>
    </range>
    <range id="semantic-domain">
        <range-element id="sd-1" label="Semantic Domain 1"/>
        <range-element id="sd-2" label="Semantic Domain 2"/>
    </range>
    <range id="academic-domain">
        <range-element id="academics" label="Academics"/>
        <range-element id="general" label="General"/>
    </range>
    <range id="variant-type">
        <range-element id="spelling" label="Spelling Variant"/>
        <range-element id="dialectal" label="Dialectal Variant"/>
    </range>
    <range id="lexical-relation">
        <range-element id="synonym" label="Synonym"/>
        <range-element id="antonym" label="Antonym"/>
        <range-element id="hypernym" label="Hypernym"/>
        <range-element id="hyponym" label="Hyponym"/>
        <range-element id="component-lexeme" label="Component Lexeme"/>
    </range>
</lift-ranges>'''
            f.write(ranges_xml)
            temp_file = f.name

        # Add ranges - always add for shared DB (ranges may have been cleared), add once for isolated
        try:
            connector.execute_command(f"ADD {temp_file}")
            logger.info(f"Added ranges.xml to {'shared' if use_shared_db else 'isolated'} test database")
        except Exception as e:
            logger.warning(f"Failed to add ranges.xml: {e}")

        # Clean up temp file (always)
        try:
            os.unlink(temp_file)
        except OSError:
            pass

        yield connector
        
    finally:
        # Clean up test database
        try:
            try:
                connector.disconnect()
            except Exception:
                pass

            # Only drop if it's NOT a shared database (shared DB is dropped by session fixture)
            if not use_shared_db:
                cleanup_connector = BaseXConnector(
                    host=os.getenv('BASEX_HOST', 'localhost'),
                    port=int(os.getenv('BASEX_PORT', '1984')),
                    username=os.getenv('BASEX_USERNAME', 'admin'),
                    password=os.getenv('BASEX_PASSWORD', 'admin'),
                    database=None,
                )
                cleanup_connector.connect()
                cleanup_connector.drop_database(db_name)
                logger.info(f"Dropped isolated test database: {db_name}")
                cleanup_connector.disconnect()
        except Exception as e:
            logger.warning(f"Failed to drop test database {db_name}: {e}")
            try:
                if 'cleanup_connector' in locals():
                    cleanup_connector.disconnect()
            except Exception:
                pass


@pytest.fixture(scope="function")
def isolated_basex_connector(safe_test_db_name: str, basex_available: bool, request) -> Generator[BaseXConnector, None, None]:
    """
    Create a completely isolated BaseX connector with safe cleanup.
    
    This fixture provides stronger isolation guarantees than basex_test_connector:
    - Uses safe database naming with timestamp and test type
    - Validates database name safety before creation
    - Restores original environment variables after test
    - Performs atomic cleanup with verification
    - Prevents environment variable leakage between tests
    """
    if not basex_available:
        pytest.skip("BaseX server not available")
    
    # Store original environment variables for restoration
    original_test_db = os.environ.get('TEST_DB_NAME')
    original_basex_db = os.environ.get('BASEX_DATABASE')
    
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=None,
    )
    
    try:
        # Set isolated environment for this test only
        os.environ['TEST_DB_NAME'] = safe_test_db_name
        os.environ['BASEX_DATABASE'] = safe_test_db_name
        
        # Connect and create database (retry with unique suffix if DB is in use)
        connector.connect()
        chosen_db = safe_test_db_name
        max_attempts = 3
        from app.utils.exceptions import DatabaseError
        for attempt in range(1, max_attempts + 1):
            try:
                connector.create_database(chosen_db)
                break
            except Exception as e:  # Be tolerant and try alternate name on typical collisions
                err_text = str(e)
                logger.warning(f"Attempt {attempt} to create DB {chosen_db} failed: {err_text}")
                # If DB is opened by another process or already exists in a conflicting state,
                # try a new name with a short random suffix to avoid collision.
                if 'opened by another process' in err_text or 'already exists' in err_text.lower():
                    chosen_db = f"{safe_test_db_name}_{uuid.uuid4().hex[:6]}"
                    # update env vars so subsequent operations use the tentative name
                    os.environ['TEST_DB_NAME'] = chosen_db
                    os.environ['BASEX_DATABASE'] = chosen_db
                    # wait briefly before retrying to allow transient locks to clear
                    time.sleep(0.2)
                    connector = BaseXConnector(
                        host=os.getenv('BASEX_HOST', 'localhost'),
                        port=int(os.getenv('BASEX_PORT', '1984')),
                        username=os.getenv('BASEX_USERNAME', 'admin'),
                        password=os.getenv('BASEX_PASSWORD', 'admin'),
                        database=None,
                    )
                    connector.connect()
                    continue
                # otherwise, propagate the unexpected error
                raise
        else:
            raise DatabaseError(f"Failed to create an isolated test database after {max_attempts} attempts")

        # Use the chosen database name going forward and ensure connector uses it
        connector.database = chosen_db
        connector.disconnect()
        connector.connect()  # Reconnect with database
        
        logger.info(f"Created isolated test database: {chosen_db}")
        
        # Add sample LIFT content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            sample_lift = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
    <entry id="test_entry_1">
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
</lift>'''
            f.write(sample_lift)
            temp_file = f.name
        
        try:
            connector.execute_command(f"ADD {temp_file}")
            logger.info("Added LIFT data to isolated test database")
        except Exception as e:
            logger.warning(f"Failed to add data to isolated database: {e}")
        finally:
            try:
                os.unlink(temp_file)
            except OSError:
                pass
        
        # Add minimal ranges.xml
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            ranges_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <range id="grammatical-info">
        <range-element id="Noun" label="Noun" abbrev="n"/>
        <range-element id="Verb" label="Verb" abbrev="v"/>
    </range>
    <range id="lexical-relation">
        <range-element id="synonym" label="Synonym"/>
        <range-element id="antonym" label="Antonym"/>
    </range>
</lift-ranges>'''
            f.write(ranges_xml)
            temp_file = f.name
        
        try:
            connector.execute_command(f"ADD {temp_file}")
            logger.info("Added ranges.xml to isolated test database")
        except Exception as e:
            logger.warning(f"Failed to add ranges.xml to isolated database: {e}")
        finally:
            try:
                os.unlink(temp_file)
            except OSError:
                pass
        
        yield connector
        
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
                    if safe_test_db_name in result:
                        cleanup_connector.execute_command(f"DROP DB {safe_test_db_name}")
                        logger.info(f"Successfully dropped isolated test database: {safe_test_db_name}")
                    else:
                        logger.warning(f"Isolated test database {safe_test_db_name} not found during cleanup")
                except Exception as e:
                    logger.warning(f"Could not verify database existence before cleanup: {e}")
                
            finally:
                try:
                    cleanup_connector.disconnect()
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Failed to clean up isolated test database {safe_test_db_name}: {e}")
            # Even if cleanup fails, we've restored the environment variables
            raise


@pytest.fixture(scope="function")
def dict_service_with_db(basex_test_connector: BaseXConnector) -> DictionaryService:
    """Create dictionary service with real test database.

    For integration tests using a shared session-scoped database (via TEST_DB_NAME),
    this fixture correctly uses the shared database. For unit tests, it creates
    an isolated database per test function.
    """
    return DictionaryService(db_connector=basex_test_connector)


# --- Flask live server fixture for Selenium integration tests ---
@pytest.fixture(scope="function")
def flask_test_server():
    """Start the Flask app in-process on a free port using Werkzeug's WSGI server.

    This avoids subprocess env var races and ensures the Flask app uses the
    same TEST_DB_NAME / BASEX_DATABASE that test fixtures set, preventing e2e
    tests from accidentally operating on production databases.
    """
    from werkzeug.serving import make_server
    from app import create_app

    # Find a free port
    sock = socket.socket()
    sock.bind(("localhost", 0))
    port = sock.getsockname()[1]
    sock.close()

    # Load .env for PostgreSQL settings (has correct WSL IP 172.17.96.1)
    # This is critical for E2E tests that need PostgreSQL for worksets
    from dotenv import load_dotenv
    load_dotenv('/mnt/d/Dokumenty/slownik-wielki/flask-app/.env', override=True)

    # Create the app with testing config
    app = create_app(os.getenv('FLASK_CONFIG') or 'testing')

    # Force E2E mode AFTER app creation - this is essential for PostgreSQL
    # We manually create PostgreSQL connection since TestingConfig has TESTING=True
    # which would normally skip it
    import psycopg2
    # Retry connecting to PostgreSQL a few times to handle transient network issues
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            pg_pool = psycopg2.pool.SimpleConnectionPool(
                1, 20,
                user=app.config.get("PG_USER"),
                password=app.config.get("PG_PASSWORD"),
                host=app.config.get("PG_HOST"),
                port=app.config.get("PG_PORT"),
                database=app.config.get("PG_DATABASE"),
                connect_timeout=5
            )
            app.pg_pool = pg_pool
            # Create workset tables (may raise if DB not ready)
            from app.database.workset_db import create_workset_tables
            create_workset_tables(pg_pool)
            print(f"Successfully connected to PostgreSQL at {app.config.get('PG_HOST')}:{app.config.get('PG_PORT')} (attempt {attempt})")
            break
        except Exception as e:
            print(f"Warning: Attempt {attempt} to connect to PostgreSQL failed: {e}")
            app.pg_pool = None
            if attempt < max_attempts:
                import time
                time.sleep(1)
            else:
                print("Warning: Could not connect to PostgreSQL after multiple attempts; continuing with app.pg_pool=None")

    # Prefer explicit TEST_DB_NAME if present
    env_db = os.environ.get('TEST_DB_NAME') or os.environ.get('BASEX_DATABASE')
    if env_db:
        app.config['BASEX_DATABASE'] = env_db
    else:
        # If not provided, ensure tests don't accidentally use production db
        # Use a safe name that passes the safety check (starts with 'test_', no protected patterns)
        app.config['BASEX_DATABASE'] = app.config.get('BASEX_DATABASE', 'test_entries_db')

    # Export to environment so other services/readers see the same value
    os.environ['BASEX_DATABASE'] = app.config['BASEX_DATABASE']
    os.environ['TEST_DB_NAME'] = app.config['BASEX_DATABASE']
    
    # Create default project settings in the app's database
    project_id = None
    with app.app_context():
        from app.config_manager import ConfigManager
        from app.models.project_settings import ProjectSettings

        # Check if project exists, if not create it
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
            # Commit is handled by create_settings

    server = make_server('localhost', port, app)
    thread = None
    try:
        import threading
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        base_url = f"http://localhost:{port}"

        # Wait for server to be ready (simple health check)
        import urllib.request
        for _ in range(30):
            try:
                with urllib.request.urlopen(base_url) as resp:
                    if resp.status in (200, 404):
                        break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError(f"Flask test server did not start on {base_url}")

        # Store project_id in a global for the fixture to access
        # This is a workaround to avoid changing the fixture return type
        flask_test_server._project_id = project_id  # type: ignore

        # Set the test app reference for test utilities
        from tests.test_app_utils import set_test_app
        set_test_app(app)

        yield base_url

    finally:
        # Reset the test app reference
        from tests.test_app_utils import reset_test_app
        reset_test_app()

        try:
            server.shutdown()
        except Exception:
            pass
        if thread and thread.is_alive():
            thread.join(timeout=1)


@pytest.fixture
def flask_test_server_info(flask_test_server) -> tuple:
    """Return (base_url, project_id) from flask_test_server fixture.

    Use this fixture when you need both the base URL and the project ID.
    """
    project_id = getattr(flask_test_server, '_project_id', None)
    return flask_test_server, project_id



@pytest.fixture
def sample_entry() -> Entry:
    """Create a sample Entry object for testing."""
    entry = Entry(
        id_="test_entry",
        lexical_unit={"en": "test"},
        pronunciations={"seh-fonipa": "test"},
        grammatical_info="noun"
    )
    
    # Add a sense
    sense = Sense(
        id_="sense1",
        glosses={"pl": "test"},
        definitions={"en": "to try something"}
    )
    
    # Add an example to the sense
    example = Example(
        id_="example1",
        forms={"en": "This is a test."},
        translations={"pl": "To jest test."}
    )
    
    sense.examples.append(example)
    entry.senses.append(sense)
    
    return entry


@pytest.fixture
def sample_entry_with_pronunciation() -> Entry:
    """Create a sample Entry object with a specific pronunciation for testing."""
    entry = Entry(
        id_="test_pronunciation_entry",
        lexical_unit={"en": "pronunciation test"},
        pronunciations={"seh-fonipa": "/pro.nun.si.eɪ.ʃən/"},
        grammatical_info="noun"
    )
    return entry


@pytest.fixture
def sample_entries() -> list[Entry]:
    """Create a list of sample Entry objects for testing."""
    entries = []
    
    # Create 10 sample entries
    for i in range(10):
        entry = Entry(
            id_=f"entry_{i}",
            lexical_unit={"en": f"word_{i}"},
            grammatical_info="noun" if i % 2 == 0 else "verb"
        )
        
        # Add a sense
        sense = Sense(
            id_=f"sense_{i}",
            glosses={"pl": f"słowo_{i}"},
            definitions={"en": f"Definition for word_{i}"}
        )
        
        entry.senses.append(sense.to_dict())  # type: ignore
        entries.append(entry)
    
    return entries


@pytest.fixture
def temp_lift_file() -> Generator[str, None, None]:
    """Create a temporary LIFT file for testing."""
    content = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test_1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
            <form lang="pl"><text>test</text></form>
        </lexical-unit>
        <sense id="sense1">
            <definition>
                <form lang="pl"><text>Test definition</text></form>
            </definition>
            <gloss lang="en"><text>Test gloss</text></gloss>
            <grammatical-info value="Noun"/>
        </sense>
    </entry>
</lift>'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    try:
        os.unlink(temp_path)
    except OSError as e:
        logger.warning(f"Could not delete temp file {temp_path}: {e}")


@pytest.fixture
def populated_dict_service(dict_service_with_db: DictionaryService, sample_entry: Entry) -> DictionaryService:
    """Dictionary service with sample data."""
    try:
        dict_service_with_db.create_entry(sample_entry)
    except Exception as e:
        logger.warning(f"Could not create sample entry: {e}")
    
    return dict_service_with_db


# Unit test configuration
def pytest_configure(config):
    """Configure pytest for unit tests."""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (uses mocking)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires real database)"
    )
    config.addinivalue_line(
        "markers", "skip_et_mock: skip ET module mocking for tests that need real XML parsing"
    )
    config.addinivalue_line(
        "markers", "javascript: mark test as JavaScript test"
    )
    config.addinivalue_line(
        "markers", "js_lint: mark test as JavaScript linting test"
    )


def pytest_collection_modifyitems(config, items):
    """Marks tests based on their location: `unit`, `integration`, or `e2e`."""
    for item in items:
        path = str(item.fspath).replace('\\', '/')  # Normalize path separators
        if "tests/unit/" in path:
            item.add_marker(pytest.mark.unit)
        elif "tests/integration/" in path:
            item.add_marker(pytest.mark.integration)
        elif "tests/e2e/" in path:
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.integration)  # E2E tests are also integration tests

    # Deselect tests not in unit, integration, e2e, or js test folders
    selected_items = []
    deselected_items = []

    for item in items:
        path = str(item.fspath).replace('\\', '/')  # Normalize path separators
        if ("tests/unit/" in path or
            "tests/integration/" in path or
            "tests/e2e/" in path):
            selected_items.append(item)
        else:
            deselected_items.append(item)

    items[:] = selected_items
    if deselected_items:
        config.hook.pytest_deselected(items=deselected_items)


def pytest_addoption(parser):
    """Add command line options."""
    parser.addoption(
        "--integration", action="store_true", default=False, help="run integration tests"
    )


def pytest_ignore_collect(path, config):
    """Ignore collection for legacy, problematic test modules.

    This is a temporary safety net to prevent flaky or corrupted legacy
    modules from causing whole-suite collection failures while we
    continue converting tests to the canonical, clean modules.
    """
    try:
        # path may be a py.path.local or pathlib.Path; normalize to string
        p = str(path)
    except Exception:
        return False

    if p.endswith("tests/integration/test_ranges_elements_crud.py"):
        return True
