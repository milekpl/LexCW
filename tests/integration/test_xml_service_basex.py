"""
Integration tests for XML Entry Service with real BaseX database

These tests require a running BaseX instance on localhost:1984.
They test actual database operations end-to-end.
"""

from __future__ import annotations

import pytest
import sys
from pathlib import Path

# Add parent directory to path to find BaseXClient
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.xml_entry_service import (
    XMLEntryService,
    XMLEntryServiceError,
    EntryNotFoundError,
    InvalidXMLError,
    LIFT_NS
)


# Test entry XML templates
TEST_ENTRY_TEMPLATE = f'''
<entry xmlns="{LIFT_NS}" id="{{entry_id}}" guid="{{entry_id}}_guid" dateCreated="2024-12-01T12:00:00Z">
    <lexical-unit>
        <form lang="en"><text>{{lexical_unit}}</text></form>
    </lexical-unit>
    <sense id="sense_001" order="0">
        <gloss lang="en"><text>{{gloss}}</text></gloss>
    </sense>
</entry>
'''.strip()


@pytest.fixture(scope="module")
def service():
    """Create XML Entry Service connected to real BaseX."""
    try:
        svc = XMLEntryService(
            host='localhost',
            port=1984,
            username='admin',
            password='admin',
            database='dictionary'
        )
        yield svc
    except Exception as e:
        pytest.skip(f"BaseX not available: {e}")


@pytest.fixture(scope="function", autouse=True)
def clean_test_entries(service):
    """Clean up test entries before and after each test."""
    test_id_patterns = [
        'integration_test_001',
        'integration_test_002',
        'integration_test_003',
        'integration_test_004',
        'integration_test_005',
        'integration_test_search_001',
        'integration_test_search_002',
        'integration_test_search_003',
        'integration_test_search_004',
        'integration_test_search_005',
        'integration_test_update',
    ]
    
    # Clean before test
    for entry_id in test_id_patterns:
        try:
            if service.entry_exists(entry_id):
                service.delete_entry(entry_id)
        except:
            pass
    
    yield
    
    # Clean after test
    for entry_id in test_id_patterns:
        try:
            if service.entry_exists(entry_id):
                service.delete_entry(entry_id)
        except:
            pass


class TestIntegrationCreateEntry:
    """Test entry creation with real database."""
    
    def test_create_and_verify_entry(self, service):
        """Test creating an entry and verifying it exists."""
        xml = TEST_ENTRY_TEMPLATE.format(
            entry_id='integration_test_001',
            lexical_unit='integrationword',
            gloss='a word for integration testing'
        )
        
        # Create entry
        result = service.create_entry(xml)
        
        assert result['id'] == 'integration_test_001'
        assert result['status'] == 'created'
        assert 'filename' in result
        
        # Verify it exists
        assert service.entry_exists('integration_test_001')
    
    def test_create_duplicate_entry_fails(self, service):
        """Test that creating duplicate entry fails."""
        xml = TEST_ENTRY_TEMPLATE.format(
            entry_id='integration_test_002',
            lexical_unit='duplicateword',
            gloss='a duplicate test'
        )
        
        # Create first time - should succeed
        service.create_entry(xml)
        
        # Try to create again - should fail
        with pytest.raises(XMLEntryServiceError, match="already exists"):
            service.create_entry(xml)
    
    def test_create_invalid_xml_fails(self, service):
        """Test that invalid XML is rejected."""
        invalid_xml = '<entry id="bad"><unclosed>'
        
        with pytest.raises(InvalidXMLError):
            service.create_entry(invalid_xml)


class TestIntegrationGetEntry:
    """Test entry retrieval with real database."""
    
    def test_get_existing_entry(self, service):
        """Test retrieving an existing entry."""
        # First create an entry
        xml = TEST_ENTRY_TEMPLATE.format(
            entry_id='integration_test_001',
            lexical_unit='getword',
            gloss='a word to retrieve'
        )
        service.create_entry(xml)
        
        # Now retrieve it
        entry = service.get_entry('integration_test_001')
        
        assert entry['id'] == 'integration_test_001'
        assert entry['guid'] == 'integration_test_001_guid'
        assert 'xml' in entry
        assert len(entry['lexical_units']) > 0
        assert entry['lexical_units'][0]['forms'][0]['text'] == 'getword'
        assert len(entry['senses']) > 0
        assert entry['senses'][0]['glosses'][0]['text'] == 'a word to retrieve'
    
    def test_get_nonexistent_entry_fails(self, service):
        """Test that retrieving non-existent entry fails."""
        with pytest.raises(EntryNotFoundError):
            service.get_entry('nonexistent_entry_xyz')


