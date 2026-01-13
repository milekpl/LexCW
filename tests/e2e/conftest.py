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
<lift-ranges version="0.13">
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
    </range>
    <range id="variant-type">
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
    </range>
    <range id="semantic-domain-ddp4">
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
</lift-ranges>'''


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
    from dotenv import load_dotenv
    import psycopg2.pool
    
    # Load environment variables
    load_dotenv('/mnt/d/Dokumenty/slownik-wielki/flask-app/.env', override=True)
    
    # Disable Redis caching for E2E tests
    os.environ['REDIS_ENABLED'] = 'false'
    
    # Create Flask app
    app = create_app(os.getenv('FLASK_CONFIG') or 'testing')
    app.config['TESTING'] = True
    app.config['DEBUG'] = False
    
    # Initialize PostgreSQL for worksets (once per session)
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
def test_database(request, pristine_lift_data: str, pristine_ranges_data: str):
    """Create a fresh BaseX database for each test.
    
    - Unique database name per test
    - Initialized with pristine LIFT data AND ranges
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
            logger.info(f"Loaded pristine LIFT data into {db_name}")
        finally:
            os.unlink(temp_file)
        
        # Add pristine ranges data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(pristine_ranges_data)
            temp_file = f.name
        
        try:
            connector.execute_command(f"ADD {temp_file}")
            logger.info(f"Loaded pristine ranges data into {db_name}")
        finally:
            os.unlink(temp_file)
        
        connector.disconnect()
        
        yield db_name
        
    finally:
        # Cleanup: Drop test database with retries in case of transient locks
        try:
            connector.connect()
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    connector.execute_command(f"DROP DB {db_name}")
                    logger.info(f"Dropped test database: {db_name}")
                    break
                except Exception as drop_err:
                    if attempt == max_retries:
                        logger.warning(f"Failed to drop test database {db_name} after {attempt} attempts: {drop_err}")
                    else:
                        logger.info(f"Retrying drop DB {db_name} (attempt {attempt}/{max_retries}) due to: {drop_err}")
                        import time as _time
                        _time.sleep(0.5 * attempt)
            connector.disconnect()
        except Exception as e:
            logger.warning(f"Failed to connect/disconnect during cleanup for {db_name}: {e}")


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
        # Reset DictionaryService ranges cache to ensure fresh ranges per test
        try:
            dict_service = app.injector.get('DictionaryService') if hasattr(app, 'injector') else None
            if dict_service:
                # Clear in-memory cached ranges
                dict_service.ranges = {}
                dict_service.ranges_parser = dict_service.ranges_parser.__class__()
        except Exception:
            pass
        
        logger.info(f"Configured Flask app for database: {test_database}")
    
    yield app, base_url

    # Teardown: ensure the app's singleton BaseX connector has closed any open
    # database/session so that the per-test DB can be dropped reliably. This
    # prevents "Database '...' is opened by another process" errors during
    # cleanup when the test harness attempts to DROP the test DB.
    try:
        from app.database.basex_connector import BaseXConnector
        with app.app_context():
            try:
                conn = app.injector.get(BaseXConnector)
                # Close any open database and fully disconnect the session
                conn.close_database()
                conn.disconnect()
                logger.info(f"Closed app BaseX connector session for DB {test_database}")
            except Exception as e:
                logger.warning(f"Failed to close app BaseX connector during teardown: {e}")
    except Exception:
        # Defensive: keep teardown robust if import or injector access fails
        logger.debug("Skipping app BaseX connector shutdown in teardown (not available)")


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
def page(browser: Browser, app_url: str, ensure_project_settings, configured_flask_app) -> Generator[Page, None, None]:
    """Function-scoped page - fresh browser context per test with project selected."""
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(10000)  # 10 seconds
    page.set_default_navigation_timeout(15000)  # 15 seconds
    
    # Set project in session by navigating to select endpoint
    # Get the project ID that was created by ensure_project_settings fixture
    app, _ = configured_flask_app
    with app.app_context():
        from app.models.project_settings import ProjectSettings
        settings = ProjectSettings.query.first()
        if settings:
            project_id = settings.id
            try:
                # Navigate to select endpoint - this sets session['project_id'] in cookie
                page.goto(f"{app_url}/settings/projects/{project_id}/select", wait_until="networkidle")
                logger.info(f"Set project {project_id} in Playwright session for test")
            except Exception as e:
                logger.warning(f"Could not set project {project_id} in session: {e}")
        else:
            logger.error("No project settings found - tests will fail with redirects!")
    
    yield page
    
    page.close()
    context.close()


# ============================================================================
# CONVENIENCE FIXTURES (Backward compatibility)
# ============================================================================

@pytest.fixture(scope="function")
def flask_test_server(configured_flask_app) -> str:
    """Backward compatible fixture name - returns base URL string."""
    app, base_url = configured_flask_app
    return base_url


@pytest.fixture(scope="function")
def app_url(configured_flask_app) -> str:
    """Get base URL for test requests."""
    app, base_url = configured_flask_app
    return base_url


# ============================================================================
# PROJECT SETTINGS FIXTURE
# ============================================================================

@pytest.fixture(scope="function", autouse=True)
def ensure_project_settings(configured_flask_app, test_database: str):
    """Ensure project settings exist for each test.
    
    Required by many API endpoints that expect project_settings.id.
    """
    app, _ = configured_flask_app
    
    with app.app_context():
        from app.models.project_settings import ProjectSettings
        from app.models.workset_models import db
        
        # Check if settings exist; create or update so it always points to current test DB
        settings = ProjectSettings.query.first()
        if not settings:
            # Create default settings
            settings = ProjectSettings(
                project_name="Test Project",
                basex_db_name=test_database,
                source_language={"code": "en", "name": "English"},
                target_languages=[],
                settings_json={}
            )
            db.session.add(settings)
            logger.info("Created project settings for test")
        else:
            # Update existing settings to reference the per-test database to avoid
            # cross-test leakage when session['project_id'] is used by APIs (e.g., /api/search)
            settings.basex_db_name = test_database
            logger.debug("Updated existing project settings to use test DB: %s", test_database)

        # Persist changes (create or update) so each test's project_settings
        # consistently reference the correct per-test BaseX database.
        db.session.commit()


# ============================================================================
# HELPER FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def ensure_sense():
    """Helper to ensure at least one sense exists in the entry form.
    
    Usage: ensure_sense(page)
    
    This function checks if there's at least one visible sense form on the page.
    If not, it clicks the "Add Sense" button to create one.
    """
    def _ensure_sense(page):
        """Ensure at least one sense form exists on the page."""
        # Only add sense if no VISIBLE definition textarea exists (exclude hidden template)
        if page.locator('textarea[name*="definition"]:visible').count() == 0:
            if page.locator('#add-first-sense-btn').count() > 0:
                page.click('#add-first-sense-btn')
            elif page.locator('#add-sense-btn').count() > 0:
                page.click('#add-sense-btn')
            else:
                # Try generic button text selectors as fallback
                add_sense_btn = page.locator('button:has-text("Add Sense"), button:has-text("Add Another Sense")')
                if add_sense_btn.count() > 0:
                    add_sense_btn.first.click()
                else:
                    raise RuntimeError('Could not find any Add Sense button on page to create a sense')
            
            # Wait until a VISIBLE definition textarea appears (exclude template)
            for _ in range(50):
                if page.locator('textarea[name*="definition"]:visible').count() > 0:
                    break
                page.wait_for_timeout(100)
            else:
                raise RuntimeError('Timed out waiting for visible definition textarea to appear')
    
    return _ensure_sense


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
