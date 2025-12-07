"""
Conftest for E2E tests using Playwright.
"""

from __future__ import annotations

import sys
import os
import pytest
import tempfile
import logging
from typing import Generator
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import fixtures from parent conftest
from tests.conftest import flask_test_server

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def setup_e2e_test_database():
    """
    Set up a persistent test database for E2E tests.
    This ensures the flask_test_server subprocess can access test data.
    """
    from app.database.basex_connector import BaseXConnector
    
    # Create connector to manage test database
    connector = BaseXConnector(
        host=os.getenv('BASEX_HOST', 'localhost'),
        port=int(os.getenv('BASEX_PORT', '1984')),
        username=os.getenv('BASEX_USERNAME', 'admin'),
        password=os.getenv('BASEX_PASSWORD', 'admin'),
        database=None,
    )
    
    test_db = 'dictionary_test'
    
    try:
        connector.connect()
        
        # Drop existing test database if it exists
        try:
            connector.execute_update(f"db:drop('{test_db}')")
            logger.info(f"Dropped existing test database: {test_db}")
        except Exception:
            pass  # Database doesn't exist
        
        # Create new test database
        connector.create_database(test_db)
        connector.database = test_db
        connector.disconnect()
        connector.connect()
        
        # Add sample LIFT content
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
        
        try:
            connector.execute_command(f"ADD {temp_file}")
            logger.info("Added LIFT data to E2E test database")
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
            connector.execute_command(f"ADD {temp_file}")
            logger.info("Added comprehensive ranges.xml to E2E test database")
        finally:
            try:
                os.unlink(temp_file)
            except OSError:
                pass
        
        yield
        
    finally:
        # Clean up test database after all tests
        try:
            connector.execute_update(f"db:drop('{test_db}')")
            logger.info(f"Dropped E2E test database: {test_db}")
        except Exception as e:
            logger.warning(f"Failed to drop E2E test database: {e}")
        finally:
            try:
                connector.disconnect()
            except Exception:
                pass


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


@pytest.fixture
def app():
    """Create Flask application for E2E tests."""
    from app import create_app
    app = create_app('testing')
    app.config['TESTING'] = True
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
