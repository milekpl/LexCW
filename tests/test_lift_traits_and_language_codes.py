"""
Test for extracting variant types from LIFT trait elements and language codes.

This module tests the extraction of variant types from LIFT trait elements
and the extraction of language codes from LIFT files, ensuring that the UI
can properly display project-specific information.
"""

from __future__ import annotations

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
import xml.etree.ElementTree as ET

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.parsers.lift_parser import LIFTParser
from app.services.dictionary_service import DictionaryService


class TestLIFTTraitsAndLanguageCodes:
    """
    Test variant types from traits and language codes from LIFT files.
    """

    @pytest.fixture
    def sample_lift_with_traits(self) -> str:
        """Sample LIFT XML with variant traits and at least one sense per entry."""
        return """<?xml version="1.0" encoding="UTF-8" ?>
        <lift producer="SIL.FLEx 9.1.25.877" version="0.13">
        <entry id="test1">
            <lexical-unit>
                <form lang="en"><text>test</text></form>
            </lexical-unit>
            <variant type="dialectal">
                <form lang="en"><text>test variant</text></form>
                <trait name="type" value="dialectal"/>
            </variant>
            <pronunciation>
                <form lang="seh-fonipa"><text>test</text></form>
            </pronunciation>
            <note>
                <form lang="pl"><text>Test note with language</text></form>
            </note>
            <sense id="s1">
                <definition><form lang="en"><text>dummy</text></form></definition>
            </sense>
        </entry>
        <entry id="test2">
            <lexical-unit>
                <form lang="pl"><text>test2</text></form>
            </lexical-unit>
            <variant type="spelling">
                <form lang="en-GB"><text>test2 variant</text></form>
                <trait name="type" value="spelling"/>
            </variant>
            <pronunciation>
                <form lang="seh-fonipa"><text>test2</text></form>
            </pronunciation>
            <sense id="s2">
                <definition><form lang="pl"><text>dummy2</text></form></definition>
            </sense>
        </entry>
        </lift>
        """

    def test_extract_variant_types_from_traits(self, sample_lift_with_traits: str) -> None:
        """Test extracting variant types from trait elements."""
        parser = LIFTParser()
        
        # Extract variant types
        variant_types = parser.extract_variant_types_from_traits(sample_lift_with_traits)
        
        # Check that we have the expected types
        assert len(variant_types) == 2
        
        # Verify that the dialectal type is included
        dialectal_type = next((t for t in variant_types if t["id"] == "dialectal"), None)
        assert dialectal_type is not None
        assert dialectal_type["value"] == "dialectal"
        assert dialectal_type["abbrev"] == "dia"  # First 3 chars as abbreviation
        
        # Verify that the spelling type is included
        spelling_type = next((t for t in variant_types if t["id"] == "spelling"), None)
        assert spelling_type is not None
        assert spelling_type["value"] == "spelling"
        assert spelling_type["abbrev"] == "spe"  # First 3 chars as abbreviation

    def test_extract_language_codes(self, sample_lift_with_traits: str) -> None:
        """Test extracting language codes from LIFT data."""
        parser = LIFTParser()
        
        # Extract language codes
        lang_codes = parser.extract_language_codes_from_file(sample_lift_with_traits)
        
        # Check that we have the expected codes
        assert len(lang_codes) == 4
        assert "en" in lang_codes
        assert "en-GB" in lang_codes
        assert "pl" in lang_codes
        assert "seh-fonipa" in lang_codes  # Should be added automatically

    def test_dictionary_service_variant_types(self, sample_lift_with_traits: str) -> None:
        """Test variant types extraction through dictionary service."""
        # Mock DB connector
        mock_connector = MagicMock()
        mock_connector.execute_query.return_value = sample_lift_with_traits
        
        # Create service with mocked DB
        service = DictionaryService(mock_connector)
        
        # Test variant types extraction
        with patch.object(service.lift_parser, 'extract_variant_types_from_traits') as mock_extract:
            mock_extract.return_value = [
                {"id": "dialectal", "value": "dialectal", "abbrev": "dia", "description": {"en": "Dialectal variant"}},
                {"id": "spelling", "value": "spelling", "abbrev": "spe", "description": {"en": "Spelling variant"}}
            ]
            
            variant_types = service.get_variant_types_from_traits()
            
            # Verify mock was called
            mock_extract.assert_called_once()
            
            # Check results
            assert len(variant_types) == 2
            assert variant_types[0]["id"] == "dialectal"
            assert variant_types[1]["id"] == "spelling"

    def test_note_extraction_with_lang_forms(self, sample_lift_with_traits: str) -> None:
        """Test extraction of notes with language forms."""
        parser = LIFTParser()
        
        # Parse the LIFT XML
        entries = parser.parse_string(sample_lift_with_traits)
        
        # Check if we have at least one entry
        assert len(entries) > 0
        
        # Check if the first entry has notes
        assert hasattr(entries[0], 'notes')
        
        # Check if the note has the expected structure
        assert 'general' in entries[0].notes
        
        # In the new structure, the note should be a dict mapping languages to text
        assert isinstance(entries[0].notes['general'], dict)
        assert 'pl' in entries[0].notes['general']
        assert entries[0].notes['general']['pl']['text'] == 'Test note with language'

    def test_fixed_pronunciation_language(self, sample_lift_with_traits: str) -> None:
        """Test that pronunciations always use seh-fonipa language code."""
        parser = LIFTParser()
        
        # Parse the LIFT XML
        entries = parser.parse_string(sample_lift_with_traits)
        
        # Check pronunciations in all entries
        for entry in entries:
            if hasattr(entry, 'pronunciations') and entry.pronunciations:
                # In our model, pronunciations are stored as a dictionary mapping language codes to strings
                for lang_code, pronunciation_text in entry.pronunciations.items():
                    # Check that the language is always seh-fonipa
                    assert lang_code == 'seh-fonipa', f"Expected seh-fonipa, got {lang_code}"
                    assert isinstance(pronunciation_text, str), f"Pronunciation text should be string: {pronunciation_text}"
