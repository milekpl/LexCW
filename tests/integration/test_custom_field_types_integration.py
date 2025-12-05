"""
Integration tests for LIFT 0.13 Custom Field Types (Day 36-37).

Tests XML parsing and generation for Integer, GenDate, and MultiUnicode custom field types.
"""

import pytest
from app.parsers.lift_parser import LIFTParser
from app.models.entry import Entry
from app.models.sense import Sense


@pytest.mark.integration
class TestIntegerCustomFieldsXML:
    """Test Integer custom field XML parsing and generation."""
    
    def test_parse_integer_custom_field_on_entry(self) -> None:
        """Test parsing integer custom field from entry XML."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test1">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <trait name="CustomFldEntry-Number" value="42"/>
    <sense>
        <gloss lang="en"><text>test</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        assert len(entries) == 1
        entry = entries[0]
        assert "CustomFldEntry-Number" in entry.traits
        assert entry.traits["CustomFldEntry-Number"] == "42"
    
    def test_parse_integer_custom_field_on_sense(self) -> None:
        """Test parsing integer custom field from sense XML."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test1">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <sense>
        <gloss lang="en"><text>test</text></gloss>
        <trait name="CustomFldSense-Count" value="100"/>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        entry = entries[0]
        sense = entry.senses[0]
        assert "CustomFldSense-Count" in sense.traits
        assert sense.traits["CustomFldSense-Count"] == "100"
    
    def test_generate_integer_custom_field(self) -> None:
        """Test generating integer custom field to XML."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            senses=[Sense(id_="s1", glosses={"en": "test"})],
            traits={"CustomFldEntry-Number": "42"}
        )
        
        parser = LIFTParser()
        xml = parser.generate_lift_string([entry])
        
        assert 'trait name="CustomFldEntry-Number" value="42"' in xml
    
    def test_roundtrip_integer_custom_field(self) -> None:
        """Test round-trip preservation of integer custom field."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test1">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <trait name="CustomFldEntry-Rating" value="5"/>
    <sense>
        <gloss lang="en"><text>test</text></gloss>
        <trait name="CustomFldSense-Priority" value="10"/>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries1 = parser.parse(xml_content)
        xml_generated = parser.generate_lift_string(entries1)
        entries2 = parser.parse(xml_generated)
        
        # Verify entry-level integer field
        assert entries2[0].traits["CustomFldEntry-Rating"] == "5"
        
        # Verify sense-level integer field
        assert entries2[0].senses[0].traits["CustomFldSense-Priority"] == "10"


