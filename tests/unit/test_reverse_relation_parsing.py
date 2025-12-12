"""Test parsing of reverse relation fields from LIFT ranges."""
import pytest
from app.parsers.lift_parser import LIFTRangesParser


@pytest.mark.skip_et_mock
def test_parse_reverse_relation_fields():
    """Test that reverse-label and reverse-abbrev fields are parsed correctly."""
    # Use the actual file since it has the correct structure
    parser = LIFTRangesParser()
    ranges = parser.parse_file('sample-lift-file/sample-lift-file.lift-ranges')
    
    # Verify the range was parsed
    assert 'lexical-relation' in ranges
    
    # Get the abbreviation relation element
    lex_rel_range = ranges['lexical-relation']
    assert 'values' in lex_rel_range
    assert len(lex_rel_range['values']) > 0
    
    # Find the skrot element
    skrot_elem = None
    for val in lex_rel_range['values']:
        if val.get('id') == 'skrot':
            skrot_elem = val
            break
    
    assert skrot_elem is not None, "skrot element not found"
    
    # Verify reverse-label was parsed
    assert 'reverse_labels' in skrot_elem
    assert 'en' in skrot_elem['reverse_labels']
    assert skrot_elem['reverse_labels']['en'] == 'expansion'
    assert 'pl' in skrot_elem['reverse_labels']
    assert skrot_elem['reverse_labels']['pl'] == 'rozwiniecie'
    
    # Verify reverse-abbrev was parsed
    assert 'reverse_abbrevs' in skrot_elem
    assert 'en' in skrot_elem['reverse_abbrevs']
    assert skrot_elem['reverse_abbrevs']['en'] == 'abbr. from'
    assert 'pl' in skrot_elem['reverse_abbrevs']
    assert skrot_elem['reverse_abbrevs']['pl'] == 'skr. od'


@pytest.mark.skip_et_mock
def test_parse_symmetric_relation_no_reverse():
    """Test that symmetric relations without reverse fields don't break parsing."""
    parser = LIFTRangesParser()
    ranges = parser.parse_file('sample-lift-file/sample-lift-file.lift-ranges')
    
    # Verify the range was parsed
    assert 'lexical-relation' in ranges
    
    # Get a symmetric relation element (e.g., synonym)
    synonym_elem = None
    for val in ranges['lexical-relation']['values']:
        if val.get('id') == 'synonym':
            synonym_elem = val
            break
    
    # If synonym doesn't exist, just verify any element has the keys
    if synonym_elem is None:
        synonym_elem = ranges['lexical-relation']['values'][0]
    
    # Verify reverse fields exist but may be empty
    assert 'reverse_labels' in synonym_elem
    assert 'reverse_abbrevs' in synonym_elem


if __name__ == "__main__":
    print("Testing reverse relation field parsing...")
    test_parse_reverse_relation_fields()
    print("✓ Reverse relation fields parsed correctly")
    
    print("Testing symmetric relation without reverse fields...")
    test_parse_symmetric_relation_no_reverse()
    print("✓ Symmetric relations work correctly")
    
    print("\nAll tests passed!")
