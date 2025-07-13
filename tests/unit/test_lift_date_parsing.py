import pytest
from datetime import datetime
from app.parsers.lift_parser import LiftParser
from app.models.entry import Entry

def test_lift_parser_extracts_dates():
    """Test that LIFT parser extracts date_created and date_modified fields"""
    test_lift = '''<entry id="test1" dateCreated="2023-01-15T12:00:00Z" dateModified="2023-02-20T15:30:00Z">
        <lexical-unit><form lang="en"><text>test</text></form></lexical-unit>
    </entry>'''
    
    parser = LiftParser()
    entries = parser.parse_from_string(test_lift)
    
    assert len(entries) == 1
    entry = entries[0]
    assert isinstance(entry, Entry)
    assert entry.date_created == datetime(2023, 1, 15, 12, 0, 0)
    assert entry.date_modified == datetime(2023, 2, 20, 15, 30, 0)