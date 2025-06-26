"""
Test grammatical info parsing specifically.
"""

import pytest
from app.parsers.lift_parser import LIFTParser
from app.models.entry import Entry
from app.models.sense import Sense
import xml.etree.ElementTree as ET

class TestGrammaticalInfoParsing:
    """Test cases specifically for grammatical info parsing."""
    
    def test_grammatical_info_with_namespace(self):
        """Test parsing grammatical info with namespace."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <lift xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
            <entry id="test_entry">
                <lexical-unit>
                    <form lang="en">
                        <text>test</text>
                    </form>
                </lexical-unit>
                <sense id="sense1">
                    <grammatical-info value="noun"/>
                    <definition>
                        <form lang="en">
                            <text>A test word</text>
                        </form>
                    </definition>
                </sense>
            </entry>
        </lift>"""
        
        parser = LIFTParser()
        root = ET.fromstring(xml_content)
        entry_elem = root.find('.//{http://fieldworks.sil.org/schemas/lift/0.13}entry')
        
        entry = parser._parse_entry(entry_elem)
        
        assert len(entry.senses) == 1
        sense = entry.senses[0]
        assert isinstance(sense, Sense)
        assert sense.grammatical_info == "noun"
    
    def test_grammatical_info_without_namespace(self):
        """Test parsing grammatical info without namespace."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <entry id="test_entry">
            <lexical-unit>
                <form lang="en">
                    <text>test</text>
                </form>
            </lexical-unit>
            <sense id="sense1">
                <grammatical-info value="verb"/>
                <definition>
                    <form lang="en">
                        <text>A test action</text>
                    </form>
                </definition>
            </sense>
        </entry>"""
        
        parser = LIFTParser()
        root = ET.fromstring(xml_content)
        
        entry = parser._parse_entry(root)
        
        assert len(entry.senses) == 1
        sense = entry.senses[0]
        assert isinstance(sense, Sense)
        assert sense.grammatical_info == "verb"
    
    def test_multiple_senses_with_different_grammatical_info(self):
        """Test parsing multiple senses with different grammatical info."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <entry id="test_entry">
            <lexical-unit>
                <form lang="en">
                    <text>run</text>
                </form>
            </lexical-unit>
            <sense id="sense1">
                <grammatical-info value="verb"/>
                <definition>
                    <form lang="en">
                        <text>To move quickly</text>
                    </form>
                </definition>
            </sense>
            <sense id="sense2">
                <grammatical-info value="noun"/>
                <definition>
                    <form lang="en">
                        <text>A running session</text>
                    </form>
                </definition>
            </sense>
        </entry>"""
        
        parser = LIFTParser()
        root = ET.fromstring(xml_content)
        
        entry = parser._parse_entry(root)
        
        assert len(entry.senses) == 2
        
        # Find senses by ID
        sense1 = next(s for s in entry.senses if s.id == "sense1")
        sense2 = next(s for s in entry.senses if s.id == "sense2")
        
        assert sense1.grammatical_info == "verb"
        assert sense2.grammatical_info == "noun"
    
    def test_sense_without_grammatical_info(self):
        """Test parsing sense without grammatical info."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <entry id="test_entry">
            <lexical-unit>
                <form lang="en">
                    <text>test</text>
                </form>
            </lexical-unit>
            <sense id="sense1">
                <definition>
                    <form lang="en">
                        <text>A test word</text>
                    </form>
                </definition>
            </sense>
        </entry>"""
        
        parser = LIFTParser()
        root = ET.fromstring(xml_content)
        
        entry = parser._parse_entry(root)
        
        assert len(entry.senses) == 1
        sense = entry.senses[0]
        assert isinstance(sense, Sense)
        assert sense.grammatical_info is None
    
    def test_empty_grammatical_info_value(self):
        """Test parsing grammatical info with empty value."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <entry id="test_entry">
            <lexical-unit>
                <form lang="en">
                    <text>test</text>
                </form>
            </lexical-unit>
            <sense id="sense1">
                <grammatical-info value=""/>
                <definition>
                    <form lang="en">
                        <text>A test word</text>
                    </form>
                </definition>
            </sense>
        </entry>"""
        
        parser = LIFTParser()
        root = ET.fromstring(xml_content)
        
        entry = parser._parse_entry(root)
        
        assert len(entry.senses) == 1
        sense = entry.senses[0]
        assert isinstance(sense, Sense)
        assert sense.grammatical_info == ""  # Empty string, not None
