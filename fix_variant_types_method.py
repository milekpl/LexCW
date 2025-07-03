"""
Script to add the extract_variant_types_from_traits method to LIFTParser.
"""

import re

# Define the path to the file
lift_parser_path = r"D:\Dokumenty\slownik-wielki\flask-app\app\parsers\lift_parser.py"

# Read the entire file
with open(lift_parser_path, 'r', encoding='utf-8') as file:
    content = file.read()

# Find the position of the extract_language_codes_from_file method
match = re.search(r'def extract_language_codes_from_file', content)
if match:
    pos = match.start()
    
    # Look for the position to insert the variant types method (before the language codes method)
    # Find the beginning of the method definition line
    line_start = content.rfind('\n', 0, pos) + 1
    indent = ' ' * (pos - line_start)
    
    # Prepare the method to add
    method_text = f'''
{indent}def extract_variant_types_from_traits(self, xml_string: str) -> List[Dict[str, Any]]:
{indent}    """
{indent}    Extract all unique variant types from <trait> elements in variant forms.
{indent}    
{indent}    This extracts the 'type' traits from all variant elements in the LIFT file,
{indent}    which represent the actual variant types used in the document rather than
{indent}    using the standard ranges.
{indent}    
{indent}    Args:
{indent}        xml_string: LIFT XML string
{indent}        
{indent}    Returns:
{indent}        List of variant type objects in the format expected by the range API
{indent}    """
{indent}    self.logger.info("Extracting variant types from traits in LIFT file")
{indent}    try:
{indent}        root = ET.fromstring(xml_string)
{indent}        # Find all variant elements and extract their types
{indent}        variant_types: set[str] = set()
{indent}        
{indent}        # Use both namespaced and non-namespaced XPath for compatibility
{indent}        variant_elems = self._find_elements(root, './/lift:variant', './/variant')
{indent}        
{indent}        for variant_elem in variant_elems:
{indent}            # Extract the type attribute directly from variant element
{indent}            variant_type = variant_elem.get('type')
{indent}            if variant_type and variant_type.strip():
{indent}                variant_types.add(variant_type.strip())
{indent}            
{indent}            # Also look for trait elements that might indicate variant types
{indent}            for trait_elem in self._find_elements(variant_elem, './/lift:trait', './/trait'):
{indent}                trait_name = trait_elem.get('name')
{indent}                trait_value = trait_elem.get('value')
{indent}                if trait_name == 'type' and trait_value and trait_value.strip():
{indent}                    variant_types.add(trait_value.strip())
{indent}        
{indent}        # Format the results as expected by the ranges API
{indent}        result: List[Dict[str, Any]] = []
{indent}        for variant_type in sorted(variant_types):
{indent}            # Create a standardized structure for each variant type
{indent}            result.append({{
{indent}                'id': variant_type,
{indent}                'value': variant_type,
{indent}                'abbrev': variant_type[:3].lower(),  # Simple abbreviation
{indent}                'description': {{'en': f'{{variant_type}} variant'}}
{indent}            }})
{indent}            
{indent}        self.logger.info(f"Extracted {{len(result)}} variant types from LIFT file")
{indent}        return result
{indent}        
{indent}    except Exception as e:
{indent}        self.logger.error(f"Error extracting variant types from LIFT: {{e}}", exc_info=True)
{indent}        return []
{indent}        
'''
    
    # Insert the method before the language codes method
    new_content = content[:line_start] + method_text + content[line_start:]
    
    # Write the updated content back to the file
    with open(lift_parser_path, 'w', encoding='utf-8') as file:
        file.write(new_content)
    
    print("Method added successfully!")
else:
    print("Could not find extract_language_codes_from_file method in the file")
