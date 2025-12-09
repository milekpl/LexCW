"""
Integration tests for merge/split API endpoints.
"""

import pytest
from unittest.mock import Mock, patch
from app import create_app
from app.models.entry import Entry
from app.models.sense import Sense
from app.services.merge_split_service import MergeSplitService

@pytest.fixture
def client():
    """Create test client."""
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    # Mock the merge/split service
    mock_service = Mock(spec=MergeSplitService)
    app.merge_split_service = mock_service

    with app.test_client() as client:
        yield client

def test_get_operations_empty(client):
    """Test getting operations when none exist."""
    # Mock empty operations
    client.application.merge_split_service.get_operation_history.return_value = []

    response = client.get('/api/merge-split/operations')
    assert response.status_code == 200
    assert response.json == []

def test_get_operation_not_found(client):
    """Test getting a non-existent operation."""
    # Mock operation not found
    client.application.merge_split_service.get_operation_by_id.return_value = None

    response = client.get('/api/merge-split/operations/999')
    assert response.status_code == 404
    assert 'error' in response.json

def test_split_entry_api(client):
    """Test split entry API endpoint."""
    # Mock successful split operation
    mock_operation = Mock()
    mock_operation.to_dict.return_value = {
        'operation_type': 'split_entry',
        'source_id': 'entry_001',
        'sense_ids': ['sense_001'],
        'status': 'completed'
    }

    client.application.merge_split_service.split_entry.return_value = mock_operation

    response = client.post('/api/merge-split/entries/entry_001/split', json={
        'sense_ids': ['sense_001'],
        'new_entry_data': {
            'lexical_unit': {'en': 'new entry'}
        }
    })

    assert response.status_code == 201
    assert response.json['success'] is True
    assert response.json['operation']['operation_type'] == 'split_entry'

def test_split_entry_validation_error(client):
    """Test split entry with validation error."""
    from app.utils.exceptions import ValidationError
    client.application.merge_split_service.split_entry.side_effect = ValidationError("Invalid sense IDs")

    response = client.post('/api/merge-split/entries/entry_001/split', json={
        'sense_ids': ['invalid_sense_id'],
        'new_entry_data': {}
    })

    assert response.status_code == 400
    assert 'error' in response.json

def test_split_entry_not_found(client):
    """Test split entry with non-existent source entry."""
    from app.utils.exceptions import NotFoundError
    client.application.merge_split_service.split_entry.side_effect = NotFoundError("Entry not found")

    response = client.post('/api/merge-split/entries/entry_999/split', json={
        'sense_ids': ['sense_001'],
        'new_entry_data': {}
    })

    assert response.status_code == 404
    assert 'error' in response.json

def test_merge_entries_api(client):
    """Test merge entries API endpoint."""
    # Mock successful merge operation
    mock_operation = Mock()
    mock_operation.to_dict.return_value = {
        'operation_type': 'merge_entries',
        'source_id': 'entry_001',
        'target_id': 'entry_002',
        'sense_ids': ['sense_001'],
        'status': 'completed'
    }

    client.application.merge_split_service.merge_entries.return_value = mock_operation

    response = client.post('/api/merge-split/entries/entry_002/merge', json={
        'source_entry_id': 'entry_001',
        'sense_ids': ['sense_001']
    })

    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['operation']['operation_type'] == 'merge_entries'

def test_merge_entries_missing_source_id(client):
    """Test merge entries with missing source_entry_id."""
    response = client.post('/api/merge-split/entries/entry_002/merge', json={
        'sense_ids': ['sense_001']
        # Missing source_entry_id
    })

    assert response.status_code == 400
    assert 'error' in response.json

def test_merge_senses_api(client):
    """Test merge senses API endpoint."""
    # Mock successful merge senses operation
    mock_operation = Mock()
    mock_operation.to_dict.return_value = {
        'operation_type': 'merge_senses',
        'source_id': 'entry_001',
        'target_id': 'sense_001',
        'sense_ids': ['sense_002'],
        'status': 'completed'
    }

    client.application.merge_split_service.merge_senses.return_value = mock_operation

    response = client.post('/api/merge-split/entries/entry_001/senses/sense_001/merge', json={
        'source_sense_ids': ['sense_002']
    })

    assert response.status_code == 200
    assert response.json['success'] is True
    assert response.json['operation']['operation_type'] == 'merge_senses'

