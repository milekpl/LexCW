"""
PyTest fixtures for integration testing - sets up real BaseX database with sample LIFT files.
"""

from __future__ import annotations

import os
import sys
import pytest
import tempfile
import uuid
import logging
from typing import Generator
import threading
import time
from urllib.parse import urlparse

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app
from app.database.basex_connector import BaseXConnector
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example
from app.models.pronunciation import Pronunciation
from flask import Flask
from flask.testing import FlaskClient
from playwright.sync_api import Page, Browser, sync_playwright

logger = logging.getLogger(__name__)


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="session")
def sample_lift_files() -> dict[str, str]:
    """Get paths to sample LIFT files."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sample_dir = os.path.join(base_dir, 'sample-lift-file')
    
    return {
        'lift': os.path.join(sample_dir, 'sample-lift-file.lift'),
        'ranges': os.path.join(sample_dir, 'sample-lift-file.lift-ranges')
    }


@pytest.fixture(scope="function")
def basex_test_connector(basex_available: bool, test_db_name: str, sample_lift_files: dict[str, str]):
    """Create BaseX connector with isolated test database loaded with sample LIFT files."""
    if not basex_available:
        pytest.skip("BaseX server not available")
    
    # Verify sample files exist
    if not os.path.exists(sample_lift_files['lift']):
        pytest.skip(f"Sample LIFT file not found: {sample_lift_files['lift']}")
    if not os.path.exists(sample_lift_files['ranges']):
        pytest.skip(f"Sample LIFT ranges file not found: {sample_lift_files['ranges']}")
    
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
        logger.info(f"Created test database: {test_db_name}")
        
        # Now set the database name and reconnect
        connector.database = test_db_name
        connector.disconnect()
        connector.connect()  # Reconnect with the database
        
        # Load sample LIFT file
        try:
            # Use BaseX ADD command to add the LIFT file
            lift_path = sample_lift_files['lift'].replace('\\', '/')
            connector.execute_command(f"ADD {lift_path}")
            logger.info(f"Added sample LIFT file to test database: {lift_path}")
        except Exception as e:
            logger.warning(f"Failed to add LIFT file with ADD command: {e}")
            # Fallback: read file and add content
            try:
                with open(sample_lift_files['lift'], 'r', encoding='utf-8') as f:
                    lift_content = f.read()
                # Remove XML declaration for BaseX
                if lift_content.startswith('<?xml'):
                    lift_content = lift_content.split('\n', 1)[1] if '\n' in lift_content else lift_content
                connector.execute_update(f"db:add('{test_db_name}', '{lift_content}', 'lift.xml')")
                logger.info("Added LIFT content using db:add function")
            except Exception as e2:
                logger.error(f"Failed to add LIFT content: {e2}")
                raise
        
        # Load sample LIFT ranges file
        try:
            # Use BaseX ADD command to add the ranges file
            ranges_path = sample_lift_files['ranges'].replace('\\', '/')
            connector.execute_command(f"ADD {ranges_path}")
            logger.info(f"Added sample LIFT ranges file to test database: {ranges_path}")
        except Exception as e:
            logger.warning(f"Failed to add ranges file with ADD command: {e}")
            # Fallback: read file and add content
            try:
                with open(sample_lift_files['ranges'], 'r', encoding='utf-8') as f:
                    ranges_content = f.read()
                # Remove XML declaration for BaseX
                if ranges_content.startswith('<?xml'):
                    ranges_content = ranges_content.split('\n', 1)[1] if '\n' in ranges_content else ranges_content
                # Escape quotes for BaseX
                ranges_content = ranges_content.replace("'", "''")
                connector.execute_update(f"db:add('{test_db_name}', '{ranges_content}', 'ranges.xml')")
                logger.info("Added ranges content using db:add function")
            except Exception as e2:
                logger.error(f"Failed to add ranges content: {e2}")
                raise
        
        # Verify data was loaded
        try:
            entry_count = connector.execute_query("count(//entry)")
            ranges_count = connector.execute_query("count(//range)")
            logger.info(f"Test database loaded with {entry_count} entries and {ranges_count} ranges")
        except Exception as e:
            logger.warning(f"Could not verify data loading: {e}")
        
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
def dict_service_with_db(basex_test_connector: BaseXConnector) -> DictionaryService:
    """Create dictionary service with real test database loaded with sample data."""
    return DictionaryService(db_connector=basex_test_connector)


@pytest.fixture(scope="function")
def app(dict_service_with_db: DictionaryService) -> Generator[Flask, None, None]:
    """Create and configure a Flask app for integration testing with real database."""
    from flask import Flask
    import os
    
    template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'app', 'templates')
    app = Flask(__name__, template_folder=template_dir)
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-for-sessions'
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
    
    # Register the ranges blueprint
    from app.api.ranges import ranges_bp
    app.register_blueprint(ranges_bp)
    
    # Register the workbench views blueprint
    from app.views import workbench_bp
    app.register_blueprint(workbench_bp)
    
    # Set up dependency injection for the test app
    from injector import Injector, singleton
    from app.database.basex_connector import BaseXConnector
    from app.services.dictionary_service import DictionaryService
    
    test_injector = Injector()
    
    def configure_test_dependencies(binder):
        binder.bind(DictionaryService, to=dict_service_with_db)
        # Create a test BaseXConnector if needed
        if hasattr(dict_service_with_db, 'db_connector'):
            binder.bind(BaseXConnector, to=dict_service_with_db.db_connector)
    
    test_injector.binder.install(configure_test_dependencies)
    
    # Make the injector available to the app
    app.injector = test_injector  # type: ignore
    
    # Import and make injector available globally (like in real app)
    import app as app_module
    app_module.injector = test_injector
    
    # Attach the test dictionary service (use the same instance as dict_service_with_db)
    app.dict_service = dict_service_with_db  # type: ignore
    app.dict_service_with_db = dict_service_with_db  # type: ignore - alias for compatibility
    
    # Initialize cache service for tests (matching production app initialization)
    from app.services.cache_service import CacheService
    app.cache_service = CacheService()  # type: ignore
    
    # Create application context
    with app.app_context():
        yield app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Test client for integration testing."""
    return app.test_client()


import threading
import time
from urllib.parse import urlparse

@pytest.fixture(scope="function")
def playwright_page(app: Flask) -> Generator[Page, None, None]:
    """Provides a Playwright Page object for browser automation testing."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        yield page
        browser.close()

@pytest.fixture(scope="function")
def live_server(app: Flask):
    """Starts the Flask app in a separate thread for Playwright tests."""
    port = 5000  # Default Flask port, adjust if needed
    url = f"http://localhost:{port}"
    
    # Function to run the Flask app
    def run_app():
        app.run(port=port, debug=False, use_reloader=False)

    # Start the Flask app in a new thread
    server_thread = threading.Thread(target=run_app)
    server_thread.daemon = True  # Daemonize thread so it terminates when the main program exits
    server_thread.start()

    # Wait for the server to start
    # You might need a more robust check here, e.g., trying to connect to the URL
    time.sleep(2)  # Give the server some time to boot up

    class LiveServer:
        def __init__(self, url):
            self.url = url
            self.app = app
    
    yield LiveServer(url)

    # No explicit shutdown needed for daemon thread, but can add if necessary
    # For example, if app.run() had a shutdown mechanism.
    # In this setup, the thread will exit when the main process exits.



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


# Integration test configuration
def pytest_configure(config):
    """Configure pytest for integration tests."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires real database)"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests in integration directory as integration tests."""
    for item in items:
        # If test is in integration directory, mark it as integration test
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)