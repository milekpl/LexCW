from __future__ import annotations

import pytest

from app.models.entry import Entry
from app.parsers.lift_parser import LIFTParser
from app.utils.exceptions import ValidationError

# LIFT entry with multiple senses and nested data
COMPLEX_LIFT_ENTRY_2 = '''
<entry id="test_id_002">
    <lexical-unit>
        <form lang="en"><text>run</text></form>
        <form lang="es"><text>correr</text></form>
    </lexical-unit>
    <sense id="sense_1">
        <grammatical-info value="verb" />
        <definition><form lang="en"><text>to move swiftly on foot</text></form></definition>
        <example>
            <form lang="en"><text>He can run very fast.</text></form>
            <translation><form lang="es"><text>Él puede correr muy rápido.</text></form></translation>
        </example>
    </sense>
    <sense id="sense_2">
        <grammatical-info value="verb" />
        <definition><form lang="en"><text>to operate or manage</text></form></definition>
        <relation type="hypernym" ref="manage_id_001" />
    </sense>
</entry>
'''

# LIFT entry with missing optional fields
MINIMAL_LIFT_ENTRY = '''
<entry id="test_id_003">
    <lexical-unit>
        <form lang="en"><text>minimal</text></form>
    </lexical-unit>
</entry>
'''

@pytest.fixture
def lift_parser() -> LIFTParser:
    '''Fixture to provide a LIFTParser instance.'''
    return LIFTParser()

def test_parse_entry_with_multiple_senses(lift_parser: LIFTParser):
    '''
    Tests that the LIFT parser correctly handles an entry with multiple senses,
    including nested examples and relations within a sense.
    '''
    # Act
    entry: Entry = lift_parser.parse_entry(COMPLEX_LIFT_ENTRY_2)

    # Assert
    assert entry is not None
    assert entry.id == "test_id_002"
    assert len(entry.senses) == 2

    # Check first sense
    sense1 = entry.senses[0]
    assert sense1.id == "sense_1"
    assert sense1.grammatical_info == "verb"
    assert sense1.definitions.get("en") == "to move swiftly on foot"
    assert len(sense1.examples) == 1
    example1 = sense1.examples[0]
    assert example1.get("form", {}).get("en") == "He can run very fast."
    assert example1.get("translations", {}).get("es") == "Él puede correr muy rápido."

    # Check second sense
    sense2 = entry.senses[1]
    assert sense2.id == "sense_2"
    assert sense2.grammatical_info == "verb"
    assert len(sense2.relations) == 1
    relation = sense2.relations[0]
    assert relation.get("type") == "hypernym"
    assert relation.get("ref") == "manage_id_001"

def test_parse_minimal_entry(lift_parser: LIFTParser):
    '''
    Tests that the LIFT parser rejects minimal entries that don't meet validation requirements.
    '''
    # Act & Assert - should raise ValidationError due to missing senses
    with pytest.raises(ValidationError) as exc_info:
        lift_parser.parse_entry(MINIMAL_LIFT_ENTRY)
    
    # Verify the specific validation error
    assert "At least one sense is required per entry" in str(exc_info.value)
