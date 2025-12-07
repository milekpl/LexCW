"""
Unit tests for Entry order and optional date attributes (Day 43-44).

Tests the LIFT 0.13 optional attributes:
- order: Manual entry ordering
- dateDeleted: Soft delete support
- dateCreated/dateModified: Already implemented, verifying preservation
"""

import pytest
from datetime import datetime
from app.models.entry import Entry


class TestEntryOrderAttribute:
    """Test order attribute for manual entry ordering."""
    
    def test_entry_with_order(self):
        """Entry can have an order attribute."""
        entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'},
            order=5
        )
        assert entry.order == 5
    
    def test_entry_without_order_defaults_to_none(self):
        """Entry without order defaults to None."""
        entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'}
        )
        assert entry.order is None
    
    def test_order_to_dict(self):
        """Order attribute is included in to_dict()."""
        entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'},
            order=10
        )
        entry_dict = entry.to_dict()
        assert entry_dict['order'] == 10
    
    def test_order_none_in_dict(self):
        """Order=None is included in dict."""
        entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'},
            order=None
        )
        entry_dict = entry.to_dict()
        assert 'order' in entry_dict
        assert entry_dict['order'] is None


class TestEntryDateDeletedAttribute:
    """Test dateDeleted attribute for soft deletes."""
    
    def test_entry_with_date_deleted(self):
        """Entry can have a dateDeleted attribute."""
        entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'},
            date_deleted='2025-12-05T10:30:00Z'
        )
        assert entry.date_deleted == '2025-12-05T10:30:00Z'
    
    def test_entry_without_date_deleted_defaults_to_none(self):
        """Entry without dateDeleted defaults to None."""
        entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'}
        )
        assert entry.date_deleted is None
    
    def test_date_deleted_to_dict(self):
        """dateDeleted attribute is included in to_dict()."""
        entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'},
            date_deleted='2025-12-05T10:30:00Z'
        )
        entry_dict = entry.to_dict()
        assert entry_dict['date_deleted'] == '2025-12-05T10:30:00Z'


class TestExistingDateAttributes:
    """Verify existing date attributes still work correctly."""
    
    def test_date_created_preserved(self):
        """dateCreated attribute works correctly."""
        entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'},
            date_created='2025-01-15T10:30:00Z'
        )
        assert entry.date_created == '2025-01-15T10:30:00Z'
        assert entry.to_dict()['date_created'] == '2025-01-15T10:30:00Z'
    
    def test_date_modified_preserved(self):
        """dateModified attribute works correctly."""
        entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'},
            date_modified='2025-02-20T14:45:00Z'
        )
        assert entry.date_modified == '2025-02-20T14:45:00Z'
        assert entry.to_dict()['date_modified'] == '2025-02-20T14:45:00Z'
    
    def test_all_date_attributes_together(self):
        """All date attributes can coexist."""
        entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'},
            date_created='2025-01-15T10:30:00Z',
            date_modified='2025-02-20T14:45:00Z',
            date_deleted='2025-03-01T09:00:00Z'
        )
        entry_dict = entry.to_dict()
        assert entry_dict['date_created'] == '2025-01-15T10:30:00Z'
        assert entry_dict['date_modified'] == '2025-02-20T14:45:00Z'
        assert entry_dict['date_deleted'] == '2025-03-01T09:00:00Z'


class TestOrderAndDatesCombined:
    """Test order and date attributes working together."""
    
    def test_entry_with_all_optional_attributes(self):
        """Entry can have order and all date attributes."""
        entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'},
            order=5,
            date_created='2025-01-15T10:30:00Z',
            date_modified='2025-02-20T14:45:00Z',
            date_deleted='2025-03-01T09:00:00Z'
        )
        
        assert entry.order == 5
        assert entry.date_created == '2025-01-15T10:30:00Z'
        assert entry.date_modified == '2025-02-20T14:45:00Z'
        assert entry.date_deleted == '2025-03-01T09:00:00Z'
        
        entry_dict = entry.to_dict()
        assert entry_dict['order'] == 5
        assert entry_dict['date_created'] == '2025-01-15T10:30:00Z'
        assert entry_dict['date_modified'] == '2025-02-20T14:45:00Z'
        assert entry_dict['date_deleted'] == '2025-03-01T09:00:00Z'