class TestIntegrationUpdateEntry:
    """Test entry updates with real database."""
    
    def test_update_existing_entry(self, service):
        """Test updating an existing entry."""
        # Create initial entry
        xml = TEST_ENTRY_TEMPLATE.format(
            entry_id='integration_test_update',
            lexical_unit='originalword',
            gloss='original meaning'
        )
        service.create_entry(xml)
        
        # Update it
        updated_xml = TEST_ENTRY_TEMPLATE.format(
            entry_id='integration_test_update',
            lexical_unit='updatedword',
            gloss='updated meaning'
        )
        result = service.update_entry('integration_test_update', updated_xml)
        
        assert result['id'] == 'integration_test_update'
        assert result['status'] == 'updated'
        
        # Verify update
        entry = service.get_entry('integration_test_update')
        assert entry['lexical_units'][0]['forms'][0]['text'] == 'updatedword'
        assert entry['senses'][0]['glosses'][0]['text'] == 'updated meaning'
    
    def test_update_nonexistent_entry_fails(self, service):
        """Test that updating non-existent entry fails."""
        xml = TEST_ENTRY_TEMPLATE.format(
            entry_id='nonexistent',
            lexical_unit='word',
            gloss='gloss'
        )
        
        with pytest.raises(EntryNotFoundError):
            service.update_entry('nonexistent', xml)
    
    def test_update_with_id_mismatch_fails(self, service):
        """Test that ID mismatch is detected."""
        # Create entry
        xml = TEST_ENTRY_TEMPLATE.format(
            entry_id='integration_test_001',
            lexical_unit='word',
            gloss='gloss'
        )
        service.create_entry(xml)
        
        # Try to update with different ID in XML
        wrong_xml = TEST_ENTRY_TEMPLATE.format(
            entry_id='different_id',
            lexical_unit='word',
            gloss='gloss'
        )
        
        with pytest.raises(InvalidXMLError, match="ID mismatch"):
            service.update_entry('integration_test_001', wrong_xml)


class TestIntegrationDeleteEntry:
    """Test entry deletion with real database."""
    
    def test_delete_existing_entry(self, service):
        """Test deleting an existing entry."""
        # Create entry
        xml = TEST_ENTRY_TEMPLATE.format(
            entry_id='integration_test_001',
            lexical_unit='deleteword',
            gloss='to be deleted'
        )
        service.create_entry(xml)
        
        # Verify it exists
        assert service.entry_exists('integration_test_001')
        
        # Delete it
        result = service.delete_entry('integration_test_001')
        
        assert result['id'] == 'integration_test_001'
        assert result['status'] == 'deleted'
        
        # Verify it's gone
        assert not service.entry_exists('integration_test_001')
    
    def test_delete_nonexistent_entry_fails(self, service):
        """Test that deleting non-existent entry fails."""
        with pytest.raises(EntryNotFoundError):
            service.delete_entry('nonexistent_entry_xyz')


class TestIntegrationSearch:
    """Test search functionality with real database."""
    
    def test_search_entries_by_text(self, service):
        """Test searching entries by lexical unit text."""
        # Create test entries
        for i in range(3):
            xml = TEST_ENTRY_TEMPLATE.format(
                entry_id=f'integration_test_search_00{i+1}',
                lexical_unit=f'searchword{i+1}',
                gloss=f'search test {i+1}'
            )
            service.create_entry(xml)
        
        # Search for entries
        results = service.search_entries(query_text='searchword', limit=10, offset=0)
        
        assert results['total'] >= 3
        assert results['count'] >= 3
        assert any(e['id'] == 'integration_test_search_001' for e in results['entries'])
        assert any(e['id'] == 'integration_test_search_002' for e in results['entries'])
        assert any(e['id'] == 'integration_test_search_003' for e in results['entries'])
    
    def test_search_with_pagination(self, service):
        """Test search pagination works correctly."""
        # Create test entries
        for i in range(5):
            xml = TEST_ENTRY_TEMPLATE.format(
                entry_id=f'integration_test_search_00{i+1}',
                lexical_unit=f'pageword{i+1}',
                gloss=f'page test {i+1}'
            )
            service.create_entry(xml)
        
        # Get first page
        page1 = service.search_entries(query_text='pageword', limit=2, offset=0)
        assert page1['limit'] == 2
        assert page1['offset'] == 0
        assert page1['count'] <= 2
        
        # Get second page
        page2 = service.search_entries(query_text='pageword', limit=2, offset=2)
        assert page2['limit'] == 2
        assert page2['offset'] == 2
        assert page2['count'] <= 2
        
        # Verify different results
        if page1['count'] > 0 and page2['count'] > 0:
            assert page1['entries'][0]['id'] != page2['entries'][0]['id']
    
    def test_search_no_results(self, service):
        """Test search with no matching results."""
        results = service.search_entries(query_text='nonexistent_xyz_abc', limit=50, offset=0)
        
        assert results['total'] == 0
        assert results['count'] == 0
        assert len(results['entries']) == 0


