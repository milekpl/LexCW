#!/usr/bin/env python3
"""
Script to fix the LIFTRangesParser to include both 'description' and 'descriptions' fields
for backward compatibility with tests.
"""

import re

def fix_lift_parser():
    """Fix the LIFTRangesParser by adding backward compatibility fields."""
    
    # Read the file
    with open('app/parsers/lift_parser.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Pattern 1: Find the _parse_range_element method and add backward compatibility
    pattern1 = r"(element_data\['descriptions'\] = self\._parse_multilingual_content\(elem, \['description'\]\)\s*\n\n\s*# Parse child elements)"
    
    replacement1 = r"element_data['descriptions'] = self._parse_multilingual_content(elem, ['description'])\n        \n        # Add backward compatibility field for tests\n        element_data['description'] = element_data['descriptions'].copy()\n\n        \1"
    
    # Pattern 2: Find the _parse_range_element_full method and add backward compatibility  
    pattern2 = r"(element_data\['descriptions'\] = self\._parse_multilingual_content\(elem, \['description'\]\)\s*\n\n\s*# Parse abbreviation)"
    
    replacement2 = r"element_data['descriptions'] = self._parse_multilingual_content(elem, ['description'])\n        \n        # Add backward compatibility field for tests\n        element_data['description'] = element_data['descriptions'].copy()\n\n        \1"
    
    # Apply the fixes
    content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)
    content = re.sub(pattern2, replacement2, content, flags=re.MULTILINE)
    
    # Write the updated file
    with open('app/parsers/lift_parser.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Successfully fixed LIFTRangesParser to include backward compatibility fields")

if __name__ == "__main__":
    fix_lift_parser()