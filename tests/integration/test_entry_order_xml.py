"""
Integration tests for Entry order and date attributes XML parsing/generation (Day 43-44).

Tests LIFT 0.13 XML round-trip for:
- order attribute (LIFT uses this for homograph_number)
- dateDeleted attribute
- Preservation of all date attributes
"""

import pytest
from app.parsers.lift_parser import LIFTParser
from app.models.entry import Entry


@pytest.mark.integration
class TestOrderAttributeXML:
    """Test order attribute in LIFT XML (used for homograph_number)."""
    
    def test_parse_entry_with_order(self):
        """LIFTParser can parse entry with order attribute (homograph_number)."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="test-entry" order="5">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
            </entry>
        </lift>'''
        
        parser = LIFTParser(validate=False)  # Disable validation for minimal test entries
        entries = parser.parse_string(xml)
        
        assert len(entries) == 1
        assert entries[0].id == 'test-entry'
        assert entries[0].order == 5  # order is set to homograph_number value
        assert entries[0].homograph_number == 5
    
    def test_parse_entry_without_order(self):
        """Entry without order attribute has order=None."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="test-entry">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
            </entry>
        </lift>'''
        
        parser = LIFTParser(validate=False)  # Disable validation for minimal test entries
        entries = parser.parse_string(xml)
        
        assert len(entries) == 1
        assert entries[0].order is None
        assert entries[0].homograph_number is None
    
    def test_generate_entry_with_order(self):
        """LIFTParser generates order attribute in XML (from homograph_number)."""
        entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'},
            homograph_number=10
        )
        
        parser = LIFTParser(validate=False)  # Disable validation for minimal test entries
        xml_output = parser.generate_lift_string([entry])
        
        assert 'order="10"' in xml_output
        assert 'id="test-entry"' in xml_output


@pytest.mark.integration
class TestDateDeletedAttributeXML:
    """Test dateDeleted attribute in LIFT XML."""
    
    def test_parse_entry_with_date_deleted(self):
        """LIFTParser can parse entry with dateDeleted attribute."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="test-entry" dateDeleted="2025-12-05T10:30:00Z">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
            </entry>
        </lift>'''
        
        parser = LIFTParser(validate=False)  # Disable validation for minimal test entries
        entries = parser.parse_string(xml)
        
        assert len(entries) == 1
        assert entries[0].date_deleted == '2025-12-05T10:30:00Z'
    
    def test_generate_entry_with_date_deleted(self):
        """LIFTParser generates dateDeleted attribute in XML."""
        entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'},
            date_deleted='2025-12-05T10:30:00Z'
        )
        
        parser = LIFTParser(validate=False)  # Disable validation for minimal test entries
        xml_output = parser.generate_lift_string([entry])
        
        assert 'dateDeleted="2025-12-05T10:30:00Z"' in xml_output


@pytest.mark.integration
class TestAllDateAttributesXML:
    """Test all date attributes together in LIFT XML."""
    
    def test_parse_entry_with_all_dates(self):
        """LIFTParser can parse all date attributes."""
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <lift version="0.13">
            <entry id="test-entry" 
                   dateCreated="2025-01-15T10:30:00Z"
                   dateModified="2025-02-20T14:45:00Z"
                   dateDeleted="2025-03-01T09:00:00Z">
                <lexical-unit>
                    <form lang="en"><text>test</text></form>
                </lexical-unit>
            </entry>
        </lift>'''
        
        parser = LIFTParser(validate=False)  # Disable validation for minimal test entries
        entries = parser.parse_string(xml)
        
        assert len(entries) == 1
        entry = entries[0]
        assert entry.date_created == '2025-01-15T10:30:00Z'
        assert entry.date_modified == '2025-02-20T14:45:00Z'
        assert entry.date_deleted == '2025-03-01T09:00:00Z'
    
    def test_generate_entry_with_all_dates(self):
        """LIFTParser generates all date attributes in XML."""
        entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'},
            date_created='2025-01-15T10:30:00Z',
            date_modified='2025-02-20T14:45:00Z',
            date_deleted='2025-03-01T09:00:00Z'
        )
        
        parser = LIFTParser(validate=False)  # Disable validation for minimal test entries
        xml_output = parser.generate_lift_string([entry])
        
        assert 'dateCreated="2025-01-15T10:30:00Z"' in xml_output
        assert 'dateModified="2025-02-20T14:45:00Z"' in xml_output
        assert 'dateDeleted="2025-03-01T09:00:00Z"' in xml_output


@pytest.mark.integration
class TestOrderAndDatesRoundTrip:
    """Test round-trip preservation of order and date attributes."""
    
    def test_round_trip_with_order_and_dates(self):
        """Order (homograph_number) and dates survive XML round-trip."""
        original_entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'},
            homograph_number=15,
            date_created='2025-01-15T10:30:00Z',
            date_modified='2025-02-20T14:45:00Z',
            date_deleted='2025-03-01T09:00:00Z'
        )
        
        parser = LIFTParser(validate=False)  # Disable validation for minimal test entries
        
        # Generate XML
        xml_output = parser.generate_lift_string([original_entry])
        
        # Parse it back
        parsed_entries = parser.parse_string(xml_output)
        
        assert len(parsed_entries) == 1
        parsed_entry = parsed_entries[0]
        
        assert parsed_entry.id == 'test-entry'
        assert parsed_entry.order == 15
        assert parsed_entry.homograph_number == 15
        assert parsed_entry.date_created == '2025-01-15T10:30:00Z'
        assert parsed_entry.date_modified == '2025-02-20T14:45:00Z'
        assert parsed_entry.date_deleted == '2025-03-01T09:00:00Z'
    
    def test_round_trip_without_optional_attributes(self):
        """Entry without optional attributes survives round-trip."""
        original_entry = Entry(
            id_='test-entry',
            lexical_unit={'en': 'test'}
        )
        
        parser = LIFTParser(validate=False)  # Disable validation for minimal test entries
        
        # Generate XML
        xml_output = parser.generate_lift_string([original_entry])
        
        # Parse it back
        parsed_entries = parser.parse_string(xml_output)
        
        assert len(parsed_entries) == 1
        parsed_entry = parsed_entries[0]
        
        assert parsed_entry.id == 'test-entry'
        assert parsed_entry.order is None
        assert parsed_entry.homograph_number is None
        assert parsed_entry.date_deleted is None
