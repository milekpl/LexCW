"""
Integration tests for XML Entry CRUD operations via API.

These tests verify that all CRUD operations work correctly with a real BaseX database.
Critical for ensuring data integrity when editing entries via the XML API.
"""

from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient
import json

from app import create_app
from app.services.xml_entry_service import XMLEntryService


# Sample LIFT XML for testing - with proper namespace
SAMPLE_ENTRY_XML = '''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="test_crud_001" dateCreated="2024-01-01T12:00:00Z" dateModified="2024-01-01T12:00:00Z" guid="test_guid_001">
    <lexical-unit>
        <form lang="en"><text>testword</text></form>
    </lexical-unit>
    <sense id="sense_001" order="0">
        <gloss lang="en"><text>a test word</text></gloss>
    </sense>
</entry>'''

UPDATED_ENTRY_XML = '''<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="test_crud_001" dateCreated="2024-01-01T12:00:00Z" dateModified="2024-01-02T12:00:00Z" guid="test_guid_001">
    <lexical-unit>
        <form lang="en"><text>updatedword</text></form>
    </lexical-unit>
    <sense id="sense_001" order="0">
        <gloss lang="en"><text>an updated test word</text></gloss>
    </sense>
</entry>'''


@pytest.fixture(scope='module')
def app():
    """Create test Flask application."""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture(scope='module')
def client(app: Flask) -> FlaskClient:
    """Create test client."""
    return app.test_client()


@pytest.fixture(scope='module')
def xml_service():
    """Create XML Entry Service instance connected to test database."""
    return XMLEntryService(database='dictionary_test')


@pytest.fixture(autouse=True)
def cleanup_test_entries(xml_service: XMLEntryService):
    """Clean up test entries before and after each test."""
    # Cleanup before test
    test_entry_ids = ['test_crud_001', 'test_crud_002', 'test_crud_003', 'nonexistent_entry']
    for entry_id in test_entry_ids:
        try:
            xml_service.delete_entry(entry_id)
        except:
            pass
    
    yield
    
    # Cleanup after test
    for entry_id in test_entry_ids:
        try:
            xml_service.delete_entry(entry_id)
        except:
            pass


