"""
PyTest fixtures for unit testing - uses mocking instead of real database connections.
This conftest.py is specifically for tests in the /tests/unit/ directory.
"""

from __future__ import annotations

import os
import sys
import pytest
import tempfile
import logging
from unittest.mock import Mock, MagicMock, patch
from typing import Generator

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
def db_app() -> Generator[Flask, None, None]:
    """Create Flask application for unit tests that need database access."""
    from app import create_app
    
    test_app = create_app('testing')
    test_app.config['TESTING'] = True
    test_app.config['WTF_CSRF_ENABLED'] = False
    
    # The db is already initialized in create_app via init_app
    # Just need to create application context
    with test_app.app_context():
        from app.models.workset_models import db
        db.create_all()
        
        yield test_app
        
        # Cleanup
        db.session.remove()
        db.drop_all()


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
def mock_app(mock_dict_service: Mock) -> Generator[Flask, None, None]:
    """Create a Flask app for unit testing with mocked dependencies."""
    from flask import Flask
    import os
    
    template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'app', 'templates')
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
    
    # Mock config manager
    mock_config_manager = Mock()
    mock_config_manager.get_source_language.return_value = {'code': 'en', 'name': 'English'}
    mock_config_manager.get_target_language.return_value = {'code': 'es', 'name': 'Spanish'}
    setattr(app, 'config_manager', mock_config_manager)
    
    with app.app_context():
        yield app


@pytest.fixture
def app(mock_app: Flask) -> Flask:
    """Flask app fixture for unit testing with mocked dependencies.
    
    This fixture delegates to mock_app to provide a simple 'app' fixture
    that tests can use without needing to know about the mocked nature.
    """
    return mock_app


@pytest.fixture
def client(mock_app: Flask) -> FlaskClient:
    """Test client for unit testing with mocked dependencies."""
    return mock_app.test_client()


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
        
        entry.senses.append(sense.to_dict())
        entries.append(entry)
    
    return entries


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


# Unit test configuration
def pytest_configure(config):
    """Configure pytest for unit tests."""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test (uses mocking)"
    )
    config.addinivalue_line(
        "markers", "skip_et_mock: skip ET module mocking for tests that need real XML parsing"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests in unit directory as unit tests."""
    for item in items:
        # If test is in unit directory, mark it as unit test
        if "tests/unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)