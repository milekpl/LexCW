from __future__ import annotations

import pytest

from app.models.entry import Entry
from app.parsers.lift_parser import LIFTParser

# Mark all tests in this module to skip ET mocking since they need real XML parsing
pytestmark = pytest.mark.skip_et_mock

# Sample LIFT XML entry with complex relations, etymologies, variants, and date attributes
COMPLEX_LIFT_ENTRY = """
<entry id="test_id_123" dateCreated="2020-01-01T12:00:00Z" dateModified="2021-02-02T13:30:00Z">
    <lexical-unit>
        <form lang="en"><text>test entry</text></form>
    </lexical-unit>
    <etymology type="proto-language" source="Proto-Indo-European">
        <form lang="en"><text>*testos</text></form>
        <gloss lang="en"><text>original meaning</text></gloss>
    </etymology>
    <sense>
        <grammatical-info value="noun" />
        <definition><form lang="en"><text>a test definition</text></form></definition>
    </sense>
    <relation type="synonym" ref="other_id_456" />
    <variant>
        <form lang="en"><text>test variant</text></form>
    </variant>
</entry>
"""


@pytest.fixture
def lift_parser() -> LIFTParser:
    """Fixture to provide a LIFTParser instance."""
    return LIFTParser()



def test_parse_entry_with_complex_structures(lift_parser: LIFTParser):
    """
    Tests that the LIFT parser correctly handles complex entry structures,
    including relations, etymologies, and variants.
    """
    # Act
    entries = lift_parser.parse_string(COMPLEX_LIFT_ENTRY)
    assert len(entries) == 1
    entry = entries[0]

    # Assert
    assert entry is not None

    # Check dateCreated and dateModified
    assert entry.date_created == "2020-01-01T12:00:00Z"
    assert entry.date_modified == "2021-02-02T13:30:00Z"

    # Check for etymology
    assert len(entry.etymologies) == 1
    etymology = entry.etymologies[0]
    assert etymology.type == "proto-language"
    assert etymology.source == "Proto-Indo-European"
    assert etymology.form["en"] == "*testos"
    assert etymology.gloss["en"] == "original meaning"

    # Check for relations
    assert len(entry.relations) == 1
    relation = entry.relations[0]
    assert relation.type == "synonym"
    assert relation.ref == "other_id_456"

    # Check for variants
    assert len(entry.variants) == 1
    variant = entry.variants[0]
    assert variant.form["en"] == "test variant"

