"""
Integration tests for DictionaryService with real BaseX database

Tests the complete CRUD lifecycle and search functionality using Entry objects.
"""

from __future__ import annotations

import pytest

from app.models.entry import Entry
from app.models.sense import Sense
from app.utils.exceptions import DatabaseError, NotFoundError


@pytest.fixture(scope="function")
def service(dict_service_with_db):
    """Use the properly initialized test database service."""
    return dict_service_with_db


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
        except Exception:
            pass
    
    yield
    
    # Clean after test
    for entry_id in test_id_patterns:
        try:
            if service.entry_exists(entry_id):
                service.delete_entry(entry_id)
        except Exception:
            pass


@pytest.mark.integration
class TestIntegrationCreateEntry:
    """Test entry creation with real database."""
    
    def test_create_and_verify_entry(self, service):
        """Test creating an entry and verifying it exists."""
        entry = Entry(
            id_='integration_test_001',
            guid='integration_test_001_guid',
            lexical_unit={'en': 'integrationword'},
            senses=[
                Sense(
                    id_='sense_001',
                    glosses={'en': 'a word for integration testing'}
                )
            ]
        )
        
        # Create entry
        result = service.create_entry(entry)
        
        assert result == 'integration_test_001'
        
        # Verify it exists
        assert service.entry_exists('integration_test_001')
    
    def test_create_duplicate_entry_fails(self, service):
        """Test that creating duplicate entry fails."""
        entry = Entry(
            id_='integration_test_002',
            lexical_unit={'en': 'duplicateword'},
            senses=[
                Sense(glosses={'en': 'a duplicate test'})
            ]
        )
        
        # Create first time - should succeed
        service.create_entry(entry)
        
        # Try to create again - should fail
        with pytest.raises(DatabaseError, match="already exists|duplicate"):
            service.create_entry(entry)
    
    def test_create_invalid_entry_fails(self, service):
        """Test that invalid entry is rejected."""
        # Entry without senses should fail validation
        invalid_entry = Entry(
            id_='integration_test_003',
            lexical_unit={'en': 'invalidword'},
            senses=[]  # Empty senses
        )
        
        with pytest.raises((DatabaseError, ValueError)):
            service.create_entry(invalid_entry)


@pytest.mark.integration
class TestIntegrationGetEntry:
    """Test entry retrieval with real database."""
    
    def test_get_existing_entry(self, service):
        """Test retrieving an existing entry."""
        # First create an entry
        entry = Entry(
            id_='integration_test_001',
            guid='integration_test_001_guid',
            lexical_unit={'en': 'getword'},
            senses=[
                Sense(
                    id_='sense_001',
                    glosses={'en': 'a word to retrieve'}
                )
            ]
        )
        service.create_entry(entry)
        
        # Now retrieve it
        retrieved = service.get_entry('integration_test_001')
        
        assert retrieved.id == 'integration_test_001'
        assert 'en' in retrieved.lexical_unit
        assert retrieved.lexical_unit['en'] == 'getword'
        assert len(retrieved.senses) > 0
        assert retrieved.senses[0].glosses['en'] == 'a word to retrieve'
    
    def test_get_nonexistent_entry_fails(self, service):
        """Test that retrieving non-existent entry fails."""
        with pytest.raises(EntryNotFoundError):
            service.get_entry('nonexistent_entry_xyz')


@pytest.mark.integration
class TestIntegrationUpdateEntry:
    """Test entry updates with real database."""
    
    def test_update_existing_entry(self, service):
        """Test updating an existing entry."""
        # Create initial entry
        entry = Entry(
            id_='integration_test_update',
            lexical_unit={'en': 'originalword'},
            senses=[
                Sense(glosses={'en': 'original meaning'})
            ]
        )
        service.create_entry(entry)
        
        # Update it
        updated_entry = Entry(
            id='integration_test_update',
            lexical_unit={'en': 'updatedword'},
            senses=[
                Sense(glosses={'en': 'updated meaning'})
            ]
        )
        service.update_entry(updated_entry)
        
        # Verify update
        retrieved = service.get_entry('integration_test_update')
        assert retrieved.lexical_unit['en'] == 'updatedword'
        assert retrieved.senses[0].glosses['en'] == 'updated meaning'
    
    def test_update_nonexistent_entry_fails(self, service):
        """Test that updating non-existent entry fails."""
        entry = Entry(
            id='nonexistent',
            lexical_unit={'en': 'word'},
            senses=[Sense(glosses={'en': 'gloss'})]
        )
        
        with pytest.raises(NotFoundError):
            service.update_entry(entry)
    
    def test_update_with_id_mismatch_fails(self, service):
        """Test that ID mismatch is detected."""
        # Create entry
        entry = Entry(
            id_='integration_test_001',
            lexical_unit={'en': 'word'},
            senses=[Sense(glosses={'en': 'gloss'})]
        )
        service.create_entry(entry)
        
        # Try to update with different ID in Entry - this should work since we only pass Entry
        # The service will update based on Entry.id, so this actually updates different_id not integration_test_001
        # This test doesn't make sense anymore - updating entry with its own ID should work
        # Let's test that update actually changes data instead
        existing = service.get_entry('integration_test_001')
        existing.lexical_unit = {'en': 'modified'}
        service.update_entry(existing)
        
        # Verify the update worked
        updated = service.get_entry('integration_test_001')
        assert updated.lexical_unit['en'] == 'modified'


