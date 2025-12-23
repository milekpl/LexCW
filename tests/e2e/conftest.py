"""
Conftest for E2E tests using Playwright.
"""

from __future__ import annotations

import sys
import os
import pytest
import tempfile
import logging
import uuid
from typing import Generator
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import safety utilities
from tests.test_db_safety_utils import generate_safe_db_name, is_safe_database_name

# Import fixtures from parent conftest
from tests.conftest import flask_test_server

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_e2e_test_database():
    """
    Set up a safe, isolated test database for E2E tests.
    
    This fixture provides stronger isolation guarantees:
    - Uses safe database naming with timestamp and test type
    - Validates database name safety before creation
    - Restores original environment variables after tests
    - Performs atomic cleanup with verification
    - Prevents environment variable leakage
    """
    from app.database.basex_connector import BaseXConnector
    
    # Store original environment variables for restoration
    original_test_db = os.environ.get('TEST_DB_NAME')
    original_basex_db = os.environ.get('BASEX_DATABASE')
    
    # Generate safe database name
    test_db = os.environ.get('TEST_DB_NAME')
    if not test_db:
        test_db = generate_safe_db_name('e2e')
        # Validate the generated name
        if not is_safe_database_name(test_db):
            pytest.fail(f"Generated unsafe E2E database name: {test_db}")
    
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=None,
    )
    
    try:
        # Set isolated environment for E2E tests
        os.environ['TEST_DB_NAME'] = test_db
        os.environ['BASEX_DATABASE'] = test_db
        
        connector.connect()
        
        # Drop existing test database if it exists
        try:
            connector.execute_command(f"DROP DB {test_db}")
            logger.info(f"Dropped existing E2E test database: {test_db}")
        except Exception:
            pass  # Database doesn't exist
        
        # Create new test database
        connector.create_database(test_db)
        connector.database = test_db
        connector.disconnect()
        connector.connect()
        
        logger.info(f"Created safe E2E test database: {test_db}")
        
        # Add sample LIFT content with dateCreated and dateModified
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            sample_lift = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
    <entry id="test_entry_1" dateCreated="2024-01-15T10:30:00Z" dateModified="2024-03-20T14:45:00Z">
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
    <entry id="test_entry_2" dateCreated="2024-01-16T11:30:00Z" dateModified="2024-03-21T15:45:00Z">
        <lexical-unit>
            <form lang="en"><text>component</text></form>
        </lexical-unit>
        <sense id="test_sense_2">
            <definition>
                <form lang="en"><text>A component entry</text></form>
            </definition>
            <gloss lang="pl"><text>komponent</text></gloss>
        </sense>
    </entry>
    <entry id="test_entry_3" dateCreated="2024-01-17T12:30:00Z" dateModified="2024-03-22T16:45:00Z">
        <lexical-unit>
            <form lang="en"><text>variant</text></form>
        </lexical-unit>
        <sense id="test_sense_3">
            <definition>
                <form lang="en"><text>A variant entry</text></form>
            </definition>
            <gloss lang="pl"><text>wariant</text></gloss>
        </sense>
    </entry>
</lift>'''
            f.write(sample_lift)
            temp_file = f.name
        
        try:
            connector.execute_command(f"ADD {temp_file}")
            logger.info("Added LIFT data to safe E2E test database")
        finally:
            try:
                os.unlink(temp_file)
            except OSError:
                pass
        
        # Add comprehensive ranges.xml
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            ranges_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <range id="grammatical-info" href="http://fieldworks.sil.org/lift/grammatical-info">
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
    <range id="lexical-relation" href="http://fieldworks.sil.org/lift/lexical-relation">
        <range-element id="_component-lexeme" guid="4e1c72b2-7430-4eb9-a9d2-4b31c5620804">
            <label>
                <form lang="en"><text>Component</text></form>
            </label>
        </range-element>
        <range-element id="_main-entry" guid="45e6b7ef-0e55-448a-a7f2-93d485712c54">
            <label>
                <form lang="en"><text>Main Entry</text></form>
            </label>
        </range-element>
    </range>
    <range id="semantic-domain-ddp4" href="http://fieldworks.sil.org/lift/semantic-domain-ddp4">
        <range-element id="1" guid="63403699-07c1-4d82-91ab-f8046c335e11">
            <label>
                <form lang="en"><text>Universe, creation</text></form>
            </label>
        </range-element>
        <range-element id="1.1" guid="999581c4-1611-4acb-ae1b-cc1f7e0e18e5" parent="1">
            <label>
                <form lang="en"><text>Sky</text></form>
            </label>
        </range-element>
    </range>
    <range id="anthro-code" href="http://fieldworks.sil.org/lift/anthro-code">
        <range-element id="1" guid="d12cf2e5-22c8-4826-9d98-8f669f4c5496">
            <label>
                <form lang="en"><text>Social organization</text></form>
            </label>
        </range-element>
    </range>
    <range id="domain-type" href="http://fieldworks.sil.org/lift/domain-type">
        <range-element id="agriculture" guid="0fc97f63-a059-4894-84bf-c29a58f96dc4">
            <label>
                <form lang="en"><text>Agriculture</text></form>
            </label>
        </range-element>
        <range-element id="grammar" guid="56d33d26-e0fb-4840-bea6-e7e1b86f3e95">
            <label>
                <form lang="en"><text>Grammar</text></form>
            </label>
        </range-element>
    </range>
    <range id="usage-type" href="http://fieldworks.sil.org/lift/usage-type">
        <range-element id="archaic" guid="4f845bbd-1bf4-4c8b-9f50-76f1b69e0d3d">
            <label>
                <form lang="en"><text>Archaic</text></form>
            </label>
        </range-element>
        <range-element id="colloquial" guid="cf829d77-cf92-4328-bc86-72a44e42fbf0">
            <label>
                <form lang="en"><text>Colloquial</text></form>
            </label>
        </range-element>
    </range>
</lift-ranges>'''
            f.write(ranges_xml)
            temp_file = f.name
        
        try:
            connector.execute_command(f"ADD TO ranges.xml {temp_file}")
            logger.info("Added comprehensive ranges.xml to safe E2E test database")
        finally:
            try:
                os.unlink(temp_file)
            except OSError:
                pass
        
        # CRITICAL: Disconnect setup connector before yielding to tests
        # If we keep this connection open, it will block database updates in the Flask server
        try:
            connector.disconnect()
            logger.info("Disconnected setup connector before tests run")
        except Exception as e:
            logger.warning(f"Failed to disconnect setup connector: {e}")
        
        yield
        
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
                    if test_db in result:
                        cleanup_connector.execute_command(f"DROP DB {test_db}")
                        logger.info(f"Successfully dropped safe E2E test database: {test_db}")
                    else:
                        logger.warning(f"E2E test database {test_db} not found during cleanup")
                except Exception as e:
                    logger.warning(f"Could not verify E2E database existence before cleanup: {e}")
                
            finally:
                try:
                    cleanup_connector.disconnect()
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Failed to clean up E2E test database {test_db}: {e}")
            # Even if cleanup fails, we've restored the environment variables
            raise


