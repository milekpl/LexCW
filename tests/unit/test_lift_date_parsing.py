import pytest
pytestmark = pytest.mark.skip_et_mock
from datetime import datetime, timezone
from app.parsers.lift_parser import LIFTParser
from app.models.entry import Entry

def test_lift_parser_extracts_dates() -> None:
    """Test that LIFT parser extracts date_created and date_modified fields with a valid entry"""
    test_lift = '''<entry id="test1" dateCreated="2023-01-15T12:00:00Z" dateModified="2023-02-20T15:30:00Z">
        <lexical-unit>
            <form lang="en"><text>test entry</text></form>
        </lexical-unit>
        <etymology type="proto-language" source="Proto-Indo-European">
            <form lang="en"><text>*testos</text></form>
            <gloss lang="en"><text>original meaning</text></gloss>
        </etymology>
        <sense id="s1">
            <grammatical-info value="noun" />
            <definition><form lang="en"><text>a test definition</text></form></definition>
        </sense>
        <relation type="synonym" ref="other_id_456" />
        <variant>
            <form lang="en"><text>test variant</text></form>
        </variant>
    </entry>'''

    parser = LIFTParser(validate=True)
    entry = parser.parse_entry(test_lift)
    assert isinstance(entry, Entry)
    assert entry.date_created is not None, f"date_created is None: {entry}"
    assert entry.date_modified is not None, f"date_modified is None: {entry}"
    assert isinstance(entry.date_created, str), f"date_created is not a string: {entry.date_created}"
    assert isinstance(entry.date_modified, str), f"date_modified is not a string: {entry.date_modified}"
    parsed_created = datetime.fromisoformat(entry.date_created.replace('Z', '+00:00'))
    parsed_modified = datetime.fromisoformat(entry.date_modified.replace('Z', '+00:00'))
    assert parsed_created == datetime(2023, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    assert parsed_modified == datetime(2023, 2, 20, 15, 30, 0, tzinfo=timezone.utc)