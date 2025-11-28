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
from dotenv import load_dotenv

# Load environment variables from .env file BEFORE any imports
load_dotenv()

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
        logger.info("Attempting to connect to BaseX without a database.")
        connector.connect()
        logger.info("Successfully connected to BaseX without a database.")
        
        # Create the test database
        logger.info(f"Attempting to create test database: {test_db_name}")
        try:
            connector.create_database(test_db_name)
            logger.info(f"Successfully created test database: {test_db_name}")
        except Exception as e:
            logger.error(f"Failed to create test database: {test_db_name}. Error: {e}")
            raise
        
        # Now set the database name and reconnect
        connector.database = test_db_name
        logger.info(f"Disconnecting before reconnecting to database: {test_db_name}")
        connector.disconnect()
        logger.info(f"Attempting to reconnect to database: {test_db_name}")
        connector.connect()  # Reconnect with the database
        logger.info(f"Successfully reconnected to database: {test_db_name}")
        
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
        
        # Add some test entries without dates for sorting tests
        try:
            # Create individual test entries as XML documents
            # Use the same approach as conftest - write to files and add them
            import tempfile
            
            test_entry_1_content = '''<entry id="no_date_entry_1">
                <lexical-unit>
                    <form lang="en">
                        <text>no date entry one</text>
                    </form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en">
                            <text>Entry without date modification for testing sorting</text>
                        </form>
                    </definition>
                </sense>
            </entry>'''
            
            test_entry_2_content = '''<entry id="no_date_entry_2" dateCreated="2023-01-01T10:00:00Z">
                <lexical-unit>
                    <form lang="en">
                        <text>no date entry two</text>
                    </form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en">
                            <text>Another entry without dateModified for testing</text>
                        </form>
                    </definition>
                </sense>
            </entry>'''
            
            test_entry_3_content = '''<entry id="no_date_entry_3">
                <lexical-unit>
                    <form lang="en">
                        <text>zzz last alphabetically</text>
                    </form>
                </lexical-unit>
                <sense>
                    <definition>
                        <form lang="en">
                            <text>Entry that should be last alphabetically but has no date</text>
                        </form>
                    </definition>
                </sense>
            </entry>'''
            
            # Create temporary files and use ADD command (same as the LIFT file approach)
            for i, entry_content in enumerate([test_entry_1_content, test_entry_2_content, test_entry_3_content], 1):
                try:
                    # Skip ADD command for now and use db:add directly with the content
                    # The ADD command seems to have issues with the file path format
                    print(f"DEBUG: Adding test entry {i} with content length {len(entry_content)}")
                    connector.execute_update(f"db:add('{test_db_name}', '{entry_content}', 'test_entry_{i}.xml')")
                    logger.info(f"Added test entry {i} using db:add")
                    print(f"DEBUG: Successfully added test entry {i}")
                except Exception as e:
                    logger.error(f"Failed to add test entry {i}: {e}")
                    print(f"DEBUG: Failed to add test entry {i}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Verify test entries were added
            test_count = connector.execute_query(f"count(collection('{test_db_name}')//entry[starts-with(@id, 'no_date_entry')])")
            logger.info(f"Verified {test_count} test entries added to database")
            
        except Exception as e:
            logger.warning(f"Could not add test entries without dates: {e}")
            # Log more details for debugging
            logger.warning(f"Exception details: {type(e).__name__}: {str(e)}")
        
        yield connector
        
    except Exception as e:
        logger.error(f"Failed to setup BaseX test connector: {e}")
        raise
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
    static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'app', 'static')
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key-for-sessions',
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    })
    
    # Initialize SQLAlchemy with the app
    from app.models.project_settings import db
    db.init_app(app)
    
    # Create database tables in test context
    with app.app_context():
        db.create_all()
    
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
    
    # Register the settings routes blueprint
    from app.routes.settings_routes import settings_bp
    app.register_blueprint(settings_bp)
    
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
    
    # Initialize ConfigManager for tests
    from app.config_manager import ConfigManager
    import tempfile
    with tempfile.TemporaryDirectory() as temp_instance_path:
        config_manager = ConfigManager(temp_instance_path)
        app.config_manager = config_manager  # type: ignore
    
    # Set up PostgreSQL connection pool for workset tests (if available)
    try:
        import psycopg2.pool
        host = os.getenv('POSTGRES_HOST')
        if not host:
            # Try to get Windows host IP from WSL
            try:
                result = os.popen("ip route show | grep -i default | awk '{ print $3}'").read().strip()
                if result:
                    host = result
            except Exception:
                pass
        
        if host:
            port = int(os.getenv('POSTGRES_PORT', '5432'))
            user = os.getenv('POSTGRES_USER', 'dict_user')
            password = os.getenv('POSTGRES_PASSWORD', 'dict_pass')
            database = os.getenv('POSTGRES_DB', 'dictionary_analytics')
            
            pg_pool = psycopg2.pool.SimpleConnectionPool(
                1, 10,
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
            app.pg_pool = pg_pool  # type: ignore
            logger.info("PostgreSQL connection pool initialized for tests")
        else:
            app.pg_pool = None  # type: ignore
            logger.info("PostgreSQL not configured for tests (workset tests will be skipped)")
    except Exception as e:
        app.pg_pool = None  # type: ignore
        logger.warning(f"Failed to initialize PostgreSQL pool: {e}")
    
    # Create application context
    with app.app_context():
        yield app


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Test client for integration testing."""
    return app.test_client()


@pytest.fixture(scope="function")
def playwright_page(app: Flask) -> Generator[Page, None, None]:
    """Provides a Playwright Page object for browser automation testing."""
    with sync_playwright() as p:
        # Launch browser in headless mode to prevent hanging on hidden windows
        browser = p.chromium.launch(headless=True)
        context = None
        page = None
        try:
            context = browser.new_context()
            page = context.new_page()
            yield page
        finally:
            # Always clean up browser resources, even on test failure
            if page:
                try:
                    page.close()
                except Exception as e:
                    logger.warning(f"Failed to close page: {e}")
            if context:
                try:
                    context.close()
                except Exception as e:
                    logger.warning(f"Failed to close context: {e}")
            try:
                browser.close()
            except Exception as e:
                logger.warning(f"Failed to close browser: {e}")

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


# ==============================================================================
# PostgreSQL Fixtures for WSL Integration
# ==============================================================================

@pytest.fixture(scope="session")
def postgres_available() -> bool:
    """Check if PostgreSQL is available from WSL."""
    try:
        import psycopg2
        host = os.getenv('POSTGRES_HOST')
        if not host:
            # Try to auto-detect Windows host IP from WSL
            try:
                # Method 1: Use ip route (more reliable)
                import subprocess
                result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'default' in line:
                            parts = line.split()
                            if len(parts) >= 3:
                                host = parts[2]
                                break
            except:
                pass
            
            if not host:
                # Method 2: Fallback to resolv.conf
                try:
                    with open('/etc/resolv.conf', 'r') as f:
                        for line in f:
                            if line.startswith('nameserver'):
                                host = line.split()[1]
                                break
                except:
                    host = 'localhost'
        
        port = int(os.getenv('POSTGRES_PORT', '5432'))
        user = os.getenv('POSTGRES_USER', 'dict_user')
        password = os.getenv('POSTGRES_PASSWORD', 'dict_pass')
        database = os.getenv('POSTGRES_DB', 'dictionary_analytics')
        
        logger.info(f"Testing PostgreSQL connection to {host}:{port}")
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=3
        )
        conn.close()
        logger.info("PostgreSQL connection successful")
        return True
    except ImportError:
        logger.warning("psycopg2 not installed - install with: pip install psycopg2-binary")
        return False
    except Exception as e:
        logger.warning(f"PostgreSQL not available: {e}")
        logger.info("See docs/POSTGRESQL_WSL_SETUP.md for setup instructions")
        return False


@pytest.fixture(scope="function")
def postgres_test_connection(postgres_available: bool):
    """
    Provide a raw psycopg2 connection to PostgreSQL database.
    
    Automatically detects Windows host IP from WSL if POSTGRES_HOST not set.
    Connection is automatically rolled back after test.
    """
    import psycopg2
    
    host = os.getenv('POSTGRES_HOST')
    if not host:
        # Auto-detect Windows host IP from WSL
        try:
            # Method 1: Use ip route (more reliable)
            import subprocess
            result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'default' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            host = parts[2]
                            break
        except:
            pass
        
        if not host:
            # Method 2: Fallback to resolv.conf
            try:
                with open('/etc/resolv.conf', 'r') as f:
                    for line in f:
                        if line.startswith('nameserver'):
                            host = line.split()[1]
                            break
            except:
                host = 'localhost'
    
    port = int(os.getenv('POSTGRES_PORT', '5432'))
    user = os.getenv('POSTGRES_USER', 'dict_user')
    password = os.getenv('POSTGRES_PASSWORD', 'dict_pass')
    database = os.getenv('POSTGRES_DB', 'dictionary_analytics')
    
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database
    )
    
    # Start transaction
    conn.autocommit = False
    
    yield conn
    
    # Rollback any changes
    try:
        conn.rollback()
        conn.close()
    except:
        pass


@pytest.fixture(scope="function")
def postgres_test_engine(postgres_available: bool):
    """
    Provide a SQLAlchemy engine for PostgreSQL database.
    
    Automatically detects Windows host IP from WSL if POSTGRES_HOST not set.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool
    
    host = os.getenv('POSTGRES_HOST')
    if not host:
        # Auto-detect Windows host IP from WSL
        try:
            # Method 1: Use ip route (more reliable)
            import subprocess
            result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'default' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            host = parts[2]
                            break
        except:
            pass
        
        if not host:
            # Method 2: Fallback to resolv.conf
            try:
                with open('/etc/resolv.conf', 'r') as f:
                    for line in f:
                        if line.startswith('nameserver'):
                            host = line.split()[1]
                            break
            except:
                host = 'localhost'
    
    port = int(os.getenv('POSTGRES_PORT', '5432'))
    user = os.getenv('POSTGRES_USER', 'dict_user')
    password = os.getenv('POSTGRES_PASSWORD', 'dict_pass')
    database = os.getenv('POSTGRES_DB', 'dictionary_analytics')
    
    url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    engine = create_engine(url, poolclass=NullPool)
    
    yield engine
    
    engine.dispose()


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests in integration directory as integration tests."""
    for item in items:
        # If test is in integration directory, mark it as integration test
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)