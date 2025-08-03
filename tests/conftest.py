import pytest
import uuid
import tempfile
import os
import sys
from typing import Generator

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
import logging
import subprocess
import socket
import time

@pytest.fixture
def dict_service_with_db() -> Generator[DictionaryService, None, None]:
    """Yield a DictionaryService using a unique, empty BaseX test database per test, and clean up after."""
    # Generate a unique test database name
    test_db_name = f"test_{uuid.uuid4().hex[:8]}"
    os.environ["TEST_DB_NAME"] = test_db_name
    connector = BaseXConnector(database=test_db_name)
    # Ensure the test database is created and initialized
    ensure_test_database(connector, test_db_name)
    service = DictionaryService(db_connector=connector)
    try:
        yield service
    finally:
        # Robustly drop the test database after the test
        try:
            # Ensure connector is connected
            if not getattr(connector, 'session', None):
                connector.connect()
            connector.execute_update(f"db:drop('{test_db_name}')")
            logger.info(f"Dropped test database: {test_db_name}")
        except Exception as e:
            logger.warning(f"Failed to drop test database {test_db_name}: {e}")
        finally:
            try:
                connector.disconnect()
            except Exception:
                pass

logger = logging.getLogger(__name__)


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

    # Start the Flask app using run.py
    proc = subprocess.Popen([
        "python", "run.py"
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




def ensure_test_database(connector: BaseXConnector, db_name: str):
    logger.info(f"Ensuring test database '{db_name}' exists.")
    """
    Ensure a test database exists and is properly initialized with minimal LIFT content.
    
    Args:
        connector: BaseX connector instance
        db_name: Name of the test database
    """
    try:
        # Check if database exists, create if not
        try:
            exists_result = connector.execute_query(f"db:exists('{db_name}')")
            exists = exists_result.strip().lower() == 'true'
        except Exception:
            exists = False
            
        if not exists:
            connector.create_database(db_name)
            logger.info(f"Created test database: {db_name}")
        
        # Ensure database has minimal LIFT structure
        try:
            result = connector.execute_query("count(//entry)")
            entry_count = int(result.strip()) if result.strip().isdigit() else 0
        except Exception:
            entry_count = 0
            
        if entry_count == 0:
            # Add minimal LIFT structure
            minimal_lift = '''<lift version="0.13" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
    <entry id="test_entry_1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="test_sense_1">
            <definition>
                <form lang="en"><text>A test entry</text></form>
            </definition>
        </sense>
    </entry>
</lift>'''
            
            try:
                # Try different methods to add content
                connector.execute_update(f"db:replace('{db_name}', '{minimal_lift}', 'lift.xml')")
                logger.info(f"Added minimal LIFT content to test database: {db_name}")
            except Exception as e:
                logger.warning(f"Failed to add content to test database {db_name}: {e}")
        
        # Ensure ranges.xml exists in the database
        try:
            result = connector.execute_query("doc('ranges.xml')")
            ranges_exist = bool(result and len(result.strip()) > 0)
        except Exception:
            ranges_exist = False
            
        if not ranges_exist:
            # Add sample ranges.xml
            ranges_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <range id="grammatical-info">
        <range-element id="Noun" label="Noun" abbrev="n">
            <description>This is a noun.</description>
        </range-element>
        <range-element id="Verb" label="Verb" abbrev="v">
            <description>This is a verb.</description>
        </range-element>
        <range-element id="Adjective" label="Adjective" abbrev="adj">
            <description>This is an adjective.</description>
        </range-element>
        <range-element id="Adverb" label="Adverb" abbrev="adv">
            <description>This is an adverb.</description>
        </range-element>
        <range-element id="Pronoun" label="Pronoun" abbrev="pr">
            <description>This is a pronoun.</description>
        </range-element>
        <range-element id="Preposition" label="Preposition" abbrev="pre">
            <description>This is a preposition.</description>
        </range-element>
        <range-element id="Conjunction" label="Conjunction" abbrev="conj">
            <description>This is a conjunction.</description>
        </range-element>
        <range-element id="Interjection" label="Interjection" abbrev="int">
            <description>This is an interjection.</description>
        </range-element>
    </range>
    <range id="variant-type">
        <range-element id="dialectal" label="Dialectal Variant">
            <description>A dialect variant</description>
        </range-element>
        <range-element id="orthographic" label="Orthographic Variant">
            <description>Alternative spelling</description>
        </range-element>
    </range>
    <range id="relation-type">
        <range-element id="synonym" label="Synonym">
            <description>Words with same meaning</description>
        </range-element>
        <range-element id="antonym" label="Antonym">
            <description>Words with opposite meaning</description>
        </range-element>
    </range>
    <range id="academic-domain">
        <range-element id="linguistics" label="Linguistics">
            <description>Linguistic terminology</description>
        </range-element>
        <range-element id="mathematics" label="Mathematics">
            <description>Mathematical terminology</description>
        </range-element>
    </range>
    <range id="usage-type">
        <range-element id="formal" label="Formal">
            <description>Formal language</description>
        </range-element>
        <range-element id="informal" label="Informal">
            <description>Informal or colloquial language</description>
        </range-element>
    </range>
    <range id="etymology">
        <range-element id="borrowed" label="Borrowed">
            <description>A word borrowed from another language.</description>
        </range-element>
        <range-element id="proto" label="Proto-language">
            <description>A reconstructed word from a proto-language.</description>
        </range-element>
    </range>
    <range id="semantic-domain">
        <range-element id="agriculture" label="Agriculture">
            <description>Related to farming and agriculture.</description>
        </range-element>
        <range-element id="technology" label="Technology">
            <description>Related to technology and engineering.</description>
        </range-element>
    </range>
</lift-ranges>'''
            
            try:
                connector.execute_update(f"db:add('{db_name}', '{ranges_xml}', 'ranges.xml')")
                logger.info(f"Added sample ranges.xml to test database: {db_name}")
            except Exception as e:
                logger.warning(f"Failed to add ranges.xml to test database {db_name}: {e}")
                
    except Exception as e:
        logger.error(f"Failed to ensure test database {db_name}: {e}")
        raise


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
    """Marks tests based on their location: `unit` or `integration`."""
    for item in items:
        path = str(item.fspath).replace('\\', '/')  # Normalize path separators
        if "tests/unit/" in path:
            item.add_marker(pytest.mark.unit)
        elif "tests/integration/" in path:
            item.add_marker(pytest.mark.integration)

    # Deselect tests not in unit or integration folders
    selected_items = []
    deselected_items = []

    for item in items:
        path = str(item.fspath).replace('\\', '/')  # Normalize path separators
        if "tests/unit/" in path or "tests/integration/" in path:
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
