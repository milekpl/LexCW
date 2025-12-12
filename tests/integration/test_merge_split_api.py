"""
Integration tests for merge/split API endpoints.
"""

import pytest
from unittest.mock import Mock, patch
from app import create_app
from app.models.entry import Entry
from app.models.sense import Sense
from app.services.merge_split_service import MergeSplitService
from app.services.operation_history_service import OperationHistoryService
import os
import tempfile
import json

@pytest.fixture
def history_file():
    """Create a temporary history file for testing."""
    with tempfile.NamedTemporaryFile(delete=False, mode='w+', encoding='utf-8') as f:
        json.dump({'operations': [], 'transfers': []}, f)
        f.flush()
        file_path = f.name
    
    yield file_path
    
    # Cleanup: remove the temporary file
    os.unlink(file_path)

@pytest.fixture
def mock_dictionary_service():
    """Create a mock dictionary service."""
    return Mock()

@pytest.fixture
def client(mock_dictionary_service, history_file):
    """Create test client with a real MergeSplitService and mocked dependencies."""
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    # Create real history service with temporary file
    real_history_service = OperationHistoryService(history_file_path=history_file)

    # Inject a real MergeSplitService with mocked dictionary_service and real history_service
    app.merge_split_service = MergeSplitService(
        dictionary_service=mock_dictionary_service,
        history_service=real_history_service
    )

    with app.test_client() as client:
        yield client

def test_get_operations_empty(client, mock_dictionary_service):
    """Test getting operations when none exist."""
    # The history service starts empty
    response = client.get('/api/merge-split/operations')
    assert response.status_code == 200
    assert response.json == []

def test_get_operation_not_found(client, mock_dictionary_service):
    """Test getting a non-existent operation."""
    # The history service starts empty, so any ID will not be found
    response = client.get('/api/merge-split/operations/999')
    assert response.status_code == 404
    assert 'error' in response.json

def test_split_entry_api(client, mock_dictionary_service):
    """Test split entry API endpoint."""
    source_entry = Entry(
        id_="entry_001",
        lexical_unit={"en": "test"},
        senses=[
            Sense(id_="sense_001", glosses={"en": "first sense"}),
            Sense(id_="sense_002", glosses={"en": "second sense"})
        ]
    )
    mock_dictionary_service.get_entry.return_value = source_entry
    mock_dictionary_service.create_entry.return_value = "new_entry_id" # Return value not used by service

    response = client.post('/api/merge-split/entries/entry_001/split', json={
        'sense_ids': ['sense_001'],
        'new_entry_data': {
            'lexical_unit': {'en': 'new entry'}
        }
    })

    assert response.status_code == 201
    assert response.json['success'] is True
    assert response.json['operation']['operation_type'] == 'split_entry'
    assert mock_dictionary_service.get_entry.called
    assert mock_dictionary_service.create_entry.called
    assert mock_dictionary_service.update_entry.called

def test_split_entry_validation_error(client, mock_dictionary_service):
    """Test split entry with validation error (non-existent sense)."""
    source_entry = Entry(
        id_="entry_001",
        lexical_unit={"en": "test"},
        senses=[
            Sense(id_="sense_001", glosses={"en": "first sense"})
        ]
    )
    mock_dictionary_service.get_entry.return_value = source_entry

    response = client.post('/api/merge-split/entries/entry_001/split', json={
        'sense_ids': ['invalid_sense_id'], # This sense doesn't exist in source_entry
        'new_entry_data': {}
    })

    assert response.status_code == 400
    assert 'error' in response.json
    assert "Sense ID invalid_sense_id not found in source entry" in response.json['error']

def test_split_entry_not_found(client, mock_dictionary_service):
    """Test split entry with non-existent source entry."""
    mock_dictionary_service.get_entry.return_value = None

    response = client.post('/api/merge-split/entries/entry_999/split', json={
        'sense_ids': ['sense_001'],
        'new_entry_data': {}
    })

    assert response.status_code == 404
    assert 'error' in response.json
    assert "Source entry entry_999 not found" in response.json['error']

