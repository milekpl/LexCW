"""
Test enhanced relations UI functionality.
"""

import pytest
from app import create_app
from app.database.mock_connector import MockDatabaseConnector
from app.services.dictionary_service import DictionaryService
from app.models.entry import Entry
from app.models.sense import Sense


@pytest.fixture
def app():
    """Create test app with mock database."""
    app = create_app('testing')
    app.config['TESTING'] = True
    
    # Setup mock database using injector pattern
    mock_connector = MockDatabaseConnector()
    from app import injector
    injector.binder.bind(DictionaryService, 
                       lambda: DictionaryService(mock_connector))
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_relations_ui_contains_search_functionality(client):
    """Test that the relations UI page includes search functionality."""
    with client.application.app_context():
        from app import injector
        dict_service = injector.get(DictionaryService)
        
        # Create a test entry first
        test_entry = Entry(
            id='main_test_entry',
            lexical_unit={'en': 'main word'},
            senses=[Sense(id='main_sense', glosses={'en': 'main meaning'})]
        )
        dict_service.create_entry(test_entry)
    
    # Access entry edit page 
    response = client.get(f'/entries/{test_entry.id}/edit', follow_redirects=True)
    assert response.status_code == 200
    
    html_content = response.get_data(as_text=True)
    
    # Check that relations section is present
    assert 'Relations' in html_content
    assert 'relations[' in html_content or 'relations-container' in html_content
    assert 'relation' in html_content
    
    # Check that our enhanced relations.js is loaded
    assert 'relations.js' in html_content


def test_correct_search_endpoint_used(client):
    """Test that the correct /api/search endpoint is accessible."""
    # Verify that /api/search works
    response = client.get('/api/search?q=test&limit=5')
    assert response.status_code == 200
    
    data = response.get_json()
    assert 'entries' in data
    assert 'query' in data
    assert data['query'] == 'test'
    
    # Verify that /api/entries/search does NOT exist
    response = client.get('/api/entries/search?q=test&limit=5')
    assert response.status_code == 404
