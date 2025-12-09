"""
HTTP/Flask route tests for editing non-existent entries.

Tests the complete HTTP workflow including:
1. GET /entries/{id}/edit for a non-existent entry (should show empty form)
2. POST /entries/{id}/edit with data (should create the entry)
3. Saving relations to non-existent targets
"""

from __future__ import annotations

import pytest
import json
from flask.testing import FlaskClient


@pytest.mark.integration
class TestEditNonexistentEntryRoute:
    """Test the Flask route for editing non-existent entries."""

    def test_get_nonexistent_entry_shows_form(self, client: FlaskClient, app) -> None:
        """
        Test that GET /entries/{id}/edit for a non-existent entry shows the form.
        
        The form should be empty but functional, allowing the user to create
        the entry.
        """
        # Access the edit form for a non-existent entry
        response = client.get('/entries/test_nonexistent_entry_12345/edit')
        
        # Should return 200 (not 404)
        assert response.status_code == 200
        
        # Should contain the form HTML
        assert b'entry_form' in response.data or b'form' in response.data
        
        # Should contain the entry ID in the form
        assert b'test_nonexistent_entry_12345' in response.data

    def test_post_nonexistent_entry_creates_it(self, client: FlaskClient) -> None:
        """
        Test that POST /entries/{id}/edit creates a non-existent entry.
        """
        entry_id = 'test_created_via_post_12345'
        
        # Prepare entry data with relations
        entry_data = {
            'id': entry_id,
            'lexical_unit[en]': 'test word',
            'senses[0].id': 'sense1',
            'senses[0].definition[en]': 'A test definition',
            'senses[0].relations[0].type': 'synonym',
            'senses[0].relations[0].ref': 'nonexistent-target-uuid'
        }
        
        # POST the form data
        response = client.post(f'/entries/{entry_id}/edit', data=entry_data)
        
        # Should succeed
        assert response.status_code in [200, 302], f"Got {response.status_code}: {response.data}"
        
        # Verify the entry was created by trying to retrieve it
        response = client.get(f'/entries/{entry_id}/edit')
        assert response.status_code == 200
        assert entry_id.encode() in response.data

    def test_post_nonexistent_entry_with_json_data(self, client: FlaskClient) -> None:
        """
        Test that POST /entries/{id}/edit works with JSON data.
        """
        entry_id = 'test_created_via_json_12345'
        
        entry_data = {
            'id': entry_id,
            'lexical_unit': {'en': 'test word'},
            'senses': [
                {
                    'id': 'sense1',
                    'definition': {'en': 'A test definition'},
                    'relations': [
                        {
                            'type': 'Porównaj',
                            'ref': 'nonexistent-uuid-target'
                        }
                    ]
                }
            ]
        }
        
        response = client.post(
            f'/entries/{entry_id}/edit',
            data=json.dumps(entry_data),
            content_type='application/json'
        )
        
        # Should succeed (200 or JSON response)
        assert response.status_code in [200, 201, 302], \
            f"Expected 200/201/302, got {response.status_code}: {response.data}"

    def test_multiple_relations_to_nonexistent_targets(self, client: FlaskClient) -> None:
        """
        Test that an entry can have multiple relations to non-existent targets.
        """
        entry_id = 'test_multiple_relations_12345'
        
        # Entry with multiple sense relations to non-existent targets
        entry_data = {
            'id': entry_id,
            'lexical_unit[en]': 'complex word',
            'senses[0].id': 'sense1',
            'senses[0].definition[en]': 'First meaning',
            'senses[0].relations[0].type': 'synonym',
            'senses[0].relations[0].ref': 'uuid-target-1',
            'senses[0].relations[1].type': 'antonym',
            'senses[0].relations[1].ref': 'uuid-target-2',
            'senses[0].relations[2].type': 'Porównaj',
            'senses[0].relations[2].ref': 'uuid-target-3'
        }
        
        response = client.post(f'/entries/{entry_id}/edit', data=entry_data)
        assert response.status_code in [200, 302]
        
        # Verify entry was created
        response = client.get(f'/entries/{entry_id}/edit')
        assert response.status_code == 200