def test_get_transfers_empty(client):
    """Test getting transfers when none exist."""
    client.application.merge_split_service.get_sense_transfer_history.return_value = []

    response = client.get('/api/merge-split/transfers')
    assert response.status_code == 200
    assert response.json == []

def test_get_transfers_by_sense(client):
    """Test getting transfers by sense ID."""
    mock_transfer = Mock()
    mock_transfer.to_dict.return_value = {
        'sense_id': 'sense_001',
        'original_entry_id': 'entry_001',
        'new_entry_id': 'entry_002'
    }

    client.application.merge_split_service.get_transfers_by_sense_id.return_value = [mock_transfer]

    response = client.get('/api/merge-split/transfers/sense/sense_001')
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]['sense_id'] == 'sense_001'

def test_get_transfers_by_entry(client):
    """Test getting transfers by entry ID."""
    mock_transfer = Mock()
    mock_transfer.to_dict.return_value = {
        'sense_id': 'sense_001',
        'original_entry_id': 'entry_001',
        'new_entry_id': 'entry_002'
    }

    client.application.merge_split_service.get_transfers_by_entry_id.return_value = [mock_transfer]

    response = client.get('/api/merge-split/transfers/entry/entry_001')
    assert response.status_code == 200
    assert len(response.json) == 1
    assert response.json[0]['original_entry_id'] == 'entry_001'

def test_get_operation_status(client):
    """Test getting operation status."""
    mock_operation = Mock()
    mock_operation.id = 'op_001'
    mock_operation.status = 'completed'
    mock_operation.operation_type = 'split_entry'
    mock_operation.timestamp = '2023-01-01T00:00:00'
    mock_operation.metadata = {}

    client.application.merge_split_service.get_operation_by_id.return_value = mock_operation

    response = client.get('/api/merge-split/operations/op_001/status')
    assert response.status_code == 200
    assert response.json['status'] == 'completed'
    assert response.json['operation_id'] == 'op_001'

def test_get_operation_status_not_found(client):
    """Test getting status of non-existent operation."""
    client.application.merge_split_service.get_operation_by_id.return_value = None

    response = client.get('/api/merge-split/operations/999/status')
    assert response.status_code == 404
    assert 'error' in response.json

def test_merge_entries_with_conflict_resolution(client):
    """Test merge entries with conflict resolution strategy."""
    mock_operation = Mock()
    mock_operation.to_dict.return_value = {
        'operation_type': 'merge_entries',
        'source_id': 'entry_001',
        'target_id': 'entry_002',
        'sense_ids': ['sense_001'],
        'status': 'completed'
    }

    client.application.merge_split_service.merge_entries.return_value = mock_operation

    response = client.post('/api/merge-split/entries/entry_002/merge', json={
        'source_entry_id': 'entry_001',
        'sense_ids': ['sense_001'],
        'conflict_resolution': {
            'duplicate_senses': 'rename'
        }
    })

    assert response.status_code == 200
    assert response.json['success'] is True

def test_merge_senses_with_strategy(client):
    """Test merge senses with specific merge strategy."""
    mock_operation = Mock()
    mock_operation.to_dict.return_value = {
        'operation_type': 'merge_senses',
        'source_id': 'entry_001',
        'target_id': 'sense_001',
        'sense_ids': ['sense_002'],
        'status': 'completed'
    }

    client.application.merge_split_service.merge_senses.return_value = mock_operation

    response = client.post('/api/merge-split/entries/entry_001/senses/sense_001/merge', json={
        'source_sense_ids': ['sense_002'],
        'merge_strategy': 'keep_target'
    })

    assert response.status_code == 200
    assert response.json['success'] is True