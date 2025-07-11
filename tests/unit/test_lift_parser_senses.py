from __future__ import annotations
import pytest
from app.parsers.lift_parser import LIFTParser

# Mark all tests in this module to skip ET mocking since they need real XML parsing
pytestmark = pytest.mark.skip_et_mock

def test_parse_entry_with_single_sense():
    """
    Ensure that parsing a LIFT entry with only one <sense> element results in exactly one sense in the parsed Entry object.
    """
    xml = '''
    <entry id="single_sense_entry">
        <lexical-unit>
            <form lang="en"><text>word</text></form>
        </lexical-unit>
        <sense>
            <definition><form lang="en"><text>definition</text></form></definition>
        </sense>
    </entry>
    '''
    parser = LIFTParser()
    entry = parser.parse_entry(xml)
    assert entry is not None
    assert hasattr(entry, 'senses')
    assert isinstance(entry.senses, list)
    assert len(entry.senses) == 1, f"Expected 1 sense, got {len(entry.senses)}"
    sense = entry.senses[0]
    assert hasattr(sense, 'definitions') or hasattr(sense, 'definition')
    # Accept both plural and singular for compatibility
    defs = getattr(sense, 'definitions', None) or getattr(sense, 'definition', None)
    assert 'en' in defs
    assert defs['en']['text'] == 'definition'
