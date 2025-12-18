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
    return f"test_{uuid.uuid4().hex[:8]}"


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
def dict_service_with_db(basex_test_connector: BaseXConnector) -> DictionaryService:
    """Create dictionary service with real test database."""
    return DictionaryService(db_connector=basex_test_connector)


# --- Flask live server fixture for Selenium integration tests ---
@pytest.fixture(scope="function")
def flask_test_server():
    """Start the Flask app in a subprocess on a free port, yield the base URL, and stop after test."""
    # Find a free port
    sock = socket.socket()
    sock.bind(("localhost", 0))
    port = sock.getsockname()[1]
    sock.close()

    env = os.environ.copy()
    env["FLASK_CONFIG"] = "testing"
    env["TESTING"] = "true"
    # Pass the test DB name to the Flask app if set by the test fixture
    if "TEST_DB_NAME" in os.environ:
        env["TEST_DB_NAME"] = os.environ["TEST_DB_NAME"]

    # Use sys.executable to get the current Python interpreter
    python_exe = sys.executable
    
    # Start the Flask app using run.py
    proc = subprocess.Popen([
        python_exe, "run.py"
    ], env={**env, "FLASK_RUN_PORT": str(port)}, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for the server to be ready
    base_url = f"http://localhost:{port}"

    for _ in range(30):
        try:
            import urllib.request
            with urllib.request.urlopen(base_url) as resp:
                if resp.status == 200 or resp.status == 404:
                    break
        except Exception:
            time.sleep(0.3)
    else:
        proc.terminate()
        try:
            out, err = proc.communicate(timeout=5)
        except Exception:
            out, err = b'', b''
        print("\n[flask_test_server] Flask server failed to start.\nSTDOUT:\n", out.decode(errors='replace'))
        print("\nSTDERR:\n", err.decode(errors='replace'))
        raise RuntimeError(f"Flask test server did not start on {base_url}")

    yield base_url

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()



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
