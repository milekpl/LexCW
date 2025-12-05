"""
Unit tests for LIFT 0.13 Custom Field Types (Day 36-37).

Tests Integer, GenDate, and MultiUnicode custom field types per FieldWorks specification:
- Integer: Simple numeric values stored as traits
- GenDate: Generic dates with precision (YYYYMMDD format + precision indicator)
- MultiUnicode: Multi-writing system text stored as fields
"""

import pytest
from typing import Dict, Optional
from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example


class TestIntegerCustomFields:
    """Test Integer custom field type (trait-based)."""
    
    def test_entry_integer_custom_field(self) -> None:
        """Test integer custom field on entry via traits."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            senses=[Sense(id_="s1", glosses={"en": "test"})],
            traits={"CustomFldEntry-Number": "42"}
        )
        
        assert "CustomFldEntry-Number" in entry.traits
        assert entry.traits["CustomFldEntry-Number"] == "42"
        # Verify it's stored as string (traits are string key-value pairs)
        assert isinstance(entry.traits["CustomFldEntry-Number"], str)
    
    def test_sense_integer_custom_field(self) -> None:
        """Test integer custom field on sense via traits."""
        sense = Sense(
            id_="s1",
            glosses={"en": "test"},
            traits={"CustomFldSense-Count": "100"}
        )
        
        assert "CustomFldSense-Count" in sense.traits
        assert sense.traits["CustomFldSense-Count"] == "100"
    
    def test_example_integer_custom_field(self) -> None:
        """Test integer custom field on example via traits."""
        example = Example(
            content={"en": "test example"},
            traits={"CustomFldExample-Rating": "5"}
        )
        
        assert "CustomFldExample-Rating" in example.traits
        assert example.traits["CustomFldExample-Rating"] == "5"
    
    def test_multiple_integer_custom_fields(self) -> None:
        """Test multiple integer custom fields on single entry."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            senses=[Sense(id_="s1", glosses={"en": "test"})],
            traits={
                "CustomFldEntry-Number1": "10",
                "CustomFldEntry-Number2": "20",
                "morph-type": "stem"  # Mixed with other traits
            }
        )
        
        assert entry.traits["CustomFldEntry-Number1"] == "10"
        assert entry.traits["CustomFldEntry-Number2"] == "20"
        assert entry.traits["morph-type"] == "stem"


class TestGenDateCustomFields:
    """Test GenDate (generic date) custom field type (trait-based)."""
    
    def test_entry_gendate_basic(self) -> None:
        """Test basic GenDate custom field."""
        # Format: YYYYMMDD + precision (0=exact, 1=approx, 2=before, 3=after)
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            senses=[Sense(id_="s1", glosses={"en": "test"})],
            traits={"CustomFldEntry-Date": "201105230"}  # May 23, 2011, exact
        )
        
        assert entry.traits["CustomFldEntry-Date"] == "201105230"
    
    def test_gendate_approximate(self) -> None:
        """Test GenDate with approximate precision."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            senses=[Sense(id_="s1", glosses={"en": "test"})],
            traits={"CustomFldEntry-Date": "201105231"}  # May 23, 2011, approximate
        )
        
        assert entry.traits["CustomFldEntry-Date"] == "201105231"
    
    def test_gendate_before(self) -> None:
        """Test GenDate with 'before' precision."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            senses=[Sense(id_="s1", glosses={"en": "test"})],
            traits={"CustomFldEntry-Date": "201105232"}  # Before May 23, 2011
        )
        
        assert entry.traits["CustomFldEntry-Date"] == "201105232"
    
    def test_gendate_after(self) -> None:
        """Test GenDate with 'after' precision."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            senses=[Sense(id_="s1", glosses={"en": "test"})],
            traits={"CustomFldEntry-Date": "201105233"}  # After May 23, 2011
        )
        
        assert entry.traits["CustomFldEntry-Date"] == "201105233"
    
    def test_sense_gendate(self) -> None:
        """Test GenDate on sense level."""
        sense = Sense(
            id_="s1",
            glosses={"en": "test"},
            traits={"CustomFldSense-FirstRecorded": "19500101"}  # Jan 1, 1950
        )
        
        assert sense.traits["CustomFldSense-FirstRecorded"] == "19500101"


class TestMultiUnicodeCustomFields:
    """Test MultiUnicode custom field type (field-based, multitext)."""
    
    def test_entry_multiUnicode_single_language(self) -> None:
        """Test MultiUnicode custom field with single language."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            senses=[Sense(id_="s1", glosses={"en": "test"})],
            custom_fields={"CustomFldEntry-MultiText": {"en": "English text"}}
        )
        
        assert "CustomFldEntry-MultiText" in entry.custom_fields
        assert entry.custom_fields["CustomFldEntry-MultiText"]["en"] == "English text"
    
    def test_entry_multiUnicode_multiple_languages(self) -> None:
        """Test MultiUnicode custom field with multiple writing systems."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            senses=[Sense(id_="s1", glosses={"en": "test"})],
            custom_fields={
                "CustomFldEntry-Description": {
                    "en": "English description",
                    "fr": "Description française",
                    "pl": "Polski opis"
                }
            }
        )
        
        field = entry.custom_fields["CustomFldEntry-Description"]
        assert field["en"] == "English description"
        assert field["fr"] == "Description française"
        assert field["pl"] == "Polski opis"
    
    def test_sense_multiUnicode(self) -> None:
        """Test MultiUnicode custom field on sense."""
        sense = Sense(
            id_="s1",
            glosses={"en": "test"},
            custom_fields={"CustomFldSense-Notes": {"en": "Note", "es": "Nota"}}
        )
        
        assert sense.custom_fields["CustomFldSense-Notes"]["en"] == "Note"
        assert sense.custom_fields["CustomFldSense-Notes"]["es"] == "Nota"
    
    def test_multiple_multiUnicode_fields(self) -> None:
        """Test multiple MultiUnicode custom fields."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            senses=[Sense(id_="s1", glosses={"en": "test"})],
            custom_fields={
                "CustomFldEntry-Field1": {"en": "Value 1"},
                "CustomFldEntry-Field2": {"en": "Value 2", "fr": "Valeur 2"}
            }
        )
        
        assert "CustomFldEntry-Field1" in entry.custom_fields
        assert "CustomFldEntry-Field2" in entry.custom_fields
        assert entry.custom_fields["CustomFldEntry-Field1"]["en"] == "Value 1"
        assert entry.custom_fields["CustomFldEntry-Field2"]["fr"] == "Valeur 2"


class TestMixedCustomFieldTypes:
    """Test combinations of different custom field types."""
    
    def test_entry_with_all_three_types(self) -> None:
        """Test entry with Integer, GenDate, and MultiUnicode custom fields."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            senses=[Sense(id_="s1", glosses={"en": "test"})],
            traits={
                "CustomFldEntry-Number": "42",  # Integer
                "CustomFldEntry-Date": "201105230",  # GenDate
                "morph-type": "stem"  # Standard trait
            },
            custom_fields={
                "CustomFldEntry-Description": {"en": "Description"}  # MultiUnicode
            }
        )
        
        # Verify Integer
        assert entry.traits["CustomFldEntry-Number"] == "42"
        
        # Verify GenDate
        assert entry.traits["CustomFldEntry-Date"] == "201105230"
        
        # Verify MultiUnicode
        assert entry.custom_fields["CustomFldEntry-Description"]["en"] == "Description"
        
        # Verify standard trait still works
        assert entry.traits["morph-type"] == "stem"
