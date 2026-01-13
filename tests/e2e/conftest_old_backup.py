"""
Rewritten conftest for E2E tests with perfect test isolation.

Each test gets:
- Its own fresh database (function-scoped)
- Its own Flask app configuration pointing to that database
- Its own Playwright page

Architecture:
- Session-scoped: Pristine data template (in memory), Flask server infrastructure
- Function-scoped: Test database, Flask config update, Playwright page
"""

from __future__ import annotations

import sys
import os
import pytest
import tempfile
import logging
import uuid
import time
from typing import Generator, Tuple
from datetime import datetime
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from tests.test_db_safety_utils import generate_safe_db_name, is_safe_database_name

import socket
from werkzeug.serving import make_server

logger = logging.getLogger(__name__)

# ============================================================================
# SESSION-SCOPED: Pristine Data Template (Gold Master)
# ============================================================================

@pytest.fixture(scope="session")
def pristine_lift_data() -> str:
    """
    Session-scoped pristine LIFT data that serves as the template for all tests.
    
    This is the "gold master" - it's created once and stored in memory.
    Each test gets a fresh database created from this template.
    """
    return '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test_entry_1" dateCreated="2024-01-01T00:00:00Z" dateModified="2024-01-01T00:00:00Z" guid="00000000-0000-0000-0000-000000000001">
        <lexical-unit>
            <form lang="en"><text>cat</text></form>
        </lexical-unit>
        <sense id="sense_1">
            <grammatical-info value="noun"/>
            <gloss lang="en"><text>a feline animal</text></gloss>
        </sense>
    </entry>
    <entry id="test_entry_2" dateCreated="2024-01-01T00:00:00Z" dateModified="2024-01-01T00:00:00Z" guid="00000000-0000-0000-0000-000000000002">
        <lexical-unit>
            <form lang="en"><text>dog</text></form>
        </lexical-unit>
        <sense id="sense_1">
            <grammatical-info value="noun"/>
            <gloss lang="en"><text>a canine animal</text></gloss>
        </sense>
    </entry>
    <entry id="test_entry_3" dateCreated="2024-01-01T00:00:00Z" dateModified="2024-01-01T00:00:00Z" guid="00000000-0000-0000-0000-000000000003">
        <lexical-unit>
            <form lang="en"><text>run</text></form>
        </lexical-unit>
        <sense id="sense_1">
            <grammatical-info value="verb"/>
            <gloss lang="en"><text>to move quickly</text></gloss>
        </sense>
    </entry>
</lift>'''


@pytest.fixture(scope="session")
def pristine_ranges_data() -> str:
    """Session-scoped pristine LIFT ranges data."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <range id="grammatical-info" guid="00000000-0000-0000-0000-000000000010">
        <range-element id="noun" guid="00000000-0000-0000-0000-000000000011"/>
        <range-element id="verb" guid="00000000-0000-0000-0000-000000000012"/>
        <range-element id="adjective" guid="00000000-0000-0000-0000-000000000013"/>
    </range>
    <range id="lexical-relation" guid="00000000-0000-0000-0000-000000000020">
        <range-element id="synonym" guid="00000000-0000-0000-0000-000000000021"/>
        <range-element id="antonym" guid="00000000-0000-0000-0000-000000000022"/>
    </range>
    <range id="semantic-domain-ddp4" guid="00000000-0000-0000-0000-000000000030">
        <range-element id="1" guid="00000000-0000-0000-0000-000000000031">
            <label>
                <form lang="en"><text>Universe, creation</text></form>
            </label>
        </range-element>
        <range-element id="2" guid="00000000-0000-0000-0000-000000000032">
            <label>
                <form lang="en"><text>Person</text></form>
            </label>
        </range-element>
    </range>
    <range id="anthro-code" guid="00000000-0000-0000-0000-000000000040">
        <range-element id="1" guid="00000000-0000-0000-0000-000000000041"/>
    </range>
    <range id="domain-type" guid="00000000-0000-0000-0000-000000000050">
        <range-element id="academic" guid="00000000-0000-0000-0000-000000000051"/>
        <range-element id="everyday" guid="00000000-0000-0000-0000-000000000052"/>
    </range>
    <range id="usage-type" guid="00000000-0000-0000-0000-000000000060">
        <range-element id="formal" guid="00000000-0000-0000-0000-000000000061"/>
        <range-element id="informal" guid="00000000-0000-0000-0000-000000000062"/>
    </range>
    <range id="variant-type" guid="00000000-0000-0000-0000-000000000070">
        <range-element id="dialectal" guid="00000000-0000-0000-0000-000000000071"/>
        <range-element id="spelling" guid="00000000-0000-0000-0000-000000000072"/>
        <range-element id="free" guid="00000000-0000-0000-0000-000000000073"/>
        <range-element id="bound" guid="00000000-0000-0000-0000-000000000074"/>
    </range>
</lift-ranges>'''


