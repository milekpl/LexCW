"""
Script to test the LIFTParser class and its methods.
"""

import sys
import os

# Add the parent directory to the path so we can import from the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.parsers.lift_parser import LIFTParser

def test_lift_parser():
    parser = LIFTParser()
    
    # Check if the methods exist
    print(f"Has extract_variant_types_from_traits: {hasattr(parser, 'extract_variant_types_from_traits')}")
    print(f"Has extract_language_codes_from_file: {hasattr(parser, 'extract_language_codes_from_file')}")
    
    # Sample LIFT XML for testing
    sample_xml = '''<?xml version="1.0" encoding="UTF-8" ?>
    <lift producer="SIL.FLEx 9.1.25.877" version="0.13">
    <entry id="test1">
        <lexical-unit>
            <form lang="en"><text>test</text></form>
        </lexical-unit>
        <variant type="dialectal">
            <form lang="en"><text>test variant</text></form>
            <trait name="type" value="dialectal"/>
        </variant>
        <pronunciation>
            <form lang="seh-fonipa"><text>test</text></form>
        </pronunciation>
    </entry>
    </lift>
    '''
    
    # Try to call the methods
    if hasattr(parser, 'extract_variant_types_from_traits'):
        variant_types = parser.extract_variant_types_from_traits(sample_xml)
        print(f"Variant types: {variant_types}")
    else:
        print("Method extract_variant_types_from_traits not found")
        
    if hasattr(parser, 'extract_language_codes_from_file'):
        language_codes = parser.extract_language_codes_from_file(sample_xml)
        print(f"Language codes: {language_codes}")
    else:
        print("Method extract_language_codes_from_file not found")
        
if __name__ == "__main__":
    test_lift_parser()
