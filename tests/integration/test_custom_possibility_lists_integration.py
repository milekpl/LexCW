"""
Integration tests for custom possibility list XML parsing/generation.

Tests Day 38-39 implementation:
- ReferenceAtomic trait parsing and generation
- ReferenceCollection trait parsing and generation
- Custom range loading from lift-ranges
- Round-trip XML preservation
"""

from __future__ import annotations
import pytest
from app.parsers.lift_parser import LIFTParser, LIFTRangesParser


@pytest.mark.integration
class TestReferenceAtomicXML:
    """Test ReferenceAtomic custom field XML parsing/generation."""
    
    def test_parse_reference_atomic_on_entry(self) -> None:
        """Test parsing ReferenceAtomic trait on entry."""
        lift_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
  <entry id="test-entry">
    <lexical-unit>
      <form lang="en"><text>test</text></form>
    </lexical-unit>
    <sense>
      <gloss lang="en"><text>test sense</text></gloss>
    </sense>
    <trait name="CustomFldEntry-Status" value="Pending"/>
  </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_string(lift_xml)
        
        assert len(entries) == 1
        assert entries[0].traits["CustomFldEntry-Status"] == "Pending"
    
    def test_parse_reference_atomic_on_sense(self) -> None:
        """Test parsing ReferenceAtomic trait on sense."""
        lift_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
  <entry id="test-entry">
    <lexical-unit>
      <form lang="en"><text>test</text></form>
    </lexical-unit>
    <sense>
      <gloss lang="en"><text>meaning</text></gloss>
      <trait name="CustomFldSense-Domain" value="Nature.Plants"/>
    </sense>
  </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_string(lift_xml)
        
        assert len(entries) == 1
        assert len(entries[0].senses) == 1
        assert entries[0].senses[0].traits["CustomFldSense-Domain"] == "Nature.Plants"
    
    def test_parse_reference_atomic_hierarchical(self) -> None:
        """Test parsing ReferenceAtomic with hierarchical value."""
        lift_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
  <entry id="test-entry">
    <lexical-unit>
      <form lang="en"><text>test</text></form>
    </lexical-unit>
    <sense>
      <gloss lang="en"><text>test sense</text></gloss>
    </sense>
    <trait name="CustomFldEntry-Location" value="World.Africa.Kenya.Nairobi"/>
  </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_string(lift_xml)
        
        assert entries[0].traits["CustomFldEntry-Location"] == "World.Africa.Kenya.Nairobi"
    
    def test_generate_reference_atomic(self) -> None:
        """Test generating ReferenceAtomic trait XML."""
        from app.models.entry import Entry
        from app.models.sense import Sense
        
        sense = Sense(glosses={"en": "test sense"})
        entry = Entry(
            id_="test-entry",
            lexical_unit={"en": "test"},
            traits={
                "CustomFldEntry-Status": "Confirmed"
            },
            senses=[sense]
        )
        
        parser = LIFTParser()
        xml = parser.generate_lift_string([entry])
        
        assert 'trait name="CustomFldEntry-Status" value="Confirmed"' in xml


@pytest.mark.integration
class TestReferenceCollectionXML:
    """Test ReferenceCollection custom field XML parsing/generation."""
    
    def test_parse_reference_collection_multiple_values(self) -> None:
        """Test parsing ReferenceCollection with comma-separated values."""
        lift_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
  <entry id="test-entry">
    <lexical-unit>
      <form lang="en"><text>test</text></form>
    </lexical-unit>
    <sense>
      <gloss lang="en"><text>test sense</text></gloss>
    </sense>
    <trait name="CustomFldEntry-Tags" value="noun,common,countable"/>
  </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_string(lift_xml)
        
        assert len(entries) == 1
        assert entries[0].traits["CustomFldEntry-Tags"] == "noun,common,countable"
        values = entries[0].traits["CustomFldEntry-Tags"].split(",")
        assert len(values) == 3
    
    def test_parse_reference_collection_single_value(self) -> None:
        """Test parsing ReferenceCollection with single value."""
        lift_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
  <entry id="test-entry">
    <lexical-unit>
      <form lang="en"><text>test</text></form>
    </lexical-unit>
    <sense>
      <gloss lang="en"><text>test sense</text></gloss>
    </sense>
    <trait name="CustomFldEntry-Tags" value="noun"/>
  </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_string(lift_xml)
        
        assert entries[0].traits["CustomFldEntry-Tags"] == "noun"
    
    def test_parse_reference_collection_on_sense(self) -> None:
        """Test parsing ReferenceCollection on sense."""
        lift_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.13">
  <entry id="test-entry">
    <lexical-unit>
      <form lang="en"><text>bank</text></form>
    </lexical-unit>
    <sense>
      <gloss lang="en"><text>financial institution</text></gloss>
      <trait name="CustomFldSense-Domains" value="Finance.Banking,Business.Commerce"/>
    </sense>
  </entry>
