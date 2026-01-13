"""
E2E Test Configuration with Perfect Isolation.

Architecture:
- Session-scoped: Pristine data templates, Flask server infrastructure
- Function-scoped: Fresh database per test, updated Flask config, Playwright page

Each test gets its own isolated BaseX database created from pristine templates.
No snapshot/restore complexity - just fresh databases from gold master data.
"""

from __future__ import annotations

import sys
import os
import pytest
import tempfile
import logging
import uuid
import socket
import threading
import time
from typing import Generator
from playwright.sync_api import sync_playwright, Browser, Page

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from tests.test_db_safety_utils import generate_safe_db_name, is_safe_database_name
from werkzeug.serving import make_server

logger = logging.getLogger(__name__)

# ============================================================================
# PRISTINE DATA TEMPLATES (Session-scoped, never modified)
# ============================================================================

@pytest.fixture(scope="session")
def pristine_lift_data() -> str:
    """Gold master LIFT XML data with 3 test entries.
    
    This is the source of truth for all test databases.
    Never modified - each test gets a copy.
    """
    return '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test_entry_1" guid="00000000-0000-0000-0000-000000000001" dateCreated="2025-01-01T12:00:00Z" dateModified="2025-01-01T12:00:00Z">
        <lexical-unit>
            <form lang="en"><text>cat</text></form>
        </lexical-unit>
        <sense id="test_sense_1">
            <grammatical-info value="Noun"/>
            <definition>
                <form lang="en"><text>A small domesticated carnivorous mammal</text></form>
            </definition>
        </sense>
    </entry>
    <entry id="test_entry_2" guid="00000000-0000-0000-0000-000000000002" dateCreated="2025-01-01T12:00:00Z" dateModified="2025-01-01T12:00:00Z">
        <lexical-unit>
            <form lang="en"><text>dog</text></form>
        </lexical-unit>
        <sense id="test_sense_2">
            <grammatical-info value="Noun"/>
            <definition>
                <form lang="en"><text>A domesticated carnivorous mammal</text></form>
            </definition>
        </sense>
    </entry>
    <entry id="test_entry_3" guid="00000000-0000-0000-0000-000000000003" dateCreated="2025-01-01T12:00:00Z" dateModified="2025-01-01T12:00:00Z">
        <lexical-unit>
            <form lang="en"><text>run</text></form>
        </lexical-unit>
        <sense id="test_sense_3">
            <grammatical-info value="Verb"/>
            <definition>
                <form lang="en"><text>To move at a speed faster than walking</text></form>
            </definition>
        </sense>
    </entry>
</lift>'''


@pytest.fixture(scope="session")
def pristine_ranges_data() -> str:
    """Gold master ranges XML with all standard range types.
    
    This is the source of truth for range data.
    Never modified - each test gets a copy.
    """
    return '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <range id="grammatical-info">
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
    <range id="lexical-relation">
        <range-element id="Synonym" guid="5049f0e3-12a4-4e9f-97f7-60091082793f"/>
        <range-element id="Antonym" guid="5049f0e3-12a4-4e9f-97f7-600910827940"/>
    </range>    <range id="variant-type">
        <range-element id="Spelling Variant" guid="5049f0e3-0000-0000-0000-000000000201">
            <label>
                <form lang="en"><text>Spelling Variant</text></form>
            </label>
        </range-element>
        <range-element id="Dialectal Variant" guid="5049f0e3-0000-0000-0000-000000000202">
            <label>
                <form lang="en"><text>Dialectal Variant</text></form>
            </label>
        </range-element>
        <range-element id="Free Variant" guid="5049f0e3-0000-0000-0000-000000000203">
            <label>
                <form lang="en"><text>Free Variant</text></form>
            </label>
        </range-element>
        <range-element id="Irregularly Inflected Form" guid="5049f0e3-0000-0000-0000-000000000204">
            <label>
                <form lang="en"><text>Irregularly Inflected Form</text></form>
            </label>
        </range-element>
    </range>    <range id="semantic-domain-ddp4">
        <range-element id="semantic-domain-1" guid="5049f0e3-0000-0000-0000-000000000101">
            <label>
                <form lang="en"><text>Semantic Domain 1</text></form>
            </label>
            <range-element id="semantic-domain-1.1" guid="5049f0e3-0000-0000-0000-000000000102">
                <label>
                    <form lang="en"><text>Semantic Subdomain 1.1</text></form>
                </label>
            </range-element>
        </range-element>
    </range>
    <range id="usage-type"/>
    <range id="domain-type"/>
    <range id="location"/>
    <range id="anthropology"/>
</lift>'''


# ============================================================================
# FLASK SERVER INFRASTRUCTURE (Session-scoped, shared by all tests)
# ============================================================================

