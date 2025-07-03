"""
Test script for pronunciation extraction from LIFT XML.

This script tests the LIFT parser's ability to extract pronunciations
from the XML format used in the sample LIFT file.
"""

import sys
import os
from pathlib import Path
import xml.etree.ElementTree as ET
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add project root to path for imports
project_root = str(Path(__file__).parent)
sys.path.insert(0, project_root)

from app.parsers.lift_parser import LIFTParser

def test_extract_pronunciation():
    """Test extracting pronunciation from a LIFT entry."""
    
    # XML with pronunciation in the format from the sample file
    sample_xml = '''
    <entry dateCreated="2013-03-24T20:24:33Z" dateModified="2014-06-07T11:16:20Z" id="Protestant1_8c895a90-6c91-4257-8ada-528e18d2ba69" guid="8c895a90-6c91-4257-8ada-528e18d2ba69" order="1">
    <lexical-unit>
    <form lang="en"><text>Protestant</text></form>
    </lexical-unit>
    <trait  name="morph-type" value="stem"/>
    <pronunciation>
    <form lang="seh-fonipa"><text>ˈprɒtɪstənt</text></form>
    </pronunciation>
    <sense id="f7c1d012-9485-4755-8e00-5842f6358647">
    <grammatical-info value="Noun">
    </grammatical-info>
    <definition>
    <form lang="pl"><text>protestant(ka)</text></form>
    </definition>
    </sense>
    </entry>
    '''
    
    # Create LIFT parser
    parser = LIFTParser()
    
    # Parse the entry
    try:
        entries = parser.parse_string(sample_xml)
        if entries and len(entries) > 0:
            entry = entries[0]
            logger.info(f"Entry ID: {entry.id}")
            logger.info(f"Lexical unit: {entry.lexical_unit}")
            logger.info(f"Pronunciations: {entry.pronunciations}")
            
            # Check if the pronunciation was extracted
            if 'seh-fonipa' in entry.pronunciations:
                logger.info(f"Successfully extracted pronunciation: {entry.pronunciations['seh-fonipa']}")
                assert entry.pronunciations['seh-fonipa'] == "ˈprɒtɪstənt"
                print("✅ Pronunciation extraction test passed!")
            else:
                logger.error("Failed to extract pronunciation: 'seh-fonipa' not found in pronunciations")
                print("❌ Pronunciation extraction test failed!")
        else:
            logger.error("No entries parsed from XML")
            print("❌ Pronunciation extraction test failed!")
    except Exception as e:
        logger.error(f"Error parsing XML: {e}", exc_info=True)
        print("❌ Pronunciation extraction test failed due to error!")

if __name__ == "__main__":
    print("Testing pronunciation extraction from LIFT XML...")
    test_extract_pronunciation()
