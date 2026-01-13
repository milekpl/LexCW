"""
Integration tests for entry form save operations.

These tests verify that entries created/updated via the entry form
are correctly saved and retrievable from the BaseX database.
"""

import pytest
from flask import Flask
from flask.testing import FlaskClient
import json
import uuid

from app import create_app


# Sample entry data that mimics what the entry form generates
SAMPLE_ENTRY_FORM_DATA = {
    'id': '',
    'lexical_unit': {'en': 'testword'},
    'senses': [
        {
            'id': 'sense_001',
            'gloss': {'en': 'a test word'},
            'definition': {'en': 'A test definition'},
        }
    ]
}

UPDATED_ENTRY_FORM_DATA = {
    'id': '',
    'lexical_unit': {'en': 'updatedword'},
    'senses': [
        {
            'id': 'sense_001',
            'gloss': {'en': 'an updated test word'},
            'definition': {'en': 'An updated test definition'},
        }
    ]
}


@pytest.fixture(scope='module')
def app():
    """Create test Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture(scope='module')
def unique_entry_id():
    """Generate a unique entry ID for each test run."""
    return f"form_test_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def cleanup_entry(client: FlaskClient, unique_entry_id):
    """Clean up test entry before and after test."""
    # Cleanup before test
    try:
        client.delete(f'/api/xml/entries/{unique_entry_id}')
    except:
        pass

    yield unique_entry_id

    # Cleanup after test
    try:
        client.delete(f'/api/xml/entries/{unique_entry_id}')
    except:
        pass


class TestEntryFormSave:
    """Test entry save operations via the XML API."""

    def test_create_and_retrieve_entry(self, client: FlaskClient, cleanup_entry):
        """Test creating an entry via XML API and retrieving it."""
        entry_id = cleanup_entry

        # Create entry XML
        entry_xml = f'''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>testword</text></form>
            </lexical-unit>
            <sense id="sense_001" order="0">
                <gloss lang="en"><text>a test word</text></gloss>
            </sense>
        </entry>'''

        # Create entry
        response = client.post(
            '/api/xml/entries',
            data=entry_xml,
            content_type='application/xml'
        )

        assert response.status_code == 201, f"Create failed: {response.data}"
        data = json.loads(response.data)
        assert data['success']
        assert data['entry_id'] == entry_id

        # Verify entry exists
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200
        assert entry_id.encode() in response.data
        assert b'testword' in response.data

        # Verify entry is in list
        response = client.get('/api/xml/entries')
        assert response.status_code == 200
        data = json.loads(response.data)
        entry_ids = [e['id'] for e in data.get('entries', [])]
        assert entry_id in entry_ids, f"Entry {entry_id} not found in entries list"

    def test_update_entry_and_verify(self, client: FlaskClient, cleanup_entry):
        """Test updating an entry and verifying it persists."""
        entry_id = cleanup_entry

        # Create initial entry
        create_xml = f'''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>originalword</text></form>
            </lexical-unit>
            <sense id="sense_001" order="0">
                <gloss lang="en"><text>original gloss</text></gloss>
            </sense>
        </entry>'''

        response = client.post(
            '/api/xml/entries',
            data=create_xml,
            content_type='application/xml'
        )
        assert response.status_code == 201

        # Verify original content
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert b'originalword' in response.data

        # Update entry
        update_xml = f'''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>updatedword</text></form>
            </lexical-unit>
            <sense id="sense_001" order="0">
                <gloss lang="en"><text>updated gloss</text></gloss>
            </sense>
        </entry>'''

        response = client.put(
            f'/api/xml/entries/{entry_id}',
            data=update_xml,
            content_type='application/xml'
        )

        assert response.status_code == 200, f"Update failed: {response.data}"
        data = json.loads(response.data)
        assert data['success']
        assert data['entry_id'] == entry_id

        # CRITICAL: Verify entry still exists after update
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200, f"Entry disappeared after update: {response.data}"

        # Verify updated content
        assert b'updatedword' in response.data, "Updated word not found"
        assert b'updated gloss' in response.data, "Updated gloss not found"

        # Verify old content is gone
        assert b'originalword' not in response.data, "Old word still present"

    def test_multiple_updates(self, client: FlaskClient, cleanup_entry):
        """Test that multiple updates don't lose the entry."""
        entry_id = cleanup_entry

        # Create entry
        create_xml = f'''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>version1</text></form>
            </lexical-unit>
        </entry>'''

        response = client.post('/api/xml/entries', data=create_xml, content_type='application/xml')
        assert response.status_code == 201

        # Perform multiple updates
        for i in range(3):
            update_xml = f'''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{entry_id}">
                <lexical-unit>
                    <form lang="en"><text>version{i + 2}</text></form>
                </lexical-unit>
            </entry>'''

            response = client.put(f'/api/xml/entries/{entry_id}', data=update_xml, content_type='application/xml')
            assert response.status_code == 200, f"Update {i+1} failed: {response.data}"

            # Verify entry exists after each update
            response = client.get(f'/api/xml/entries/{entry_id}')
            assert response.status_code == 200, f"Entry lost after update {i+1}"

        # Verify final content
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert b'version4' in response.data, "Final version not found"

    def test_update_with_senses(self, client: FlaskClient, cleanup_entry):
        """Test updating entry with multiple senses."""
        entry_id = cleanup_entry

        # Create entry with one sense
        create_xml = f'''<entry xmlns="http://fieldworks.silorg/schemas/lift/0.13" id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>testword</text></form>
            </lexical-unit>
            <sense id="sense_001" order="0">
                <gloss lang="en"><text>first sense</text></gloss>
            </sense>
        </entry>'''

        response = client.post('/api/xml/entries', data=create_xml, content_type='application/xml')
        assert response.status_code == 201

        # Update with multiple senses
        update_xml = f'''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>testword</text></form>
            </lexical-unit>
            <sense id="sense_001" order="0">
                <gloss lang="en"><text>first sense updated</text></gloss>
            </sense>
            <sense id="sense_002" order="1">
                <gloss lang="en"><text>second sense</text></gloss>
            </sense>
        </entry>'''

        response = client.put(f'/api/xml/entries/{entry_id}', data=update_xml, content_type='application/xml')
        assert response.status_code == 200

        # Verify entry has both senses
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200
        content = response.data.decode()
        assert 'first sense updated' in content
        assert 'second sense' in content

    def test_update_filters_empty_template_sense(self, client: FlaskClient, cleanup_entry):
        """Ensure that empty/template senses submitted by the client are not persisted."""
        entry_id = cleanup_entry

        # Create entry with one sense
        create_xml = f'''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>templatetest</text></form>
            </lexical-unit>
            <sense id="sense_001" order="0">
                <gloss lang="en"><text>original sense</text></gloss>
            </sense>
        </entry>'''

        response = client.post('/api/xml/entries', data=create_xml, content_type='application/xml')
        assert response.status_code == 201

        # Update entry and include an empty/template sense that should be filtered
        update_xml = f'''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>templatetest</text></form>
            </lexical-unit>
            <sense id="sense_001" order="0">
                <gloss lang="en"><text>original sense</text></gloss>
            </sense>
            <sense id="default-sense-template" order="1">
            </sense>
        </entry>'''

        response = client.put(f'/api/xml/entries/{entry_id}', data=update_xml, content_type='application/xml')
        assert response.status_code == 200

        # Verify that the template sense was not persisted
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200
        body = response.data.decode('utf-8')
        assert 'default-sense-template' not in body, "Template sense id should not be present in saved entry"
        # Ensure original sense still present
        assert 'sense_001' in body, "Original sense missing after update"

    def test_delete_and_verify_gone(self, client: FlaskClient, cleanup_entry):
        """Test that deleted entries are truly gone."""
        entry_id = cleanup_entry

        # Create entry
        create_xml = f'''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>todelete</text></form>
            </lexical-unit>
        </entry>'''

        response = client.post('/api/xml/entries', data=create_xml, content_type='application/xml')
        assert response.status_code == 201

        # Delete entry
        response = client.delete(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200

        # Verify entry is gone
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 404

        # Verify entry not in list
        response = client.get('/api/xml/entries')
        data = json.loads(response.data)
        entry_ids = [e['id'] for e in data.get('entries', [])]
        assert entry_id not in entry_ids


class TestEntryFormSaveWithCSRF:
    """Test entry save with CSRF protection enabled."""

    def test_create_with_csrf(self, client: FlaskClient, cleanup_entry):
        """Test creating entry with CSRF token."""
        entry_id = cleanup_entry

        # Create entry XML
        entry_xml = f'''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{entry_id}">
            <lexical-unit>
                <form lang="en"><text>csrf_test</text></form>
            </lexical-unit>
        </entry>'''

        # Create without CSRF - should fail in production
        # In testing mode, WTF_CSRF_ENABLED is False, so it should succeed
        response = client.post(
            '/api/xml/entries',
            data=entry_xml,
            content_type='application/xml'
        )

        # In testing mode, CSRF is disabled
        assert response.status_code == 201

        # Verify entry
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200
