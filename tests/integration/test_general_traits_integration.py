"""
Integration tests for LIFT 0.13 General Traits (Flexible Metadata).
Tests XML parsing and generation of trait elements on various LIFT elements.
"""

import pytest
from app.parsers.lift_parser import LIFTParser
from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example


@pytest.mark.integration
class TestGeneralTraitsXMLParsing:
    """Test parsing LIFT XML with general traits on various elements."""
    
    def test_parse_entry_with_morph_type_trait(self) -> None:
        """Test parsing entry with morph-type trait."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test1">
        <lexical-unit>
            <form lang="en"><text>running</text></form>
        </lexical-unit>
        <trait name="morph-type" value="stem"/>
        <sense id="s1">
            <gloss lang="en"><text>verb form</text></gloss>
        </sense>
    </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_lift_content(xml)
        
        assert len(entries) == 1
        entry = entries[0]
        assert entry.traits is not None
        assert entry.traits.get("morph-type") == "stem"
    
    def test_parse_entry_with_multiple_traits(self) -> None:
        """Test parsing entry with multiple traits."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test2">
        <lexical-unit>
            <form lang="en"><text>test phrase</text></form>
        </lexical-unit>
        <trait name="morph-type" value="phrase"/>
        <trait name="status" value="verified"/>
        <sense id="s1">
            <gloss lang="en"><text>multi-word expression</text></gloss>
        </sense>
    </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_lift_content(xml)
        
        entry = entries[0]
        assert entry.traits["morph-type"] == "phrase"
        assert entry.traits["status"] == "verified"
    
    def test_parse_sense_with_general_traits(self) -> None:
        """Test parsing sense with general trait elements."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test3">
        <lexical-unit>
            <form lang="en"><text>word</text></form>
        </lexical-unit>
        <sense id="s1">
            <gloss lang="en"><text>test</text></gloss>
            <trait name="status" value="reviewed"/>
            <trait name="source" value="corpus"/>
        </sense>
    </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_lift_content(xml)
        
        sense = entries[0].senses[0]
        assert sense.traits["status"] == "reviewed"
        assert sense.traits["source"] == "corpus"
    
    def test_parse_sense_with_domain_and_usage_traits(self) -> None:
        """Test parsing sense with domain-type and usage-type traits (already supported)."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test4">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <sense id="s1">
            <gloss lang="en"><text>examination</text></gloss>
            <trait name="domain-type" value="medycyna"/>
            <trait name="usage-type" value="przenosnie"/>
        </sense>
    </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_lift_content(xml)
        
        sense = entries[0].senses[0]
        # These are already stored in usage_type and domain_type lists
        assert "medycyna" in sense.domain_type
        assert "przenosnie" in sense.usage_type


@pytest.mark.integration
class TestGeneralTraitsXMLGeneration:
    """Test generating LIFT XML with general traits."""
    
    def test_generate_entry_with_traits(self) -> None:
        """Test generating XML for entry with traits."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "compound-word"},
            traits={
                "morph-type": "phrase",
                "status": "verified"
            },
            senses=[Sense(id_="s1", glosses={"en": "multi-word"})]
        )
        
        parser = LIFTParser()
        xml = parser.generate_lift_string([entry])
        
        # Verify trait elements in XML
        assert 'trait name="morph-type" value="phrase"' in xml
        assert 'trait name="status" value="verified"' in xml
    
    def test_generate_sense_with_general_traits(self) -> None:
        """Test generating XML for sense with general traits."""
        sense = Sense(
            id_="s1",
            glosses={"en": "test"},
            traits={
                "status": "reviewed",
                "confidence": "high"
            }
        )
        
        entry = Entry(
            id_="test2",
            lexical_unit={"en": "word"},
            senses=[sense]
        )
        
        parser = LIFTParser()
        xml = parser.generate_lift_string([entry])
        
        # Verify sense-level trait elements
        assert 'trait name="status" value="reviewed"' in xml
        assert 'trait name="confidence" value="high"' in xml
    
    def test_roundtrip_preserves_all_trait_types(self) -> None:
        """Test that parsing and generating preserves all trait types."""
        original_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test5">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <trait name="morph-type" value="stem"/>
        <trait name="import-date" value="2024-01-01"/>
        <sense id="s1">
            <gloss lang="en"><text>examination</text></gloss>
            <trait name="status" value="verified"/>
            <trait name="domain-type" value="technika"/>
        </sense>
    </entry>
</lift>"""
        
        parser = LIFTParser()
        
        # Parse original XML
        entries = parser.parse_lift_content(original_xml)
        entry = entries[0]
        sense = entry.senses[0]
        
        # Verify parsed data
        assert entry.traits["morph-type"] == "stem"
        assert entry.traits["import-date"] == "2024-01-01"
        assert sense.traits.get("status") == "verified"  # General trait
        assert "technika" in sense.domain_type  # Domain trait (stored separately)
        
        # Generate new XML
        new_xml = parser.generate_lift_string(entries)
        
        # Parse generated XML
        reparsed_entries = parser.parse_lift_content(new_xml)
        reparsed_entry = reparsed_entries[0]
        reparsed_sense = reparsed_entry.senses[0]
        
        # Verify roundtrip preservation
        assert reparsed_entry.traits["morph-type"] == "stem"
        assert reparsed_entry.traits.get("import-date") == "2024-01-01"
        assert reparsed_sense.traits.get("status") == "verified"
        assert "technika" in reparsed_sense.domain_type
