"""
Unit tests for entry display.

These tests verify that entries with language-specific lexical units are displayed correctly.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch
import pytest

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.entry import Entry
from app.parsers.lift_parser import LIFTParser

# Mark all tests in this module to skip ET mocking since they need real XML parsing
pytestmark = pytest.mark.skip_et_mock


class TestEntryDisplay(unittest.TestCase):
    """Test the display of entries with language-specific content."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = LIFTParser()
        
        # Sample LIFT XML for testing
        self.sample_lift = """<?xml version="1.0" encoding="UTF-8" ?>
<lift version="0.13">
    <entry id="test_entry_1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
            <form lang="pl"><text>test</text></form>
        </lexical-unit>
        <sense id="sense1">
            <grammatical-info value="Noun"/>
            <definition>
                <form lang="pl"><text>Test definition</text></form>
            </definition>
            <gloss lang="en">
                <text>Test gloss</text>
            </gloss>
        </sense>
    </entry>
    <entry id="test_entry_2">
        <lexical-unit>
            <form lang="pl"><text>polski</text></form>
        </lexical-unit>
        <sense id="sense1">
            <definition>
                <form lang="en"><text>Polish</text></form>
            </definition>
        </sense>
    </entry>
</lift>
"""

    def test_entry_with_multiple_languages(self):
        """Test that entries with multiple languages are handled correctly."""
        entries = self.parser.parse_string(self.sample_lift)
        self.assertEqual(len(entries), 2)
        
        # Check first entry with multiple languages
        entry1 = entries[0]
        self.assertEqual(entry1.id, "test_entry_1")
        
        # Check lexical_unit is a dictionary with language keys
        self.assertIsInstance(entry1.lexical_unit, dict)
        self.assertEqual(entry1.lexical_unit["en"], "test")
        self.assertEqual(entry1.lexical_unit["pl"], "test")
        
        # Check headword property returns English by default
        self.assertEqual(entry1.headword, "test")
        
        # Check language list
        self.assertEqual(set(entry1.get_language_list()), {"en", "pl"})
        
        # Check get_lexical_unit method
        self.assertEqual(entry1.get_lexical_unit("en"), "test")
        self.assertEqual(entry1.get_lexical_unit("pl"), "test")
        
        # Check second entry with only Polish
        entry2 = entries[1]
        self.assertEqual(entry2.id, "test_entry_2")
        
        # Check lexical_unit only has Polish
        self.assertIsInstance(entry2.lexical_unit, dict)
        self.assertEqual(entry2.lexical_unit["pl"], "polski")
        self.assertNotIn("en", entry2.lexical_unit)
        
        # Check headword falls back to Polish when English not available
        self.assertEqual(entry2.headword, "polski")
        
        # Check language list
        self.assertEqual(entry2.get_language_list(), ["pl"])
        
        # Check get_lexical_unit method falls back
        self.assertEqual(entry2.get_lexical_unit("en"), "")
        self.assertEqual(entry2.get_lexical_unit("pl"), "polski")
        self.assertEqual(entry2.get_lexical_unit(), "polski")

    def test_entry_to_dict(self):
        """Test that entry.to_dict() preserves the language structure."""
        entries = self.parser.parse_string(self.sample_lift)
        entry_dict = entries[0].to_dict()
        
        # Check that lexical_unit in the dictionary preserves language structure
        self.assertIsInstance(entry_dict["lexical_unit"], dict)
        self.assertEqual(entry_dict["lexical_unit"]["en"], "test")
        self.assertEqual(entry_dict["lexical_unit"]["pl"], "test")
        
        # Check that the dictionary has the new methods
        self.assertNotIn("headword", entry_dict)  # Should not be in dict as it's a property
        self.assertNotIn("get_lexical_unit", entry_dict)  # Should not be in dict as it's a method
        
        # Check that the dictionary has the expected structure for API
        self.assertIn("id", entry_dict)
        self.assertIn("senses", entry_dict)


class TestEntryTemplateDisplay(unittest.TestCase):
    """Test template rendering with Entry objects."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create sample entries
        self.entry_en_only = Entry(id_="entry1",
            lexical_unit={"en": "English Word"}
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        self.entry_multi_lang = Entry(id_="entry2",
            lexical_unit={
                "en": "English Word",
                "pl": "Polskie Słowo"
            }
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])
        
        self.entry_no_en = Entry(id_="entry3",
            lexical_unit={
                "pl": "Tylko Polski",
                "de": "Nur Deutsch"
            }
        ,
            senses=[{"id": "sense1", "definition": {"en": "test definition"}}])

    @patch('flask.render_template')
    def test_template_rendering(self, mock_render):
        """Test that templates receive the correct entry data."""
        # This is a simplified test for rendering since we can't easily test actual HTML output
        mock_render.return_value = "Rendered Template"
        
        # Check rendering with English-only entry
        self.assertEqual(self.entry_en_only.headword, "English Word")
        self.assertEqual(self.entry_en_only.get_language_list(), ["en"])
        
        # Check rendering with multi-language entry
        self.assertEqual(self.entry_multi_lang.headword, "English Word")
        self.assertEqual(set(self.entry_multi_lang.get_language_list()), {"en", "pl"})
        
        # Check rendering with no English entry
        # Should return the first language in the dictionary (may vary)
        self.assertTrue(self.entry_no_en.headword in ["Tylko Polski", "Nur Deutsch"])
        self.assertEqual(set(self.entry_no_en.get_language_list()), {"pl", "de"})


if __name__ == "__main__":
    unittest.main()