def test_merge_entries_api(client, mock_dictionary_service):
    """Test merge entries API endpoint."""
    source_entry = Entry(
        id_="entry_001",
        lexical_unit={"en": "source"},
        senses=[
            Sense(id_="sense_001", glosses={"en": "source sense 1"}),
            Sense(id_="sense_002", glosses={"en": "source sense 2"})
        ]
    )

    target_entry = Entry(
        id_="entry_002",
        lexical_unit={"en": "target"},
        senses=[
            Sense(id_="sense_003", glosses={"en": "target sense 1"})
        ]
    )
    
    def get_entry_side_effect(eid):
        if eid == "entry_001":
            return source_entry
        if eid == "entry_002":
            return target_entry
        return None
    
    mock_dictionary_service.get_entry.side_effect = get_entry_side_effect
    
    response = client.post('/api/merge-split/entries/entry_002/merge', json={
        'source_entry_id': 'entry_001',
        'sense_ids': ['sense_001']
    })

    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['operation']['operation_type'] == 'merge_entries'
    assert mock_dictionary_service.get_entry.called
    assert mock_dictionary_service.update_entry.call_count == 2 # target and source

def test_merge_entries_missing_source_id(client, mock_dictionary_service):
    """Test merge entries with missing source_entry_id in JSON body."""
    # This test is for the API endpoint's request parsing, not the service logic
    response = client.post('/api/merge-split/entries/entry_002/merge', json={
        'sense_ids': ['sense_001']
        # Missing source_entry_id
    })

    assert response.status_code == 400
    assert 'error' in response.json
    assert "source_entry_id is required" in response.json['error']


def test_merge_senses_api(client, mock_dictionary_service):
    """Test merge senses API endpoint."""
    entry = Entry(
        id_="entry_001",
        lexical_unit={"en": "test"},
        senses=[
            Sense(id_="sense_001", glosses={"en": "first sense"}),
            Sense(id_="sense_002", glosses={"en": "second sense"}),
            Sense(id_="sense_003", glosses={"en": "third sense"})
        ]
    )
    mock_dictionary_service.get_entry.return_value = entry

    response = client.post('/api/merge-split/entries/entry_001/senses/sense_001/merge', json={
        'source_sense_ids': ['sense_002']
    })

    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['operation']['operation_type'] == 'merge_senses'
    assert mock_dictionary_service.get_entry.called
    assert mock_dictionary_service.update_entry.called

def test_get_transfers_empty(client):
    """Test getting transfers when none exist."""
    response = client.get('/api/merge-split/transfers')
    assert response.status_code == 200
    assert response.json == []

def test_get_transfers_by_sense(client, mock_dictionary_service):
    """Test getting transfers by sense ID."""
    # Perform an operation that creates transfers
    source_entry = Entry(
        id_="entry_001",
        lexical_unit={"en": "test"},
        senses=[
            Sense(id_="sense_001", glosses={"en": "first sense"}),
            Sense(id_="sense_002", glosses={"en": "second sense"})
        ]
    )
    mock_dictionary_service.get_entry.return_value = source_entry
    mock_dictionary_service.create_entry.return_value = "new_entry_id"

    client.post('/api/merge-split/entries/entry_001/split', json={
        'sense_ids': ['sense_001'],
        'new_entry_data': { 'lexical_unit': {'en': 'new entry'} }
    })

    response = client.get('/api/merge-split/transfers/sense/sense_001')
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]['sense_id'] == 'sense_001'

