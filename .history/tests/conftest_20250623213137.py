"""
PyTest fixtures for testing the dictionary writing system.
"""

import os
import pytest
from unittest.mock import patch

from app import create_app
from app.database.basex_connector import BaseXConnector
from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example
from app.models.pronunciation import Pronunciation


@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    app = create_app('testing')
    app.config.update({
        'TESTING': True,
        'SERVER_NAME': 'test.example.com',
        'BASEX_HOST': 'localhost',
        'BASEX_PORT': 1984,
        'BASEX_USERNAME': 'admin',
        'BASEX_PASSWORD': 'admin',
        'BASEX_DATABASE': 'test_dictionary',
    })
    
    # Create application context
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Test client for the application."""
    return app.test_client()


@pytest.fixture
def db_connector():
    """Mock BaseX connector for testing."""
    with patch('app.database.basex_connector.BaseXSession') as mock_session:
        connector = BaseXConnector(
            host='localhost',
            port=1984,
            username='admin',
            password='admin',
            database='test_dictionary'
        )
        
        # Configure the mock
        connector.connect = lambda: True
        connector.execute_query = lambda query, **kwargs: "<entry id='test'>Test Entry</entry>"
        connector.execute_command = lambda cmd, *args: True
        
        yield connector


@pytest.fixture
def sample_entry():
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
def sample_entries():
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
