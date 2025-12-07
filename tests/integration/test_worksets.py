"""
Test worksets functionality.

NOTE: These tests require PostgreSQL to be configured.
Tests will be skipped if PostgreSQL is not available.
"""

import pytest
from flask import Flask
from app.models.workset import Workset, WorksetQuery, QueryFilter


def test_create_workset(client):
    """Test creating a new workset."""
    query = WorksetQuery(filters=[QueryFilter(field='lexical_unit', operator='starts_with', value='test')])
    response = client.post('/api/worksets', json={
        'name': 'Test Workset',
        'query': query.to_dict()
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True
    assert data['name'] == 'Test Workset'
    assert data['total_entries'] >= 0
    assert 'workset_id' in data

    workset_id = data['workset_id']

    # Verify the workset can be retrieved
    response = client.get(f'/api/worksets/{workset_id}')
    assert response.status_code == 200
    retrieved_data = response.get_json()
    assert retrieved_data['name'] == 'Test Workset'
    assert retrieved_data['id'] == workset_id