def test_get_transfers_by_entry(client, mock_dictionary_service):
    """Test getting transfers by entry ID."""
    # Perform an operation that creates transfers
    source_entry = Entry(
        id_="entry_001",
        lexical_unit={"en": "test"},
        senses=[
            Sense(id_="sense_001", glosses={"en": "first sense"}),
            Sense(id_="sense_002", glosses={"en": "second sense"})
        ]
    )
    mock_dictionary_service.get_entry.return_value = source_entry
    mock_dictionary_service.create_entry.return_value = "new_entry_id"

    client.post('/api/merge-split/entries/entry_001/split', json={
        'sense_ids': ['sense_001'],
        'new_entry_data': { 'lexical_unit': {'en': 'new entry'} }
    })

    response = client.get('/api/merge-split/transfers/entry/entry_001')
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]['original_entry_id'] == 'entry_001'

def test_get_operation_status(client, mock_dictionary_service):
    """Test getting operation status."""
    # Perform an operation
    source_entry = Entry(
        id_="entry_001",
        lexical_unit={"en": "test"},
        senses=[
            Sense(id_="sense_001", glosses={"en": "first sense"}),
            Sense(id_="sense_002", glosses={"en": "second sense"})
        ]
    )
    mock_dictionary_service.get_entry.return_value = source_entry
    mock_dictionary_service.create_entry.return_value = "new_entry_id"

    split_response = client.post('/api/merge-split/entries/entry_001/split', json={
        'sense_ids': ['sense_001'],
        'new_entry_data': { 'lexical_unit': {'en': 'new entry'} }
    })
    operation_id = split_response.json['operation']['id']

    response = client.get(f'/api/merge-split/operations/{operation_id}/status')
    assert response.status_code == 200
    assert response.json['status'] == 'completed'
    assert response.json['operation_id'] == operation_id

def test_get_operation_status_not_found(client):
    """Test getting status of non-existent operation."""
    response = client.get('/api/merge-split/operations/999/status')
    assert response.status_code == 404
    assert 'error' in response.json

def test_merge_entries_with_conflict_resolution(client, mock_dictionary_service):
    """Test merge entries with conflict resolution strategy."""
    source_entry = Entry(
        id_="entry_001",
        lexical_unit={"en": "source"},
        senses=[
            Sense(id_="sense_001", glosses={"en": "source sense 1"}),
            Sense(id_="sense_002", glosses={"en": "source sense 2"})
        ]
    )

    target_entry = Entry(
        id_="entry_002",
        lexical_unit={"en": "target"},
        senses=[
            Sense(id_="sense_001", glosses={"en": "target sense 1"}), # Conflict here
            Sense(id_="sense_003", glosses={"en": "target sense 2"})
        ]
    )
    
    def get_entry_side_effect(eid):
        if eid == "entry_001":
            return source_entry
        if eid == "entry_002":
            return target_entry
        return None
    
    mock_dictionary_service.get_entry.side_effect = get_entry_side_effect

    response = client.post('/api/merge-split/entries/entry_002/merge', json={
        'source_entry_id': 'entry_001',
        'sense_ids': ['sense_001'],
        'conflict_resolution': {
            'duplicate_senses': 'rename'
        }
    })

    assert response.status_code == 200
    assert response.json['success'] is True
    assert mock_dictionary_service.update_entry.called # ensure update was called
    # Further assertions could check the content of updated entries, but that requires more complex mocking


def test_merge_senses_with_strategy(client, mock_dictionary_service):
    """Test merge senses with specific merge strategy."""
    entry = Entry(
        id_="entry_001",
        lexical_unit={"en": "test"},
        senses=[
            Sense(id_="sense_001", glosses={"en": "first sense"}),
            Sense(id_="sense_002", glosses={"en": "second sense"}),
            Sense(id_="sense_003", glosses={"en": "third sense"})
        ]
    )
    mock_dictionary_service.get_entry.return_value = entry

    response = client.post('/api/merge-split/entries/entry_001/senses/sense_001/merge', json={
        'source_sense_ids': ['sense_002'],
        'merge_strategy': 'keep_target'
    })

    assert response.status_code == 200
    assert response.json['success'] is True
    assert mock_dictionary_service.update_entry.called # ensure update was called