</lift>"""
        
        parser = LIFTParser()
        entries = parser.parse_string(lift_xml)
        
        assert len(entries[0].senses) == 1
        domains = entries[0].senses[0].traits["CustomFldSense-Domains"]
        assert "Finance.Banking" in domains
        assert "Business.Commerce" in domains
    
    def test_generate_reference_collection(self) -> None:
        """Test generating ReferenceCollection trait XML."""
        from app.models.entry import Entry
        from app.models.sense import Sense
        
        sense = Sense(glosses={"en": "test sense"})
        entry = Entry(
            id_="test-entry",
            lexical_unit={"en": "test"},
            traits={
                "CustomFldEntry-Tags": "noun,common,countable"
            },
            senses=[sense]
        )
        
        parser = LIFTParser()
        xml = parser.generate_lift_string([entry])
        
        assert 'trait name="CustomFldEntry-Tags" value="noun,common,countable"' in xml


@pytest.mark.integration
class TestCustomRangeLoading:
    """Test loading custom possibility lists from lift-ranges."""
    
    def test_parse_custom_range_basic(self) -> None:
        """Test parsing a basic custom possibility list."""
        ranges_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
  <range id="CustomList1">
    <range-element id="value1">
      <label lang="en"><text>Value 1</text></label>
    </range-element>
    <range-element id="value2">
      <label lang="en"><text>Value 2</text></label>
    </range-element>
  </range>
</lift-ranges>"""
        
        parser = LIFTRangesParser()
        ranges = parser.parse_string(ranges_xml)
        
        assert "CustomList1" in ranges
        assert len(ranges["CustomList1"]["values"]) == 2
    
    def test_parse_custom_range_hierarchical(self) -> None:
        """Test parsing hierarchical custom possibility list."""
        ranges_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
  <range id="location">
    <range-element id="World">
      <label lang="en"><text>World</text></label>
      <range-element id="Africa">
        <label lang="en"><text>Africa</text></label>
        <range-element id="Kenya">
          <label lang="en"><text>Kenya</text></label>
        </range-element>
      </range-element>
    </range-element>
  </range>
</lift-ranges>"""
        
        parser = LIFTRangesParser()
        ranges = parser.parse_string(ranges_xml)
        
        assert "location" in ranges
        world = ranges["location"]["values"][0]
        assert world["id"] == "World"
        assert len(world["children"]) == 1
        assert world["children"][0]["id"] == "Africa"
    
    def test_parse_multiple_custom_ranges(self) -> None:
        """Test parsing multiple custom possibility lists."""
        ranges_xml = """<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
  <range id="status">
    <range-element id="Pending"><label lang="en"><text>Pending</text></label></range-element>
    <range-element id="Confirmed"><label lang="en"><text>Confirmed</text></label></range-element>
  </range>
  <range id="priority">
    <range-element id="High"><label lang="en"><text>High</text></label></range-element>
    <range-element id="Medium"><label lang="en"><text>Medium</text></label></range-element>
    <range-element id="Low"><label lang="en"><text>Low</text></label></range-element>
  </range>
</lift-ranges>"""
        
        parser = LIFTRangesParser()
        ranges = parser.parse_string(ranges_xml)
        
        assert "status" in ranges
        assert "priority" in ranges
        assert len(ranges["status"]["values"]) == 2
        assert len(ranges["priority"]["values"]) == 3


@pytest.mark.integration
class TestRoundTripPossibilityLists:
    """Test round-trip preservation of custom possibility list references."""
    
    def test_roundtrip_reference_atomic(self) -> None:
        """Test round-trip of ReferenceAtomic field."""
        from app.models.entry import Entry
        from app.models.sense import Sense
        
        original = Entry(
            id_="test-entry",
            lexical_unit={"en": "test"},
            traits={
                "CustomFldEntry-Status": "Confirmed"
            },
            senses=[Sense(glosses={"en": "test"})]
        )
        
        parser = LIFTParser()
        xml = parser.generate_lift_string([original])
        parsed = parser.parse_string(xml)
        
        assert len(parsed) == 1
        assert parsed[0].traits["CustomFldEntry-Status"] == "Confirmed"
    
    def test_roundtrip_reference_collection(self) -> None:
        """Test round-trip of ReferenceCollection field."""
        from app.models.entry import Entry
        from app.models.sense import Sense
        
        original = Entry(
            id_="test-entry",
            lexical_unit={"en": "test"},
            traits={
                "CustomFldEntry-Tags": "noun,common,countable"
            },
            senses=[Sense(glosses={"en": "test"})]
        )
        
        parser = LIFTParser()
        xml = parser.generate_lift_string([original])
        parsed = parser.parse_string(xml)
        
        assert len(parsed) == 1
        assert parsed[0].traits["CustomFldEntry-Tags"] == "noun,common,countable"
    
    def test_roundtrip_mixed_possibility_fields(self) -> None:
        """Test round-trip with both ReferenceAtomic and ReferenceCollection."""
        from app.models.entry import Entry
        from app.models.sense import Sense
        
        sense = Sense(
            glosses={"en": "test"},
            traits={
                "CustomFldSense-Domain": "Nature.Plants",
                "CustomFldSense-RegisterTags": "formal,technical"
            }
        )
        
        original = Entry(
            id_="test-entry",
            lexical_unit={"en": "test"},
            traits={
                "CustomFldEntry-Status": "Confirmed",
                "CustomFldEntry-Tags": "noun,common"
            },
            senses=[sense]
        )
        
        parser = LIFTParser()
        xml = parser.generate_lift_string([original])
        parsed = parser.parse_string(xml)
        
        assert len(parsed) == 1
        assert parsed[0].traits["CustomFldEntry-Status"] == "Confirmed"
        assert parsed[0].traits["CustomFldEntry-Tags"] == "noun,common"
        assert parsed[0].senses[0].traits["CustomFldSense-Domain"] == "Nature.Plants"
        assert parsed[0].senses[0].traits["CustomFldSense-RegisterTags"] == "formal,technical"
