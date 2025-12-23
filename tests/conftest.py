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
    """Generate a unique test database name."""
    return generate_safe_db_name('unit')


@pytest.fixture(scope="function")
def safe_test_db_name(request) -> str:
    """
    Generate a safe, unique test database name.
    
    Determines test type from the request path and generates
    an appropriate safe database name.
    """
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
    """Create BaseX connector with isolated test database."""
    if not basex_available:
        pytest.skip("BaseX server not available")
    
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
        connector.create_database(test_db_name)
        
        # Now set the database name and reconnect
        connector.database = test_db_name
        connector.disconnect()
        connector.connect()  # Reconnect with the database
        
        # Add sample LIFT content using BaseX command
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
        
        # Use BaseX ADD command to add the document to the database
        try:
            connector.execute_command(f"ADD {temp_file}")
            logger.info("Added LIFT data to test database using ADD command")
        except Exception as e:
            logger.warning(f"Failed to add data with ADD command: {e}")
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except OSError:
                pass
        
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
</lift-ranges>'''
            f.write(ranges_xml)
            temp_file = f.name
        
        try:
            connector.execute_command(f"ADD {temp_file}")
            logger.info("Added ranges.xml to test database")
        except Exception as e:
            logger.warning(f"Failed to add ranges.xml: {e}")
        finally:
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

            cleanup_connector = BaseXConnector(
                host=os.getenv('BASEX_HOST', 'localhost'),
                port=int(os.getenv('BASEX_PORT', '1984')),
                username=os.getenv('BASEX_USERNAME', 'admin'),
                password=os.getenv('BASEX_PASSWORD', 'admin'),
                database=None,
            )
            cleanup_connector.connect()
            cleanup_connector.drop_database(test_db_name)
            logger.info(f"Dropped test database: {test_db_name}")
        except Exception as e:
            logger.warning(f"Failed to drop test database {test_db_name}: {e}")
        finally:
            try:
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
        
        # Connect and create database
        connector.connect()
        connector.create_database(safe_test_db_name)
        connector.database = safe_test_db_name
        connector.disconnect()
        connector.connect()  # Reconnect with database
        
        logger.info(f"Created isolated test database: {safe_test_db_name}")
        
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
    """Create dictionary service with real test database."""
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

    # Create the app with testing config and ensure BASEX_DATABASE matches TEST_DB_NAME
    app = create_app(os.getenv('FLASK_CONFIG') or 'testing')
    app.config['TESTING'] = True

    # Prefer explicit TEST_DB_NAME if present
    env_db = os.environ.get('TEST_DB_NAME') or os.environ.get('BASEX_DATABASE')
    if env_db:
        app.config['BASEX_DATABASE'] = env_db
    else:
        # If not provided, ensure tests don't accidentally use production db
        app.config['BASEX_DATABASE'] = app.config.get('BASEX_DATABASE', 'dictionary_test')

    # Export to environment so other services/readers see the same value
    os.environ['BASEX_DATABASE'] = app.config['BASEX_DATABASE']
    os.environ['TEST_DB_NAME'] = app.config['BASEX_DATABASE']

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

        yield base_url

    finally:
        try:
            server.shutdown()
        except Exception:
            pass
        if thread and thread.is_alive():
            thread.join(timeout=1)



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

    # Deselect tests not in unit, integration, or e2e folders
    selected_items = []
    deselected_items = []

    for item in items:
        path = str(item.fspath).replace('\\', '/')  # Normalize path separators
        if "tests/unit/" in path or "tests/integration/" in path or "tests/e2e/" in path:
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