@pytest.fixture(scope="session")
def browser() -> Generator[Browser, None, None]:
    """Create a browser instance for the session."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Create a new browser context for each test."""
    context = browser.new_context()
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext, flask_test_server: str) -> Generator[Page, None, None]:
    """Create a new page for each test with base URL."""
    page = context.new_page()
    page.set_default_timeout(30000)  # 30 seconds
    # Store base URL for tests to use
    page._base_url = flask_test_server  # type: ignore
    yield page
    page.close()


@pytest.fixture(scope="function")
def app_url(flask_test_server: str) -> str:
    """Provide application base URL for tests."""
    return flask_test_server


@pytest.fixture(scope="function")
def e2e_dict_service():
    """Create a DictionaryService that uses the E2E test database (dictionary_test)."""
    from app.database.basex_connector import BaseXConnector
    from app.services.dictionary_service import DictionaryService

    test_db = os.environ.get('TEST_DB_NAME', 'dictionary_test')

    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=test_db,  # Use the E2E test database
    )
    connector.connect()
    
    service = DictionaryService(db_connector=connector)
    yield service
    
    # Cleanup
    connector.disconnect()


@pytest.fixture
def app():
    """Create Flask application for E2E tests with default project settings."""
    from app import create_app
    app = create_app('testing')
    app.config['TESTING'] = True
    
    # Set default project settings if not already configured
    if not app.config.get('PROJECT_SETTINGS'):
        app.config['PROJECT_SETTINGS'] = [{
            'project_name': 'test_project',
            'source_language': {'code': 'en', 'name': 'English'},
            'target_languages': [{'code': 'pl', 'name': 'Polish'}]
        }]
    
    return app



__all__ = [
    'browser',
    'context',
    'page',
    'flask_test_server',
    'app_url',
    'app',
    'setup_e2e_test_database',
]


@pytest.fixture(autouse=True)
def shorten_playwright_timeouts(page):
    """Reduce Playwright default timeouts for faster failures in E2E.

    Many tests previously waited the default 30s for fills/selectors which
    makes the whole suite slow when elements are not present. This fixture
    shortens timeouts so failures surface quickly and tests run faster.
    """
    # 5 seconds is a reasonable balance between flakiness and speed
    page.set_default_timeout(5000)
    page.set_default_navigation_timeout(5000)
    yield

@pytest.fixture
def ensure_sense():
    """Helper that ensures the entry form has at least one real sense (not the template).

    Usage: call ensure_sense(page) in tests before filling sense-level fields.
    """
    def _ensure(page):
        # If a VISIBLE definition textarea is present, we assume a sense exists
        if page.locator('textarea[name*="definition"]:visible').count() == 0:
            # Try the explicit first-sense button first
            if page.locator('#add-first-sense-btn').count() > 0 and page.locator('#add-first-sense-btn').first.is_visible():
                page.click('#add-first-sense-btn')
            # Fallback to generic add-sense button
            elif page.locator('#add-sense-btn').count() > 0 and page.locator('#add-sense-btn').first.is_visible():
                page.click('#add-sense-btn')
            else:
                # Try some generic selectors used in older UIs
                generic = page.locator('.add-sense-btn, button:has-text("Add Another Sense"), button:has-text("Add Sense")')
                if generic.count() > 0 and generic.first.is_visible():
                    generic.first.click()
                else:
                    raise RuntimeError('Could not find any Add Sense button on page to create a sense')

            # Wait for a VISIBLE definition textarea to appear
            for _ in range(50):
                if page.locator('textarea[name*="definition"]:visible').count() > 0:
                    break
                page.wait_for_timeout(100)
            else:
                raise RuntimeError('Timed out waiting for visible definition textarea to appear')

    return _ensure