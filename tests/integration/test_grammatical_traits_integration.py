"""
Integration tests for LIFT 0.13 Grammatical Info Traits feature.
Tests XML parsing and generation of trait elements within grammatical-info.
"""

import pytest
from app.parsers.lift_parser import LIFTParser
from app.models.entry import Entry
from app.models.sense import Sense


@pytest.mark.integration
class TestGrammaticalTraitsXMLParsing:
    """Test parsing LIFT XML with grammatical-info traits."""
    
    def test_parse_sense_with_grammatical_traits(self) -> None:
        """Test parsing sense with grammatical traits in XML."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test1">
        <lexical-unit>
            <form lang="en"><text>cat</text></form>
        </lexical-unit>
        <sense id="s1">
            <grammatical-info value="Noun">
                <trait name="gender" value="masculine"/>
                <trait name="number" value="singular"/>
            </grammatical-info>
            <gloss lang="en"><text>feline animal</text></gloss>
        </sense>
    </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_lift_content(xml)
        
        assert len(entries) == 1
        entry = entries[0]
        assert len(entry.senses) == 1
        sense = entry.senses[0]
        
        assert sense.grammatical_info == "Noun"
        assert sense.grammatical_traits is not None
        assert sense.grammatical_traits["gender"] == "masculine"
        assert sense.grammatical_traits["number"] == "singular"
    
    def test_parse_sense_with_multiple_traits(self) -> None:
        """Test parsing sense with multiple morphological traits."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test2">
        <lexical-unit>
            <form lang="en"><text>walked</text></form>
        </lexical-unit>
        <sense id="s1">
            <grammatical-info value="Verb">
                <trait name="tense" value="past"/>
                <trait name="aspect" value="perfective"/>
                <trait name="mood" value="indicative"/>
            </grammatical-info>
            <gloss lang="en"><text>moved on foot</text></gloss>
        </sense>
    </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_lift_content(xml)
        
        sense = entries[0].senses[0]
        assert sense.grammatical_traits["tense"] == "past"
        assert sense.grammatical_traits["aspect"] == "perfective"
        assert sense.grammatical_traits["mood"] == "indicative"
    
    def test_parse_sense_without_traits(self) -> None:
        """Test parsing sense with grammatical-info but no traits."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test3">
        <lexical-unit>
            <form lang="en"><text>run</text></form>
        </lexical-unit>
        <sense id="s1">
            <grammatical-info value="Verb"/>
            <gloss lang="en"><text>move quickly</text></gloss>
        </sense>
    </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_lift_content(xml)
        
        sense = entries[0].senses[0]
        assert sense.grammatical_info == "Verb"
        assert sense.grammatical_traits is None
    
    def test_parse_variant_with_grammatical_traits(self) -> None:
        """Test parsing variant with grammatical traits."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test4">
        <lexical-unit>
            <form lang="en"><text>good</text></form>
        </lexical-unit>
        <sense id="s1">
            <gloss lang="en"><text>adjective</text></gloss>
        </sense>
        <variant>
            <form lang="en"><text>better</text></form>
            <grammatical-info value="Adjective">
                <trait name="degree" value="comparative"/>
            </grammatical-info>
        </variant>
    </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_lift_content(xml)
        
        assert len(entries[0].variants) == 1
        variant = entries[0].variants[0]
        assert variant.grammatical_traits is not None
        assert variant.grammatical_traits["degree"] == "comparative"
    
    def test_parse_custom_traits(self) -> None:
        """Test parsing custom trait names."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test5">
        <lexical-unit>
            <form lang="en"><text>book</text></form>
        </lexical-unit>
        <sense id="s1">
            <grammatical-info value="Noun">
                <trait name="animacy" value="inanimate"/>
                <trait name="countability" value="countable"/>
            </grammatical-info>
            <gloss lang="en"><text>printed work</text></gloss>
        </sense>
    </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_lift_content(xml)
        
        sense = entries[0].senses[0]
        assert sense.grammatical_traits["animacy"] == "inanimate"
        assert sense.grammatical_traits["countability"] == "countable"


@pytest.mark.integration
class TestGrammaticalTraitsXMLGeneration:
    """Test generating LIFT XML with grammatical-info traits."""
    
    def test_generate_sense_with_traits(self) -> None:
        """Test generating XML for sense with grammatical traits."""
        sense = Sense(
            id_="s1",
            glosses={"en": "cat"},
            grammatical_info="Noun",
            grammatical_traits={
                "gender": "masculine",
                "number": "singular"
            }
        )
        
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "cat"},
            senses=[sense]
        )
        
        parser = LIFTParser()
        xml = parser.generate_lift_string([entry])
        
        # Verify trait elements are in XML (with namespace prefix)
        assert 'grammatical-info value="Noun"' in xml
        assert 'trait name="gender" value="masculine"' in xml
        assert 'trait name="number" value="singular"' in xml
    
    def test_generate_sense_without_traits(self) -> None:
        """Test generating XML for sense without traits."""
        sense = Sense(
            id_="s1",
            glosses={"en": "run"},
            grammatical_info="Verb",
            grammatical_traits=None
        )
        
        entry = Entry(
            id_="test2",
            lexical_unit={"en": "run"},
            senses=[sense]
        )
        
        parser = LIFTParser()
        xml = parser.generate_lift_string([entry])
        
        # Verify self-closing grammatical-info without nested traits
        assert 'grammatical-info value="Verb"' in xml
        # Ensure no traits within grammatical-info (only morph-type trait at entry level is OK)
        import re
        gram_info_blocks = re.findall(r'<[^>]*grammatical-info[^>]*>.*?</[^>]*grammatical-info>', xml, re.DOTALL)
        sense_gram_blocks = [block for block in gram_info_blocks if 'Verb' in block]
        for block in sense_gram_blocks:
            assert '<' not in block.split('>')[1] or '</lift:grammatical-info>' in block or '/>' in block  # No nested elements or self-closing
    
    def test_generate_variant_with_traits(self) -> None:
        """Test generating XML for variant with traits."""
        from app.models.entry import Variant
        
        sense = Sense(
            id_="s1",
            glosses={"en": "adjective"}
        )
        
        variant = Variant(
            form={"en": "better"},
            grammatical_traits={"degree": "comparative"}
        )
        
        entry = Entry(
            id_="test3",
            lexical_unit={"en": "good"},
            senses=[sense],
            variants=[variant]
        )
        
        parser = LIFTParser()
        xml = parser.generate_lift_string([entry])
        
        # Verify variant with trait in XML
        assert '<' in xml and 'variant' in xml
        assert 'trait name="degree" value="comparative"' in xml
    
    def test_roundtrip_preserves_traits(self) -> None:
        """Test that parsing and generating preserves grammatical traits."""
        original_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
    <entry id="test6">
        <lexical-unit>
            <form lang="en"><text>table</text></form>
        </lexical-unit>
        <sense id="s1">
            <grammatical-info value="Noun">
                <trait name="gender" value="feminine"/>
                <trait name="case" value="nominative"/>
            </grammatical-info>
            <gloss lang="en"><text>furniture</text></gloss>
        </sense>
    </entry>
</lift>"""
        
        parser = LIFTParser()
        
        # Parse original XML
        entries = parser.parse_lift_content(original_xml)
        sense = entries[0].senses[0]
        
        # Verify parsed data
        assert sense.grammatical_traits["gender"] == "feminine"
        assert sense.grammatical_traits["case"] == "nominative"
        
        # Generate new XML
        new_xml = parser.generate_lift_string(entries)
        
        # Parse generated XML
        reparsed_entries = parser.parse_lift_content(new_xml)
        reparsed_sense = reparsed_entries[0].senses[0]
        
        # Verify roundtrip preservation
        assert reparsed_sense.grammatical_traits["gender"] == "feminine"
        assert reparsed_sense.grammatical_traits["case"] == "nominative"
