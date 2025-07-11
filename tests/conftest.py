"""
PyTest fixtures for unit testing - uses mocking instead of real database connections.
"""

from __future__ import annotations

import os
import sys
import pytest
import tempfile
import logging
from unittest.mock import Mock, MagicMock, patch
from typing import Generator

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector
from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example
from app.models.pronunciation import Pronunciation
from flask import Flask
from flask.testing import FlaskClient

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_basex_connector() -> Mock:
    """Create a mock BaseX connector for unit tests."""
    connector = Mock(spec=BaseXConnector)
    
    # Configure basic mock behavior
    connector.connect.return_value = True
    connector.disconnect.return_value = True
    connector.execute_query.return_value = "<entry id='test'>Test Entry</entry>"
    connector.execute_update.return_value = True
    connector.create_database.return_value = True
    connector.drop_database.return_value = True
    
    return connector


@pytest.fixture
def mock_dict_service(mock_basex_connector: Mock) -> Mock:
    """Create a mock dictionary service for unit tests."""
    service = Mock(spec=DictionaryService)
    
    # Configure mock behavior for common operations
    service.get_entry.return_value = None
    service.create_entry.return_value = True
    service.update_entry.return_value = True
    service.delete_entry.return_value = True
    service.list_entries.return_value = ([], 0)
    service.search_entries.return_value = ([], 0)
    service.count_entries.return_value = 150
    service.count_senses_and_examples.return_value = (300, 450)
    service.get_recent_activity.return_value = []
    service.get_system_status.return_value = {
        'db_connected': True,
        'last_backup': '2025-06-27 00:15',
        'storage_percent': 25
    }
    service.get_ranges.return_value = {
        'grammatical-info': {
            'Noun': {'label': 'Noun', 'abbrev': 'n'},
            'Verb': {'label': 'Verb', 'abbrev': 'v'}
        }
    }
    
    return service


@pytest.fixture
def app(mock_dict_service: Mock) -> Generator[Flask, None, None]:
    """Create a Flask app for unit testing with mocked dependencies."""
    from flask import Flask
    import os
    
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'templates')
    app = Flask(__name__, template_folder=template_dir)
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-for-sessions'
    })
    
    # Register blueprints
    from app.api import api_bp
    from app.api.validation import validation_bp
    from app.routes.corpus_routes import corpus_bp
    from app.views import main_bp
    from app.api.worksets import worksets_bp
    from app.api.query_builder import query_builder_bp
    from app.api.ranges import ranges_bp
    from app.views import workbench_bp
    
    app.register_blueprint(api_bp)
    app.register_blueprint(validation_bp)
    app.register_blueprint(corpus_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(worksets_bp)
    app.register_blueprint(query_builder_bp)
    app.register_blueprint(ranges_bp)
    app.register_blueprint(workbench_bp)
    
    # Mock dependency injection
    from unittest.mock import Mock
    mock_injector = Mock()
    app.injector = mock_injector
    
    # Attach mocked services
    app.dict_service = mock_dict_service
    app.dict_service_with_db = mock_dict_service
    
    # Mock cache service
    mock_cache = Mock()
    mock_cache.get.return_value = None
    mock_cache.set.return_value = True
    mock_cache.delete.return_value = True
    app.cache_service = mock_cache
    
    with app.app_context():
        yield app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Test client for unit testing with mocked dependencies."""
    return app.test_client()


# Legacy fixtures for backward compatibility
@pytest.fixture
def db_connector() -> Mock:
    """Mock BaseX connector for testing (legacy)."""
    connector = Mock(spec=BaseXConnector)
    connector.connect.return_value = True
    connector.execute_query.return_value = "<entry id='test'>Test Entry</entry>"
    return connector


@pytest.fixture
def dict_service_with_db(mock_dict_service: Mock) -> Mock:
    """Legacy alias for mock_dict_service."""
    return mock_dict_service


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


# Mock external dependencies for unit tests
@pytest.fixture(autouse=True)
def mock_external_dependencies(request):
    """Automatically mock external dependencies for all unit tests."""
    # Check if the test is marked to skip ET mocking (for LIFT parser tests)
    skip_et_mock = request.node.get_closest_marker("skip_et_mock") is not None
    
    patches = [
        patch('app.database.basex_connector.BaseXSession'),
        patch('app.services.cache_service.redis.Redis'),
    ]
    
    # Only mock ET if not explicitly skipped
    if not skip_et_mock:
        patches.append(patch('app.parsers.lift_parser.ET'))
    
    if skip_et_mock:
        # Don't mock ET for LIFT parser tests
        with patches[0] as mock_session, \
             patches[1] as mock_redis:
            
            # Configure BaseX session mock
            mock_session.return_value.execute.return_value = "<entry>test</entry>"
            mock_session.return_value.close.return_value = None
            
            # Configure Redis mock
            mock_redis.return_value.get.return_value = None
            mock_redis.return_value.set.return_value = True
            mock_redis.return_value.delete.return_value = True
            
            yield
    else:
        # Mock all dependencies including ET
        with patches[0] as mock_session, \
             patches[1] as mock_redis, \
             patches[2] as mock_et:
            
            # Configure BaseX session mock
            mock_session.return_value.execute.return_value = "<entry>test</entry>"
            mock_session.return_value.close.return_value = None
            
            # Configure Redis mock
            mock_redis.return_value.get.return_value = None
            mock_redis.return_value.set.return_value = True
            mock_redis.return_value.delete.return_value = True
            
            # Configure XML parsing mock
            mock_et.parse.return_value.getroot.return_value = Mock()
            
            yield


def ensure_test_database(connector: BaseXConnector, db_name: str):
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
    <range id="etymology-type">
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
    """Automatically mark tests based on location."""
    for item in items:
        # Mark tests as unit tests if they're in:
        # 1. Main tests directory (not integration subdirectory) - legacy location
        # 2. tests/unit/ subdirectory - new preferred location
        if (("tests/test_" in str(item.fspath) and "integration" not in str(item.fspath)) or 
            "tests/unit/" in str(item.fspath)):
            item.add_marker(pytest.mark.unit)
        
        # Mark tests as integration tests if they're in tests/integration/
        if "tests/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Only skip integration tests if explicitly running unit tests only
        if "integration" in item.keywords:
            # Check if user explicitly wants to exclude integration tests
            marker_expr = config.getoption("-m", default="")
            if marker_expr == "not integration" or marker_expr == "unit":
                item.add_marker(pytest.mark.skip(reason="integration tests excluded by marker expression"))


def pytest_addoption(parser):
    """Add command line options."""
    parser.addoption(
        "--integration", action="store_true", default=False, help="run integration tests"
    )