# ============================================================================
# SESSION-SCOPED: Flask Server Infrastructure
# ============================================================================

@pytest.fixture(scope="session")
def flask_app_server():
    """
    Session-scoped Flask server that stays running for all tests.
    
    The server itself is shared, but each test gets its own database
    by updating the app's configuration.
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

    # Setup PostgreSQL connection pool
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
        logger.info(f"Connected to PostgreSQL at {app.config.get('PG_HOST')}:{app.config.get('PG_PORT')}")
    except Exception as e:
        logger.warning(f"Could not connect to PostgreSQL: {e}")
        app.pg_pool = None

    # Start the server
    server = make_server('localhost', port, app)
    import threading
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://localhost:{port}"

    # Wait for server to be ready
    for _ in range(30):
        try:
            with urllib.request.urlopen(base_url) as resp:
                if resp.status == 200:
                    break
        except Exception:
            time.sleep(0.1)

    logger.info(f"Flask server started at {base_url}")

    yield (app, base_url)

    # Shutdown
    server.shutdown()
    thread.join(timeout=5)


# ============================================================================
# FUNCTION-SCOPED: Per-Test Database
# ============================================================================

@pytest.fixture(scope="function")
def test_database(request, pristine_lift_data, pristine_ranges_data):
    """
    Function-scoped fixture that creates a fresh database for EACH test.
    
    Each test gets:
    1. A unique database name
    2. Pristine LIFT data loaded from template
    3. Pristine ranges data loaded from template
    4. Automatic cleanup after test
    
    Returns: database name (str)
    """
    from app.database.basex_connector import BaseXConnector
    
    # Generate unique database name for this test
    test_name = request.node.name
    # Sanitize test name (remove special characters)
    safe_test_name = "".join(c if c.isalnum() else "_" for c in test_name)[:30]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:6]
    db_name = f"test_{timestamp}_{safe_test_name}_{unique_id}"
    
    # Ensure it's a safe test database name
    if not is_safe_database_name(db_name):
        db_name = generate_safe_db_name(prefix="test_e2e")
    
    logger.info(f"Creating test database: {db_name} for test: {test_name}")
    
    # Connect to BaseX (no database selected)
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=None,
    )
    
    try:
        connector.connect()
        
        # Create the database
        connector.execute_command(f"CREATE DB {db_name}")
        logger.debug(f"Created database: {db_name}")
        
        # Disconnect and reconnect with database opened
        connector.disconnect()
        connector = BaseXConnector(
            host=os.getenv('BASEX_HOST', 'localhost'),
            port=int(os.getenv('BASEX_PORT', '1984')),
            username=os.getenv('BASEX_USERNAME', 'admin'),
            password=os.getenv('BASEX_PASSWORD', 'admin'),
            database=db_name,
        )
        connector.connect()
        
        # Write pristine LIFT data to temporary file and add to database
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(pristine_lift_data)
            lift_path = f.name
        
        try:
            connector.execute_command(f"ADD {lift_path}")
            logger.debug(f"Loaded pristine LIFT data into {db_name}")
        finally:
            os.unlink(lift_path)
        
        # Write pristine ranges data to temporary file and add to database
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(pristine_ranges_data)
            ranges_path = f.name
        
        try:
            connector.execute_command(f"ADD TO ranges.xml {ranges_path}")
            logger.debug(f"Loaded pristine ranges data into {db_name}")
        finally:
            os.unlink(ranges_path)
        
        # Verify data loaded correctly
        result = connector.execute_query("""
            declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
            count(collection($db)//lift:entry)
        """, db=db_name)
        logger.info(f"Database {db_name} created with {result} entries")
        
        # Set environment variables for this test
        os.environ['TEST_DB_NAME'] = db_name
        os.environ['BASEX_DATABASE'] = db_name
        
        yield db_name
        
    finally:
        # Cleanup: Drop the test database
        try:
            connector.disconnect()
            
            # Reconnect without database to drop it
            cleanup_connector = BaseXConnector(
                host=os.getenv('BASEX_HOST', 'localhost'),
                port=int(os.getenv('BASEX_PORT', '1984')),
                username=os.getenv('BASEX_USERNAME', 'admin'),
                password=os.getenv('BASEX_PASSWORD', 'admin'),
                database=None,
            )
            cleanup_connector.connect()
            
            try:
                cleanup_connector.execute_command(f"DROP DB {db_name}")
                logger.info(f"Dropped test database: {db_name}")
            except Exception as e:
                logger.warning(f"Could not drop test database {db_name}: {e}")
            finally:
                cleanup_connector.disconnect()
                
        except Exception as e:
            logger.error(f"Error during database cleanup for {db_name}: {e}")


# ============================================================================
# FUNCTION-SCOPED: Flask App Configuration Update
# ============================================================================

@pytest.fixture(scope="function")
def configured_flask_app(flask_app_server, test_database):
    """
    Function-scoped fixture that configures the Flask app to use the test database.
    
    Updates the app configuration and clears caches so each test sees only
    its own database.
    
    Returns: (app, base_url, database_name) tuple
    """
    app, base_url = flask_app_server
    db_name = test_database
    
    # Update app configuration for this test's database
    with app.app_context():
        app.config['BASEX_DATABASE'] = db_name
        os.environ['BASEX_DATABASE'] = db_name
        os.environ['TEST_DB_NAME'] = db_name
        
        # Clear any caches that might hold old database references
        try:
            from app.services.dictionary_service import DictionaryService
            from app.database.basex_connector import BaseXConnector
            
            # Invalidate ranges cache
            try:
                dict_service = app.injector.get(DictionaryService)
                dict_service.invalidate_ranges_cache()
                logger.debug(f"Invalidated ranges cache for {db_name}")
            except Exception as e:
                logger.debug(f"Could not invalidate ranges cache: {e}")
            
            # Create/update project settings for this database
            from app.config_manager import ConfigManager
            from app.models.project_settings import ProjectSettings
            
            # Clear any existing project settings and create new one
            try:
                ProjectSettings.query.delete()
                app.db.session.commit()
            except Exception:
                pass
            
            cm = ConfigManager(app.instance_path)
            settings = cm.create_settings(
                project_name="E2E Test Project",
                basex_db_name=db_name,
                settings_json={
                    'source_language': {'code': 'en', 'name': 'English'},
                    'target_languages': [{'code': 'es', 'name': 'Spanish'}]
                }
            )
            logger.debug(f"Created project settings for {db_name}")
            
        except Exception as e:
            logger.warning(f"Error during cache clearing: {e}")
    
    logger.info(f"Configured Flask app to use database: {db_name}")
    
    return (app, base_url, db_name)


# ============================================================================
# FUNCTION-SCOPED: Playwright Browser and Page
# ============================================================================

@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Session-scoped browser for all tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-dev-shm-usage']
        )
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(browser, configured_flask_app) -> Generator[Page, None, None]:
    """
    Function-scoped Playwright page for each test.
    
    Each test gets a fresh page with:
    - No shared cookies
    - No shared local storage
    - No shared session state
    """
    app, base_url, db_name = configured_flask_app
    
    context = browser.new_context()
    page = context.new_page()
    
    # Set a shorter timeout for faster test failures
    page.set_default_timeout(10000)  # 10 seconds
    
    logger.debug(f"Created new Playwright page for database: {db_name}")
    
    yield page
    
    # Cleanup
    page.close()
    context.close()


# ============================================================================
# CONVENIENCE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def app_url(configured_flask_app) -> str:
    """Convenience fixture that returns just the base URL."""
    app, base_url, db_name = configured_flask_app
    return base_url


@pytest.fixture(scope="function")
def flask_app(configured_flask_app):
    """Convenience fixture that returns just the Flask app."""
    app, base_url, db_name = configured_flask_app
    return app


# For backward compatibility with existing tests
@pytest.fixture(scope="function")
def flask_test_server(configured_flask_app) -> Tuple[str, int]:
    """
    Backward compatibility fixture for tests that expect (url, project_id).
    
    Returns: (base_url, project_id) tuple
    """
    app, base_url, db_name = configured_flask_app
    
    # Get project ID from database
    with app.app_context():
        from app.models.project_settings import ProjectSettings
        settings = ProjectSettings.query.first()
        project_id = settings.id if settings else 1
    
    return (base_url, project_id)


# ============================================================================
# PLAYWRIGHT FIXTURE CONFIGURATION
# ============================================================================

@pytest.fixture(scope="function")
def shorten_playwright_timeouts(page: Page):
    """
    Shorten Playwright timeouts for faster test failures.
    
    This is automatically applied to all tests via the page fixture dependency.
    """
    page.set_default_timeout(5000)  # 5 seconds
    page.set_default_navigation_timeout(10000)  # 10 seconds for navigations