class TestIntegrationDatabaseStats:
    """Test database statistics with real database."""
    
    def test_get_database_stats(self, service):
        """Test retrieving database statistics."""
        # Get initial stats
        stats = service.get_database_stats()
        
        assert 'entries' in stats
        assert 'senses' in stats
        assert 'avg_senses' in stats
        assert stats['entries'] >= 0
        assert stats['senses'] >= 0
        assert stats['avg_senses'] >= 0
    
    def test_stats_reflect_changes(self, service):
        """Test that stats update when entries are added."""
        # Get initial count
        initial_stats = service.get_database_stats()
        initial_entries = initial_stats['entries']
        
        # Add an entry
        xml = TEST_ENTRY_TEMPLATE.format(
            entry_id='integration_test_001',
            lexical_unit='statsword',
            gloss='for stats test'
        )
        service.create_entry(xml)
        
        # Get updated stats
        new_stats = service.get_database_stats()
        
        # Should have one more entry
        assert new_stats['entries'] == initial_entries + 1


class TestIntegrationEndToEnd:
    """End-to-end integration tests."""
    
    def test_full_crud_lifecycle(self, service):
        """Test complete CRUD lifecycle for an entry."""
        entry_id = 'integration_test_001'
        
        # 1. CREATE
        create_xml = TEST_ENTRY_TEMPLATE.format(
            entry_id=entry_id,
            lexical_unit='lifecycleword',
            gloss='initial meaning'
        )
        create_result = service.create_entry(create_xml)
        assert create_result['status'] == 'created'
        
        # 2. READ
        entry = service.get_entry(entry_id)
        assert entry['id'] == entry_id
        assert entry['lexical_units'][0]['forms'][0]['text'] == 'lifecycleword'
        
        # 3. UPDATE
        update_xml = TEST_ENTRY_TEMPLATE.format(
            entry_id=entry_id,
            lexical_unit='updatedlifecycleword',
            gloss='updated meaning'
        )
        update_result = service.update_entry(entry_id, update_xml)
        assert update_result['status'] == 'updated'
        
        # Verify update
        entry = service.get_entry(entry_id)
        assert entry['lexical_units'][0]['forms'][0]['text'] == 'updatedlifecycleword'
        
        # 4. DELETE
        delete_result = service.delete_entry(entry_id)
        assert delete_result['status'] == 'deleted'
        
        # Verify deletion
        assert not service.entry_exists(entry_id)
        with pytest.raises(EntryNotFoundError):
            service.get_entry(entry_id)
    
    def test_multiple_concurrent_entries(self, service):
        """Test handling multiple entries at once."""
        # Create multiple entries
        entry_ids = [
            'integration_test_001',
            'integration_test_002',
            'integration_test_003'
        ]
        
        for i, entry_id in enumerate(entry_ids):
            xml = TEST_ENTRY_TEMPLATE.format(
                entry_id=entry_id,
                lexical_unit=f'concurrentword{i+1}',
                gloss=f'concurrent test {i+1}'
            )
            service.create_entry(xml)
        
        # Verify all exist
        for entry_id in entry_ids:
            assert service.entry_exists(entry_id)
        
        # Search should find all
        results = service.search_entries(query_text='concurrentword', limit=10, offset=0)
        assert results['total'] >= 3
        
        # Delete all
        for entry_id in entry_ids:
            service.delete_entry(entry_id)
        
        # Verify all gone
        for entry_id in entry_ids:
            assert not service.entry_exists(entry_id)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
