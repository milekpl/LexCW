"""
Unit tests for custom possibility list (ReferenceAtomic/ReferenceCollection) support.

Tests Day 38-39 implementation:
- ReferenceAtomic: Single-selection custom fields referencing possibility lists
- ReferenceCollection: Multi-selection custom fields referencing possibility lists
- Integration with lift-ranges custom lists
"""

from __future__ import annotations
import pytest
from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example


class TestReferenceAtomicCustomFields:
    """Test single-selection custom fields (ReferenceAtomic)."""
    
    def test_entry_reference_atomic_single_value(self) -> None:
        """Test ReferenceAtomic custom field on entry with single value."""
        entry = Entry(
            id_="test-entry",
            lexical_unit={"en": "test"},
            traits={
                "CustomFldEntry-Status": "Pending"  # Single selection from status list
            }
        )
        
        assert entry.traits["CustomFldEntry-Status"] == "Pending"
    
    def test_sense_reference_atomic_domain(self) -> None:
        """Test ReferenceAtomic custom field on sense (semantic domain)."""
        sense = Sense(
            glosses={"en": "test"},
            traits={
                "CustomFldSense-Domain": "Nature.Plants"  # Single domain selection
            }
        )
        
        assert sense.traits["CustomFldSense-Domain"] == "Nature.Plants"
    
    def test_example_reference_atomic_source(self) -> None:
        """Test ReferenceAtomic custom field on example."""
        example = Example(
            content={"en": "test example"},
            traits={
                "CustomFldExample-Source": "Dictionary"  # Single source selection
            }
        )
        
        assert example.traits["CustomFldExample-Source"] == "Dictionary"
    
    def test_reference_atomic_with_hierarchy_path(self) -> None:
        """Test ReferenceAtomic with hierarchical value path."""
        entry = Entry(
            id_="test-entry",
            lexical_unit={"en": "test"},
            traits={
                "CustomFldEntry-Location": "World.Africa.Kenya"  # Hierarchical path
            }
        )
        
        assert entry.traits["CustomFldEntry-Location"] == "World.Africa.Kenya"


class TestReferenceCollectionCustomFields:
    """Test multi-selection custom fields (ReferenceCollection)."""
    
    def test_entry_reference_collection_multiple_values(self) -> None:
        """Test ReferenceCollection custom field with multiple values."""
        # Multiple values stored as comma-separated string in trait
        entry = Entry(
            id_="test-entry",
            lexical_unit={"en": "test"},
            traits={
                "CustomFldEntry-Tags": "noun,common,countable"  # Multiple selections
            }
        )
        
        assert entry.traits["CustomFldEntry-Tags"] == "noun,common,countable"
        # Split to verify multiple values
        values = entry.traits["CustomFldEntry-Tags"].split(",")
        assert len(values) == 3
        assert "noun" in values
        assert "common" in values
        assert "countable" in values
    
    def test_sense_reference_collection_domains(self) -> None:
        """Test ReferenceCollection for multiple semantic domains."""
        sense = Sense(
            glosses={"en": "bank"},
            traits={
                "CustomFldSense-Domains": "Finance.Banking,Nature.Water"  # Multiple domains
            }
        )
        
        domains = sense.traits["CustomFldSense-Domains"].split(",")
        assert len(domains) == 2
        assert "Finance.Banking" in domains
        assert "Nature.Water" in domains
    
    def test_reference_collection_empty(self) -> None:
        """Test ReferenceCollection with no selections."""
        entry = Entry(
            id_="test-entry",
            lexical_unit={"en": "test"},
            traits={}  # No selection
        )
        
        assert "CustomFldEntry-Tags" not in entry.traits
    
    def test_reference_collection_single_value(self) -> None:
        """Test ReferenceCollection with only one value selected."""
        entry = Entry(
            id_="test-entry",
            lexical_unit={"en": "test"},
            traits={
                "CustomFldEntry-Tags": "noun"  # Single value, no comma
            }
        )
        
        assert entry.traits["CustomFldEntry-Tags"] == "noun"


class TestMixedPossibilityListFields:
    """Test combinations of ReferenceAtomic and ReferenceCollection."""
    
    def test_entry_with_both_types(self) -> None:
        """Test entry with both ReferenceAtomic and ReferenceCollection."""
        entry = Entry(
            id_="test-entry",
            lexical_unit={"en": "test"},
            traits={
                "CustomFldEntry-Status": "Confirmed",  # ReferenceAtomic
                "CustomFldEntry-Tags": "noun,common",  # ReferenceCollection
                "CustomFldEntry-Location": "World.Europe.Poland"  # ReferenceAtomic with hierarchy
            }
        )
        
        assert entry.traits["CustomFldEntry-Status"] == "Confirmed"
        assert entry.traits["CustomFldEntry-Tags"] == "noun,common"
        assert entry.traits["CustomFldEntry-Location"] == "World.Europe.Poland"
    
    def test_sense_with_multiple_reference_fields(self) -> None:
        """Test sense with multiple custom possibility list references."""
        sense = Sense(
            glosses={"en": "test"},
            traits={
                "CustomFldSense-Domain": "Nature.Plants",
                "CustomFldSense-RegisterTags": "formal,technical",
                "morph-type": "stem"  # Standard trait mixed with custom
            }
        )
        
        assert sense.traits["CustomFldSense-Domain"] == "Nature.Plants"
        assert sense.traits["CustomFldSense-RegisterTags"] == "formal,technical"
        assert sense.traits["morph-type"] == "stem"
    
    def test_all_levels_with_possibility_lists(self) -> None:
        """Test possibility list references at entry, sense, and example levels."""
        entry = Entry(
            id_="test-entry",
            lexical_unit={"en": "test"},
            traits={
                "CustomFldEntry-Status": "Confirmed"
            }
        )
        
        sense = Sense(
            glosses={"en": "meaning"},
            traits={
                "CustomFldSense-Domain": "Nature.Animals"
            }
        )
        
        example = Example(
            content={"en": "example text"},
            traits={
                "CustomFldExample-Source": "Literature"
            }
        )
        
        entry.senses = [sense]
        sense.examples = [example]
        
        assert entry.traits["CustomFldEntry-Status"] == "Confirmed"
        assert entry.senses[0].traits["CustomFldSense-Domain"] == "Nature.Animals"
        assert entry.senses[0].examples[0].traits["CustomFldExample-Source"] == "Literature"