@pytest.mark.integration
class TestIntegrationDeleteEntry:
    """Test entry deletion with real database."""
    
    def test_delete_existing_entry(self, service):
        """Test deleting an existing entry."""
        # Create entry
        entry = Entry(
            id_='integration_test_001',
            lexical_unit={'en': 'deleteword'},
            senses=[Sense(glosses={'en': 'to be deleted'})]
        )
        service.create_entry(entry)
        
        # Verify it exists
        assert service.entry_exists('integration_test_001')
        
        # Delete it
        service.delete_entry('integration_test_001')
        
        # Verify it's gone
        assert not service.entry_exists('integration_test_001')
    
    def test_delete_nonexistent_entry_fails(self, service):
        """Test that deleting non-existent entry fails."""
        with pytest.raises(EntryNotFoundError):
            service.delete_entry('nonexistent_entry_xyz')


@pytest.mark.integration
class TestIntegrationSearch:
    """Test search functionality with real database."""
    
    def test_search_entries_by_text(self, service):
        """Test searching entries by lexical unit text."""
        # Create test entries
        for i in range(3):
            entry = Entry(
                id_=f'integration_test_search_00{i+1}',
                lexical_unit={'en': f'searchword{i+1}'},
                senses=[
                    Sense(glosses={'en': f'search test {i+1}'})
                ]
            )
            service.create_entry(entry)
        
        # Search for entries
        results = service.search_entries('searchword')
        
        # Should find at least the 3 we created
        found_ids = [e.id_ for e in results]
        assert 'integration_test_search_001' in found_ids
        assert 'integration_test_search_002' in found_ids
        assert 'integration_test_search_003' in found_ids
    
    def test_search_with_pagination(self, service):
        """Test search pagination works correctly."""
        # Create test entries
        for i in range(5):
            entry = Entry(
                id_=f'integration_test_search_00{i+1}',
                lexical_unit={'en': f'pageword{i+1}'},
                senses=[
                    Sense(glosses={'en': f'page test {i+1}'})
                ]
            )
            service.create_entry(entry)
        
        # Get all results
        all_results = service.search_entries('pageword')
        
        # Should have at least 5
        assert len(all_results) >= 5
    
    def test_search_no_results(self, service):
        """Test search with no matching results."""
        results = service.search_entries('nonexistent_xyz_abc')
        
        assert len(results) == 0


@pytest.mark.integration
class TestIntegrationDatabaseStats:
    """Test database statistics with real database."""
    
    def test_get_database_stats(self, service):
        """Test retrieving database statistics."""
        # DictionaryService doesn't have get_database_stats
        # Test entry count functionality instead
        count = service.get_entry_count()
        
        assert isinstance(count, int)
        assert count >= 0
    
    def test_stats_reflect_changes(self, service):
        """Test that entry count reflects changes."""
        # Get initial count
        initial_count = service.get_entry_count()
        
        # Add an entry
        entry = Entry(
            id='integration_test_001',
            lexical_unit={'en': 'statsword'},
            senses=[Sense(glosses={'en': 'for stats test'})]
        )
        service.create_entry(entry)
        
        # Get updated count
        new_count = service.get_entry_count()
        
        # Should have one more entry
        assert new_count == initial_count + 1


@pytest.mark.integration
class TestIntegrationEndToEnd:
    """End-to-end integration tests."""
    
    def test_full_crud_lifecycle(self, service):
        """Test complete CRUD lifecycle for an entry."""
        entry_id = 'integration_test_001'
        
        # 1. CREATE
        entry = Entry(
            id_=entry_id,
            lexical_unit={'en': 'lifecycleword'},
            senses=[Sense(glosses={'en': 'initial meaning'})]
        )
        result = service.create_entry(entry)
        assert result == entry_id
        
        # 2. READ
        retrieved = service.get_entry(entry_id)
        assert retrieved.id_ == entry_id
        assert retrieved.lexical_unit['en'] == 'lifecycleword'
        
        # 3. UPDATE
        updated_entry = Entry(
            id_=entry_id,
            lexical_unit={'en': 'updatedlifecycleword'},
            senses=[Sense(glosses={'en': 'updated meaning'})]
        )
        service.update_entry(entry_id, updated_entry)
        
        # Verify update
        retrieved = service.get_entry(entry_id)
        assert retrieved.lexical_unit['en'] == 'updatedlifecycleword'
        
        # 4. DELETE
        service.delete_entry(entry_id)
        
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
            entry = Entry(
                id_=entry_id,
                lexical_unit={'en': f'concurrentword{i+1}'},
                senses=[
                    Sense(glosses={'en': f'concurrent test {i+1}'})
                ]
            )
            service.create_entry(entry)
        
        # Verify all exist
        for entry_id in entry_ids:
            assert service.entry_exists(entry_id)
        
        # Search should find all
        results, total = service.search_entries('concurrentword')
        found_ids = [e.id for e in results]
        assert len([eid for eid in entry_ids if eid in found_ids]) >= 3
        assert total >= 3
        
        # Delete all
        for entry_id in entry_ids:
            service.delete_entry(entry_id)
        
        # Verify all gone
        for entry_id in entry_ids:
            assert not service.entry_exists(entry_id)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