@pytest.mark.integration
class TestGenDateCustomFieldsXML:
    """Test GenDate custom field XML parsing and generation."""
    
    def test_parse_gendate_exact(self) -> None:
        """Test parsing exact GenDate custom field."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test1">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <trait name="CustomFldEntry-Date" value="201105230"/>
    <sense>
        <gloss lang="en"><text>test</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        entry = entries[0]
        assert entry.traits["CustomFldEntry-Date"] == "201105230"
    
    def test_parse_gendate_approximate(self) -> None:
        """Test parsing approximate GenDate."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test1">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <trait name="CustomFldEntry-Date" value="201105231"/>
    <sense>
        <gloss lang="en"><text>test</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        assert entries[0].traits["CustomFldEntry-Date"] == "201105231"
    
    def test_parse_gendate_before_after(self) -> None:
        """Test parsing before/after GenDate values."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test1">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <trait name="CustomFldEntry-DateBefore" value="201105232"/>
    <trait name="CustomFldEntry-DateAfter" value="201105233"/>
    <sense>
        <gloss lang="en"><text>test</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        entry = entries[0]
        assert entry.traits["CustomFldEntry-DateBefore"] == "201105232"
        assert entry.traits["CustomFldEntry-DateAfter"] == "201105233"
    
    def test_generate_gendate(self) -> None:
        """Test generating GenDate custom field to XML."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            senses=[Sense(id_="s1", glosses={"en": "test"})],
            traits={"CustomFldEntry-FirstRecorded": "19500101"}
        )
        
        parser = LIFTParser()
        xml = parser.generate_lift_string([entry])
        
        assert 'trait name="CustomFldEntry-FirstRecorded" value="19500101"' in xml
    
    def test_roundtrip_gendate(self) -> None:
        """Test round-trip preservation of GenDate custom field."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test1">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <trait name="CustomFldEntry-Date" value="201105232"/>
    <sense>
        <gloss lang="en"><text>test</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries1 = parser.parse(xml_content)
        xml_generated = parser.generate_lift_string(entries1)
        entries2 = parser.parse(xml_generated)
        
        assert entries2[0].traits["CustomFldEntry-Date"] == "201105232"


@pytest.mark.integration
class TestMultiUnicodeCustomFieldsXML:
    """Test MultiUnicode custom field XML parsing and generation."""
    
    def test_parse_multiUnicode_single_language(self) -> None:
        """Test parsing MultiUnicode field with single language."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test1">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <field type="CustomFldEntry-Description">
        <form lang="en"><text>English description</text></form>
    </field>
    <sense>
        <gloss lang="en"><text>test</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        entry = entries[0]
        assert "CustomFldEntry-Description" in entry.custom_fields
        assert entry.custom_fields["CustomFldEntry-Description"]["en"] == "English description"
    
    def test_parse_multiUnicode_multiple_languages(self) -> None:
        """Test parsing MultiUnicode field with multiple writing systems."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test1">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <field type="CustomFldEntry-Notes">
        <form lang="en"><text>English note</text></form>
        <form lang="fr"><text>Note française</text></form>
        <form lang="pl"><text>Polski notatka</text></form>
    </field>
    <sense>
        <gloss lang="en"><text>test</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        entry = entries[0]
        field = entry.custom_fields["CustomFldEntry-Notes"]
        assert field["en"] == "English note"
        assert field["fr"] == "Note française"
        assert field["pl"] == "Polski notatka"
    
    def test_parse_multiUnicode_on_sense(self) -> None:
        """Test parsing MultiUnicode field on sense level."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test1">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <sense>
        <gloss lang="en"><text>test</text></gloss>
        <field type="CustomFldSense-Comment">
            <form lang="en"><text>Comment</text></form>
            <form lang="es"><text>Comentario</text></form>
        </field>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        sense = entries[0].senses[0]
        assert "CustomFldSense-Comment" in sense.custom_fields
        assert sense.custom_fields["CustomFldSense-Comment"]["en"] == "Comment"
        assert sense.custom_fields["CustomFldSense-Comment"]["es"] == "Comentario"
    
    def test_generate_multiUnicode(self) -> None:
        """Test generating MultiUnicode custom field to XML."""
        entry = Entry(
            id_="test1",
            lexical_unit={"en": "test"},
            senses=[Sense(id_="s1", glosses={"en": "test"})],
            custom_fields={
                "CustomFldEntry-Description": {
                    "en": "Description",
                    "fr": "Description"
                }
            }
        )
        
        parser = LIFTParser()
        xml = parser.generate_lift_string([entry])
        
        assert 'field type="CustomFldEntry-Description"' in xml
        assert 'lang="en"' in xml
        assert '>Description<' in xml
    
    def test_roundtrip_multiUnicode(self) -> None:
        """Test round-trip preservation of MultiUnicode custom field."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test1">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <field type="CustomFldEntry-MultiText">
        <form lang="en"><text>English</text></form>
        <form lang="pl"><text>Polski</text></form>
    </field>
    <sense>
        <gloss lang="en"><text>test</text></gloss>
        <field type="CustomFldSense-Notes">
            <form lang="en"><text>Sense note</text></form>
        </field>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries1 = parser.parse(xml_content)
        xml_generated = parser.generate_lift_string(entries1)
        entries2 = parser.parse(xml_generated)
        
        # Verify entry-level MultiUnicode
        entry_field = entries2[0].custom_fields["CustomFldEntry-MultiText"]
        assert entry_field["en"] == "English"
        assert entry_field["pl"] == "Polski"
        
        # Verify sense-level MultiUnicode
        sense_field = entries2[0].senses[0].custom_fields["CustomFldSense-Notes"]
        assert sense_field["en"] == "Sense note"


@pytest.mark.integration
class TestMixedCustomFieldTypesXML:
    """Test combinations of all three custom field types in XML."""
    
    def test_parse_all_three_types_together(self) -> None:
        """Test parsing entry with Integer, GenDate, and MultiUnicode fields."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test1">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <trait name="CustomFldEntry-Number" value="42"/>
    <trait name="CustomFldEntry-Date" value="201105230"/>
    <field type="CustomFldEntry-Description">
        <form lang="en"><text>Description</text></form>
    </field>
    <sense>
        <gloss lang="en"><text>test</text></gloss>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries = parser.parse(xml_content)
        
        entry = entries[0]
        # Integer
        assert entry.traits["CustomFldEntry-Number"] == "42"
        # GenDate
        assert entry.traits["CustomFldEntry-Date"] == "201105230"
        # MultiUnicode
        assert entry.custom_fields["CustomFldEntry-Description"]["en"] == "Description"
    
    def test_roundtrip_all_three_types(self) -> None:
        """Test round-trip with all three custom field types."""
        xml_content = '''<?xml version="1.0" encoding="utf-8"?>
<entry id="test1">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <trait name="morph-type" value="stem"/>
    <trait name="CustomFldEntry-Rating" value="5"/>
    <trait name="CustomFldEntry-Created" value="202312040"/>
    <field type="CustomFldEntry-Notes">
        <form lang="en"><text>English notes</text></form>
        <form lang="pl"><text>Polski notatki</text></form>
    </field>
    <sense>
        <gloss lang="en"><text>test</text></gloss>
        <trait name="CustomFldSense-Count" value="10"/>
        <field type="CustomFldSense-Comment">
            <form lang="en"><text>Comment</text></form>
        </field>
    </sense>
</entry>'''
        
        parser = LIFTParser()
        entries1 = parser.parse(xml_content)
        xml_generated = parser.generate_lift_string(entries1)
        entries2 = parser.parse(xml_generated)
        
        entry = entries2[0]
        sense = entry.senses[0]
        
        # Standard trait
        assert entry.traits["morph-type"] == "stem"
        
        # Entry-level custom fields
        assert entry.traits["CustomFldEntry-Rating"] == "5"
        assert entry.traits["CustomFldEntry-Created"] == "202312040"
        assert entry.custom_fields["CustomFldEntry-Notes"]["en"] == "English notes"
        assert entry.custom_fields["CustomFldEntry-Notes"]["pl"] == "Polski notatki"
        
        # Sense-level custom fields
        assert sense.traits["CustomFldSense-Count"] == "10"
        assert sense.custom_fields["CustomFldSense-Comment"]["en"] == "Comment"
