"""
Unit tests for the LIFT parser.
"""

import os
import pytest
from unittest.mock import patch, mock_open
import xml.etree.ElementTree as ET

from app.parsers.lift_parser import LIFTParser, LIFTRangesParser
from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example
from app.utils.exceptions import ValidationError


class TestLIFTParser:
    """Tests for the LIFT parser."""
    
    def setup_method(self):
        """Set up the test environment."""
        self.parser = LIFTParser()
        
        # Sample LIFT XML for testing
        self.sample_lift_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="test_entry_1">
                <lexical-unit>
                    <form lang="en">
                        <text>test</text>
                    </form>
                </lexical-unit>
                <sense id="sense1">
                    <gloss lang="pl">
                        <text>testować</text>
                    </gloss>
                    <definition>
                        <form lang="en">
                            <text>to try something</text>
                        </form>
                    </definition>
                    <example id="example1">
                        <form lang="en">
                            <text>This is a test.</text>
                        </form>
                        <translation>
                            <form lang="pl">
                                <text>To jest test.</text>
                            </form>
                        </translation>
                    </example>
                </sense>
                <pronunciation writing-system="seh-fonipa" value="test" />
            </entry>
        </lift>
        '''
    
    def test_parse_string(self):
        """Test parsing a LIFT XML string."""
        entries = self.parser.parse_string(self.sample_lift_xml)
        
        assert len(entries) == 1
        assert entries[0].id == "test_entry_1"
        assert entries[0].lexical_unit["en"] == "test"
        assert len(entries[0].senses) == 1
        assert entries[0].senses[0]["glosses"]["pl"] == "testować"
        assert entries[0].senses[0]["definitions"]["en"] == "to try something"
        assert entries[0].pronunciations["seh-fonipa"] == "test"
    
    def test_parse_file(self):
        """Test parsing a LIFT file."""
        with patch("os.path.exists", return_value=True), \
             patch("xml.etree.ElementTree.parse") as mock_parse:
            
            # Set up the mock
            mock_root = ET.fromstring(self.sample_lift_xml)
            mock_parse.return_value.getroot.return_value = mock_root
            
            # Call the method with a dummy file path
            entries = self.parser.parse_file("dummy.lift")
            
            # Assertions
            assert len(entries) == 1
            assert entries[0].id == "test_entry_1"
            assert entries[0].lexical_unit["en"] == "test"
    
    def test_file_not_found(self):
        """Test handling of non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.parser.parse_file("nonexistent.lift")
    
    def test_validation_enabled(self):
        """Test that validation is performed when enabled."""
        # Create a parser with validation enabled
        parser = LIFTParser(validate=True)
        
        # Create an invalid XML (missing required fields)
        invalid_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="invalid_entry">
                <!-- Missing lexical-unit -->
            </entry>
        </lift>
        '''
        
        # Mock the Entry.validate method to raise a ValidationError
        with patch("app.models.entry.Entry.validate", side_effect=ValidationError("Invalid entry")):
            with pytest.raises(ValidationError):
                parser.parse_string(invalid_xml)
    
    def test_validation_disabled(self):
        """Test that validation is skipped when disabled."""
        # Create a parser with validation disabled
        parser = LIFTParser(validate=False)
        
        # Create an invalid XML (missing required fields)
        invalid_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="invalid_entry">
                <!-- Missing lexical-unit -->
            </entry>
        </lift>
        '''
        
        # Mock the Entry.validate method to raise a ValidationError
        with patch("app.models.entry.Entry.validate", side_effect=ValidationError("Invalid entry")):
            # Should not raise an exception
            entries = parser.parse_string(invalid_xml)
            assert len(entries) == 1
            assert entries[0].id == "invalid_entry"
    
    def test_generate_lift_string(self):
        """Test generating a LIFT XML string from Entry objects."""
        # Create an Entry object
        entry = Entry(
            id_="test_entry_2",
            lexical_unit={"en": "example"},
            pronunciations={"seh-fonipa": "ɪɡˈzæmpəl"}
        )
        
        # Add a sense
        sense = Sense(
            id_="sense1",
            glosses={"pl": "przykład"},
            definitions={"en": "a thing characteristic of its kind"}
        )
        
        # Add an example to the sense
        example = Example(
            id_="example1",
            forms={"en": "This is an example."},
            translations={"pl": "To jest przykład."}
        )
        
        sense.examples.append(example.to_dict())
        entry.senses.append(sense.to_dict())
          # Generate LIFT XML
        xml_string = self.parser.generate_lift_string([entry])
        
        # Debug: print the generated XML
        print(f"Generated XML: {xml_string}")
          # Parse the generated XML to verify it
        root = ET.fromstring(xml_string)
        
        # Define namespaces for searching
        namespaces = {'lift': 'http://fieldworks.sil.org/schemas/lift/0.13'}
        
        # Verify entry
        entry_elem = root.find(".//lift:entry", namespaces)
        assert entry_elem is not None
        assert entry_elem.get("id") == "test_entry_2"
        
        # Verify lexical unit
        lex_unit = entry_elem.find(".//lift:lexical-unit/lift:form[@lang='en']/lift:text", namespaces)
        assert lex_unit is not None
        assert lex_unit.text == "example"
          # Verify pronunciation  
        pron = entry_elem.find(".//lift:pronunciation[@writing-system='seh-fonipa']", namespaces)
        assert pron is not None
        assert pron.get("value") == "ɪɡˈzæmpəl"
        
        # Verify sense
        sense_elem = entry_elem.find(".//lift:sense", namespaces)
        assert sense_elem is not None
        assert sense_elem.get("id") == "sense1"
        
        # Verify gloss
        gloss_elem = sense_elem.find(".//lift:gloss[@lang='pl']/lift:text", namespaces)
        assert sense_elem.get("id") == "sense1"
        
        # Verify gloss
        gloss = sense_elem.find(".//gloss[@lang='pl']/text")
        assert gloss is not None
        assert gloss.text == "przykład"
        
        # Verify definition
        definition = sense_elem.find(".//definition/form[@lang='en']/text")
        assert definition is not None
        assert definition.text == "a thing characteristic of its kind"
        
        # Verify example
        example_elem = sense_elem.find(".//example")
        assert example_elem is not None
        assert example_elem.get("id") == "example1"
        
        # Verify example form
        example_form = example_elem.find(".//form[@lang='en']/text")
        assert example_form is not None
        assert example_form.text == "This is an example."
        
        # Verify example translation
        example_trans = example_elem.find(".//translation/form[@lang='pl']/text")
        assert example_trans is not None
        assert example_trans.text == "To jest przykład."


class TestLIFTRangesParser:
    """Tests for the LIFT ranges parser."""
    
    def setup_method(self):
        """Set up the test environment."""
        self.parser = LIFTRangesParser()
        
        # Sample LIFT ranges XML for testing
        self.sample_ranges_xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift-ranges>
            <range id="grammatical-info" guid="12345">
                <label lang="en">Grammatical Info</label>
                <range-element id="noun" guid="67890">
                    <label lang="en">Noun</label>
                    <abbrev>n</abbrev>
                    <range-element id="countable" guid="54321">
                        <label lang="en">Countable</label>
                        <abbrev>c</abbrev>
                    </range-element>
                    <range-element id="uncountable" guid="98765">
                        <label lang="en">Uncountable</label>
                        <abbrev>u</abbrev>
                    </range-element>
                </range-element>
                <range-element id="verb" guid="13579">
                    <label lang="en">Verb</label>
                    <abbrev>v</abbrev>
                </range-element>
            </range>
        </lift-ranges>
        '''
    
    def test_parse_file(self):
        """Test parsing a LIFT ranges file."""
        with patch("os.path.exists", return_value=True), \
             patch("xml.etree.ElementTree.parse") as mock_parse:
            
            # Set up the mock
            mock_root = ET.fromstring(self.sample_ranges_xml)
            mock_parse.return_value.getroot.return_value = mock_root
            
            # Call the method with a dummy file path
            ranges = self.parser.parse_file("dummy.lift-ranges")
            
            # Verify the structure of the parsed data
            assert "grammatical-info" in ranges
            assert ranges["grammatical-info"]["id"] == "grammatical-info"
            assert ranges["grammatical-info"]["guid"] == "12345"
            assert ranges["grammatical-info"]["description"]["en"] == "Grammatical Info"
            
            # Verify the values (range elements)
            values = ranges["grammatical-info"]["values"]
            assert len(values) == 2
            
            # Verify noun element
            noun = next((v for v in values if v["id"] == "noun"), None)
            assert noun is not None
            assert noun["guid"] == "67890"
            assert noun["description"]["en"] == "Noun"
            assert noun["abbrev"] == "n"
            
            # Verify noun children
            assert len(noun["children"]) == 2
            countable = next((c for c in noun["children"] if c["id"] == "countable"), None)
            assert countable is not None
            assert countable["guid"] == "54321"
            assert countable["description"]["en"] == "Countable"
            assert countable["abbrev"] == "c"
            
            # Verify verb element
            verb = next((v for v in values if v["id"] == "verb"), None)
            assert verb is not None
            assert verb["guid"] == "13579"
            assert verb["description"]["en"] == "Verb"
            assert verb["abbrev"] == "v"
    
    def test_file_not_found(self):
        """Test handling of non-existent file."""
        with pytest.raises(FileNotFoundError):
            self.parser.parse_file("nonexistent.lift-ranges")
