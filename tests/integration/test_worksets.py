"""
Test worksets functionality.

NOTE: These tests require PostgreSQL to be configured.
Tests will be skipped if PostgreSQL is not available.
"""

import pytest
from flask import Flask
from app.models.workset import Workset, WorksetQuery, QueryFilter
from app.services.workset_service import WorksetService


def test_create_workset(client):
    """Test creating a new workset."""
    query = WorksetQuery(filters=[QueryFilter(field='lexical_unit', operator='starts_with', value='test')])
    # Create via service to avoid data-rich JSON endpoint
    service = WorksetService()
    workset = service.create_workset(name='Test Workset', query=query)
    assert workset is not None
    workset_id = workset.id

    # Verify the workset can be retrieved
    response = client.get(f'/api/worksets/{workset_id}')
    assert response.status_code == 200
    retrieved_data = response.get_json()
    assert retrieved_data['name'] == 'Test Workset'
    assert retrieved_data['id'] == workset_id


def test_create_workset_json_rejected(client):
    """POST /api/worksets should reject data-rich JSON inputs (415)."""
    query = WorksetQuery(filters=[QueryFilter(field='lexical_unit', operator='starts_with', value='test')])
    response = client.post('/api/worksets', json={
        'name': 'Test Workset JSON',
        'query': query.to_dict()
    }, content_type='application/json')
    assert response.status_code in (400, 415)