@pytest.fixture(scope="session")
def flask_app_server(pristine_ranges_data: str):
    """Session-scoped Flask server that stays running.
    
    - Runs PostgreSQL setup once (worksets database)
    - Creates ranges database once (shared by all tests)
    - Keeps server running for performance
    - Each test updates app.config to point to its own BaseX database
    """
    from app import create_app
    from app.database.basex_connector import BaseXConnector
    from app.database.init_db import init_db as init_postgresql
    
    # Disable Redis caching for E2E tests
    os.environ['REDIS_ENABLED'] = 'false'
    
    # Create Flask app
    app = create_app()
    app.config['TESTING'] = True
    app.config['DEBUG'] = False
    
    # Initialize PostgreSQL for worksets (once per session)
    with app.app_context():
        init_postgresql()
    
    # Create session-wide ranges database
    ranges_db = f"test_{int(time.time())}_ranges_{uuid.uuid4().hex[:8]}"
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=None,
    )
    
    try:
        connector.connect()
        connector.create_database(ranges_db)
        
        # Add ranges data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(pristine_ranges_data)
            temp_file = f.name
        
        try:
            connector.execute_command(f"ADD {temp_file}")
            logger.info(f"Created session ranges database: {ranges_db}")
        finally:
            os.unlink(temp_file)
            
    finally:
        connector.disconnect()
    
    # Set ranges database in environment
    os.environ['BASEX_RANGES_DATABASE'] = ranges_db
    app.config['BASEX_RANGES_DATABASE'] = ranges_db
    
    # Start Flask server in background thread
    def find_free_port():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    port = find_free_port()
    server = make_server('127.0.0.1', port, app)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    # Wait for server to be ready
    base_url = f"http://127.0.0.1:{port}"
    for _ in range(30):
        try:
            import requests
            requests.get(f"{base_url}/health", timeout=1)
            break
        except:
            time.sleep(0.1)
    
    logger.info(f"Flask server started on {base_url}")
    
    yield app, base_url
    
    # Cleanup
    server.shutdown()
    
    # Drop ranges database
    try:
        connector.connect()
        connector.execute_command(f"DROP DB {ranges_db}")
        connector.disconnect()
    except:
        pass


# ============================================================================
# PER-TEST DATABASE (Function-scoped, fresh for each test)
# ============================================================================

@pytest.fixture(scope="function")
def test_database(request, pristine_lift_data: str):
    """Create a fresh BaseX database for each test.
    
    - Unique database name per test
    - Initialized with pristine LIFT data
    - Automatically cleaned up after test
    - No snapshot/restore complexity
    """
    from app.database.basex_connector import BaseXConnector
    
    # Generate unique database name for this test
    test_name = request.node.name
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    db_name = f"test_{timestamp}_{test_name}_{unique_id}"
    
    # Validate database name
    if not is_safe_database_name(db_name):
        db_name = generate_safe_db_name(test_type="e2e")
    
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=None,
    )
    
    try:
        connector.connect()
        
        # Drop if exists (cleanup from failed previous run)
        try:
            connector.execute_command(f"DROP DB {db_name}")
        except:
            pass
        
        # Create fresh database
        connector.create_database(db_name)
        logger.info(f"Created test database: {db_name}")
        
        # Add pristine LIFT data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(pristine_lift_data)
            temp_file = f.name
        
        try:
            connector.execute_command(f"ADD {temp_file}")
            logger.info(f"Loaded pristine data into {db_name}")
        finally:
            os.unlink(temp_file)
        
        connector.disconnect()
        
        yield db_name
        
    finally:
        # Cleanup: Drop test database
        try:
            connector.connect()
            connector.execute_command(f"DROP DB {db_name}")
            connector.disconnect()
            logger.info(f"Dropped test database: {db_name}")
        except Exception as e:
            logger.warning(f"Failed to drop test database {db_name}: {e}")


# ============================================================================
# PER-TEST FLASK CONFIGURATION (Function-scoped)
# ============================================================================

@pytest.fixture(scope="function")
def configured_flask_app(flask_app_server, test_database: str):
    """Update Flask app to use this test's database.
    
    - Points app.config to test's BaseX database
    - Clears all caches (ranges, dictionary, etc.)
    - Ensures test has clean Flask state
    """
    app, base_url = flask_app_server
    
    # Update app configuration to use test's database
    with app.app_context():
        app.config['BASEX_DATABASE'] = test_database
        os.environ['BASEX_DATABASE'] = test_database
        os.environ['TEST_DB_NAME'] = test_database
        
        # Clear all caches
        from app.services.cache_service import CacheService
        CacheService.reset_singleton()
        
        # Clear range cache
        from app.models.entry import Entry
        Entry._range_cache.clear()
        
        # Clear dictionary cache if exists
        try:
            from app.services.dictionary_service import DictionaryService
            DictionaryService._cache.clear()
        except:
            pass
        
        logger.info(f"Configured Flask app for database: {test_database}")
    
    yield app, base_url


# ============================================================================
# PLAYWRIGHT FIXTURES (Function-scoped by default)
# ============================================================================

@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Session-scoped browser instance."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-dev-shm-usage', '--no-sandbox']
        )
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def page(browser: Browser) -> Generator[Page, None, None]:
    """Function-scoped page - fresh browser context per test."""
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(10000)  # 10 seconds
    page.set_default_navigation_timeout(15000)  # 15 seconds
    
    yield page
    
    page.close()
    context.close()


# ============================================================================
# CONVENIENCE FIXTURES (Backward compatibility)
# ============================================================================

@pytest.fixture(scope="function")
def flask_test_server(configured_flask_app):
    """Backward compatible fixture name."""
    return configured_flask_app


@pytest.fixture(scope="function")
def app_url(configured_flask_app) -> str:
    """Get base URL for test requests."""
    app, base_url = configured_flask_app
    return base_url


# ============================================================================
# PROJECT SETTINGS FIXTURE
# ============================================================================

@pytest.fixture(scope="function", autouse=True)
def ensure_project_settings(configured_flask_app):
    """Ensure project settings exist for each test.
    
    Required by many API endpoints that expect project_settings.id.
    """
    app, _ = configured_flask_app
    
    with app.app_context():
        from app.models.project_settings import ProjectSettings
        from app import db
        
        # Check if settings exist
        settings = ProjectSettings.query.first()
        if not settings:
            # Create default settings
            settings = ProjectSettings(
                project_name="Test Project",
                lexicon_language="en"
            )
            db.session.add(settings)
            db.session.commit()
            logger.info("Created project settings for test")


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Configure logging for e2e tests."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
