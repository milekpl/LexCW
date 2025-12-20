"""Minimal test to reproduce the XML generation issue."""
import pytest

def test_minimal_reproduction():
    """Minimal test to reproduce the XML generation issue."""
    from app.models.entry import Entry, Relation
    from app.parsers.lift_parser import LIFTParser

    # Create simple entry with relation + traits
    entry = Entry(id="test", lexical_unit={"en": "test"})
    relation = Relation(type="synonym", ref="test_ref")
    relation.traits = {"variant-type": "test_value"}
    entry.relations = [relation]

    # Generate XML
    parser = LIFTParser(validate=False)
    xml_output = parser.generate_lift_string([entry])

    print(f"Generated XML:\n{xml_output}")
    assert 'type="synonym"' in xml_output, "Relation should be in XML"
    assert 'name="variant-type"' in xml_output, "Traits should be in XML"


if __name__ == "__main__":
    test_minimal_reproduction()