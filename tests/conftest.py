"""
PyTest fixtures for testing the dictionary writing system.
"""

from __future__ import annotations

import os
import sys
import pytest
import tempfile
import uuid
import logging
from unittest.mock import patch, MagicMock
from typing import Generator, Any

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example
from app.models.pronunciation import Pronunciation
from flask import Flask
from flask.testing import FlaskClient

logger = logging.getLogger(__name__)


@pytest.fixture(scope="class")  # Changed to class scope to match search_service fixture
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
            # Try alternative approach - use REPLACE command to add root document
            try:
                connector.execute_update(f"db:replace('{test_db_name}', '{temp_file}', 'lift.xml')")
                logger.info("Added LIFT data to test database using REPLACE command")
            except Exception as e2:
                logger.warning(f"Failed to add data with REPLACE command: {e2}")
                # Final fallback - directly insert LIFT XML
                try:
                    lift_xml = sample_lift.replace('<?xml version="1.0" encoding="UTF-8"?>\n', '')
                    connector.execute_update(f"db:add('{test_db_name}', '{lift_xml}', 'lift.xml')")
                    logger.info("Added LIFT data to test database using db:add function")
                except Exception as e3:
                    logger.error(f"All methods failed to add data: {e3}")
                    # Create a minimal database structure
                    try:
                        minimal_lift = '<lift version="0.13"></lift>'
                        connector.execute_update(f"db:add('{test_db_name}', '{minimal_lift}', 'lift.xml')")
                        logger.info("Created minimal LIFT structure in test database")
                    except Exception as e4:
                        logger.error(f"Failed to create minimal structure: {e4}")
        
        # Clean up temp file
        try:
            os.unlink(temp_file)
        except OSError:
            pass
            
        logger.info(f"Created test database: {test_db_name}")
        
        yield connector
        
    except Exception as e:
        logger.error(f"Failed to setup BaseX test connector: {e}")
        pytest.skip(f"Could not setup BaseX connection: {e}")
    finally:
        # Cleanup: drop test database and disconnect
        try:
            if connector._session:  # Check the actual session attribute
                connector.drop_database(test_db_name)
                logger.info(f"Dropped test database: {test_db_name}")
                connector.disconnect()
        except Exception as e:
            logger.warning(f"Could not cleanup test database {test_db_name}: {e}")


@pytest.fixture(scope="function")
def basex_connector(basex_available: bool):
    """Create BaseX connector using existing dictionary database."""
    if not basex_available:
        pytest.skip("BaseX server not available")
    
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database='dictionary',  # Use existing dictionary database
        
    )
    
    try:
        # Connect to existing database
        connector.connect()
        yield connector
        
    except Exception as e:
        logger.error(f"Failed to setup BaseX test connector: {e}")
        pytest.skip(f"Could not setup BaseX connection: {e}")
    finally:
        # Cleanup: just disconnect
        try:
            if connector.session:
                connector.disconnect()
        except Exception as e:
            logger.warning(f"Could not disconnect from BaseX: {e}")


@pytest.fixture(scope="function")
def dict_service_with_db(basex_test_connector: BaseXConnector) -> DictionaryService:
    """Create dictionary service with real test database."""
    return DictionaryService(db_connector=basex_test_connector)


@pytest.fixture(scope="function") 
def dict_service_with_test_db(basex_available: bool):
    """Create a dictionary service with a properly initialized test database."""
    if not basex_available:
        pytest.skip("BaseX server not available")
    
    test_db_name = f"test_{uuid.uuid4().hex[:8]}"
    
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=test_db_name,
        
    )
    
    try:
        connector.connect()
        ensure_test_database(connector, test_db_name)
        
        service = DictionaryService(db_connector=connector)
        
        yield service
        
    except Exception as e:
        logger.error(f"Failed to setup test dictionary service: {e}")
        pytest.skip(f"Could not setup test database: {e}")
    finally:
        # Cleanup
        try:
            if connector.session:
                connector.drop_database(test_db_name)
                logger.info(f"Dropped test database: {test_db_name}")
                connector.disconnect()
        except Exception as e:
            logger.warning(f"Could not cleanup test database {test_db_name}: {e}")


@pytest.fixture
def app(dict_service_with_db: DictionaryService) -> Generator[Flask, None, None]:
    """Create and configure a Flask app for testing with real database."""
    # Create a minimal Flask app for testing with correct template directory
    from flask import Flask
    import os
    
    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'app', 'templates')
    app = Flask(__name__, template_folder=template_dir)
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
    })
    
    # Register the main API blueprint
    from app.api import api_bp
    app.register_blueprint(api_bp)
    
    # Register the validation blueprint
    from app.api.validation import validation_bp
    app.register_blueprint(validation_bp)
    
    # Register the corpus routes blueprint
    from app.routes.corpus_routes import corpus_bp
    app.register_blueprint(corpus_bp)
    
    # Register the main views blueprint
    from app.views import main_bp
    app.register_blueprint(main_bp)
    
    # Register the worksets blueprint
    from app.api.worksets import worksets_bp
    app.register_blueprint(worksets_bp)
    
    # Register the query builder blueprint
    from app.api.query_builder import query_builder_bp
    app.register_blueprint(query_builder_bp)
    
    # Register the workbench views blueprint
    from app.views import workbench_bp
    app.register_blueprint(workbench_bp)
    
    # Attach the test dictionary service (use the same instance as dict_service_with_db)
    app.dict_service = dict_service_with_db  # type: ignore
    app.dict_service_with_db = dict_service_with_db  # type: ignore - alias for compatibility
    
    # Create application context
    with app.app_context():
        yield app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Test client for the application."""
    return app.test_client()


@pytest.fixture
def db_connector() -> Generator[BaseXConnector, None, None]:
    """Mock BaseX connector for testing."""
    with patch('app.database.basex_connector.BaseXSession'):
        connector = BaseXConnector(
            host='localhost',
            port=1984,
            username='admin',
            password='admin',
            database='test_dictionary',
            
        )
        
        # Configure the mock
        connector.connect = lambda: True
        connector.execute_query = lambda query, **kwargs: "<entry id='test'>Test Entry</entry>"  # type: ignore
        
        yield connector


@pytest.fixture
def mock_dict_service() -> MagicMock:
    """Create a mock dictionary service for unit tests."""
    service = MagicMock(spec=DictionaryService)
    service.get_entry.return_value = None
    service.create_entry.return_value = True
    service.list_entries.return_value = ([], 0)
    service.search_entries.return_value = ([], 0)
    service.count_entries.return_value = 0
    
    return service


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
    
    sense.examples.append(example.to_dict())
    entry.senses.append(sense.to_dict())
    
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
                
    except Exception as e:
        logger.error(f"Failed to ensure test database {db_name}: {e}")
        raise
