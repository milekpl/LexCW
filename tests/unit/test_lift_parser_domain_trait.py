from __future__ import annotations

import pytest

from app.parsers.lift_parser import LIFTParser


pytestmark = pytest.mark.skip_et_mock


def test_parse_entry_level_semantic_domain_trait() -> None:
    """Test that LIFTParser correctly parses entry-level semantic domain traits."""
    xml = '''<entry id="e1">
        <lexical-unit><form lang="en"><text>test</text></form></lexical-unit>
        <trait name="semantic-domain-ddp4" value="informatyka"/>
    </entry>'''

    parser = LIFTParser(validate=False)
    entries = parser.parse_string(xml)
    assert entries and entries[0]
    entry = entries[0]
    print('ENTRY TRAITS:', entry.traits)
    assert 'semantic-domain-ddp4' in entry.traits
    assert entry.traits['semantic-domain-ddp4'] == 'informatyka'