class TestXMLEntryCRUD:
    """Test complete CRUD cycle for XML entries."""
    
    def test_create_entry_via_api(self, client: FlaskClient, xml_service: XMLEntryService):
        """Test creating a new entry via API."""
        # Create entry
        response = client.post(
            '/api/xml/entries',
            data=SAMPLE_ENTRY_XML,
            content_type='application/xml'
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['entry_id'] == 'test_crud_001'
        assert data['success']
        
        # Verify entry exists in database
        assert xml_service.entry_exists('test_crud_001')
        
        # Verify entry content
        entry_data = xml_service.get_entry('test_crud_001')
        assert 'testword' in entry_data['xml']
    
    def test_read_entry_via_api(self, client: FlaskClient, xml_service: XMLEntryService):
        """Test reading an entry via API."""
        # First create an entry
        xml_service.create_entry(SAMPLE_ENTRY_XML)
        
        # Read entry via API
        response = client.get('/api/xml/entries/test_crud_001')
        
        assert response.status_code == 200
        assert b'testword' in response.data
        assert b'test_crud_001' in response.data
    
    def test_update_entry_via_api(self, client: FlaskClient, xml_service: XMLEntryService):
        """
        Test updating an existing entry via API.
        
        CRITICAL: This test verifies that the entry is actually updated
        and not deleted. This was a bug where update would delete the entry
        without re-inserting it.
        """
        # First create an entry
        xml_service.create_entry(SAMPLE_ENTRY_XML)
        
        # Count entries before update
        session = xml_service._get_session()
        q = session.query('count(//entry)')
        count_before = int(q.execute())
        q.close()
        
        # Verify entry exists before update
        assert xml_service.entry_exists('test_crud_001')
        
        # Update entry via API
        response = client.put(
            '/api/xml/entries/test_crud_001',
            data=UPDATED_ENTRY_XML,
            content_type='application/xml'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['entry_id'] == 'test_crud_001'
        assert data['success']
        
        # CRITICAL: Verify entry still exists after update
        assert xml_service.entry_exists('test_crud_001'), \
            "Entry was deleted instead of being updated!"
        
        # Verify entry count hasn't changed
        q = session.query('count(//entry)')
        count_after = int(q.execute())
        q.close()
        assert count_after == count_before, \
            f"Entry count changed from {count_before} to {count_after} - entry was deleted!"
        
        # Verify updated content
        entry_data = xml_service.get_entry('test_crud_001')
        assert 'updatedword' in entry_data['xml']
        assert 'testword' not in entry_data['xml']
    
    def test_delete_entry_via_api(self, client: FlaskClient, xml_service: XMLEntryService):
        """Test deleting an entry via API."""
        # First create an entry
        xml_service.create_entry(SAMPLE_ENTRY_XML)
        
        # Delete entry via API
        response = client.delete('/api/xml/entries/test_crud_001')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['entry_id'] == 'test_crud_001'
        assert data['success']
        
        # Verify entry no longer exists
        assert not xml_service.entry_exists('test_crud_001')
    
    def test_full_crud_cycle(self, client: FlaskClient, xml_service: XMLEntryService):
        """Test complete CRUD cycle: Create -> Read -> Update -> Delete."""
        entry_id = 'test_crud_002'
        
        # 1. CREATE
        create_xml = SAMPLE_ENTRY_XML.replace('test_crud_001', entry_id)
        response = client.post(
            '/api/xml/entries',
            data=create_xml,
            content_type='application/xml'
        )
        assert response.status_code == 201
        assert xml_service.entry_exists(entry_id)
        
        # 2. READ
        response = client.get(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200
        assert entry_id.encode() in response.data
        
        # 3. UPDATE
        update_xml = UPDATED_ENTRY_XML.replace('test_crud_001', entry_id)
        response = client.put(
            f'/api/xml/entries/{entry_id}',
            data=update_xml,
            content_type='application/xml'
        )
        assert response.status_code == 200
        assert xml_service.entry_exists(entry_id), "Entry deleted during update!"
        
        # Verify update
        entry_data = xml_service.get_entry(entry_id)
        assert 'updatedword' in entry_data['xml']
        
        # 4. DELETE
        response = client.delete(f'/api/xml/entries/{entry_id}')
        assert response.status_code == 200
        assert not xml_service.entry_exists(entry_id)
    
    def test_update_preserves_other_entries(self, client: FlaskClient, xml_service: XMLEntryService):
        """
        Test that updating one entry doesn't affect other entries.
        
        CRITICAL: This test catches bugs where update operations incorrectly
        delete or modify other entries in the database.
        """
        # Create multiple entries
        entry1_xml = SAMPLE_ENTRY_XML.replace('test_crud_001', 'test_crud_001')
        entry2_xml = SAMPLE_ENTRY_XML.replace('test_crud_001', 'test_crud_002')
        entry3_xml = SAMPLE_ENTRY_XML.replace('test_crud_001', 'test_crud_003')
        
        xml_service.create_entry(entry1_xml)
        xml_service.create_entry(entry2_xml)
        xml_service.create_entry(entry3_xml)
        
        # Count total entries
        session = xml_service._get_session()
        q = session.query('count(//entry)')
        count_before = int(q.execute())
        q.close()
        
        # Update one entry
        update_xml = UPDATED_ENTRY_XML.replace('test_crud_001', 'test_crud_002')
        response = client.put(
            '/api/xml/entries/test_crud_002',
            data=update_xml,
            content_type='application/xml'
        )
        assert response.status_code == 200
        
        # Verify all three entries still exist
        assert xml_service.entry_exists('test_crud_001'), "Entry 1 was deleted!"
        assert xml_service.entry_exists('test_crud_002'), "Entry 2 was deleted!"
        assert xml_service.entry_exists('test_crud_003'), "Entry 3 was deleted!"
        
        # Verify total count unchanged
        q = session.query('count(//entry)')
        count_after = int(q.execute())
        q.close()
        assert count_after == count_before, \
            f"Entry count changed from {count_before} to {count_after}!"
        
        # Verify only entry 2 was updated
        entry2_data = xml_service.get_entry('test_crud_002')
        assert 'updatedword' in entry2_data['xml']
        
        entry1_data = xml_service.get_entry('test_crud_001')
        assert 'testword' in entry1_data['xml']
        assert 'updatedword' not in entry1_data['xml']


class TestXMLEntryAPIErrorHandling:
    """Test error handling in XML Entry API."""
    
    def test_update_nonexistent_entry(self, client: FlaskClient):
        """Test updating an entry that doesn't exist."""
        response = client.put(
            '/api/xml/entries/nonexistent_entry',
            data=SAMPLE_ENTRY_XML.replace('test_crud_001', 'nonexistent_entry'),
            content_type='application/xml'
        )
        
        assert response.status_code == 404
    
    def test_create_duplicate_entry(self, client: FlaskClient, xml_service: XMLEntryService):
        """Test creating an entry with duplicate ID."""
        # Create first entry
        xml_service.create_entry(SAMPLE_ENTRY_XML)
        
        # Try to create duplicate
        response = client.post(
            '/api/xml/entries',
            data=SAMPLE_ENTRY_XML,
            content_type='application/xml'
        )
        
        assert response.status_code == 409  # Conflict
    
    def test_invalid_xml(self, client: FlaskClient):
        """Test submitting invalid XML."""
        invalid_xml = '<entry><unclosed>'
        
        response = client.post(
            '/api/xml/entries',
            data=invalid_xml,
            content_type='application/xml'
        )
        
        assert response.status_code == 400
