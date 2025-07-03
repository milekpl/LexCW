"""
Script to verify the content of lift_parser.py and add the missing methods.
"""

import os
import re

# Define the path to the file
lift_parser_path = r"D:\Dokumenty\slownik-wielki\flask-app\app\parsers\lift_parser.py"

# Read the entire file
with open(lift_parser_path, 'r', encoding='utf-8') as file:
    content = file.read()

# Check if the methods already exist
extract_variant_exists = 'def extract_variant_types_from_traits' in content
extract_language_exists = 'def extract_language_codes_from_file' in content

print(f"extract_variant_types_from_traits exists: {extract_variant_exists}")
print(f"extract_language_codes_from_file exists: {extract_language_exists}")

# If methods don't exist, add them to the file before the LIFTRangesParser class
if not extract_variant_exists or not extract_language_exists:
    # Find the position to insert the methods (before LIFTRangesParser class)
    match = re.search(r'class LIFTRangesParser:', content)
    if match:
        insert_position = match.start()
        
        # Prepare the methods to add
        methods_text = '''
    def extract_variant_types_from_traits(self, xml_string: str) -> List[Dict[str, Any]]:
        """
        Extract all unique variant types from <trait> elements in variant forms.
        
        This extracts the 'type' traits from all variant elements in the LIFT file,
        which represent the actual variant types used in the document rather than
        using the standard ranges.
        
        Args:
            xml_string: LIFT XML string
            
        Returns:
            List of variant type objects in the format expected by the range API
        """
        self.logger.info("Extracting variant types from traits in LIFT file")
        try:
            root = ET.fromstring(xml_string)
            # Find all variant elements and extract their types
            variant_types: set[str] = set()
            
            # Use both namespaced and non-namespaced XPath for compatibility
            variant_elems = self._find_elements(root, './/lift:variant', './/variant')
            
            for variant_elem in variant_elems:
                # Extract the type attribute directly from variant element
                variant_type = variant_elem.get('type')
                if variant_type and variant_type.strip():
                    variant_types.add(variant_type.strip())
                
                # Also look for trait elements that might indicate variant types
                for trait_elem in self._find_elements(variant_elem, './/lift:trait', './/trait'):
                    trait_name = trait_elem.get('name')
                    trait_value = trait_elem.get('value')
                    if trait_name == 'type' and trait_value and trait_value.strip():
                        variant_types.add(trait_value.strip())
            
            # Format the results as expected by the ranges API
            result: List[Dict[str, Any]] = []
            for variant_type in sorted(variant_types):
                # Create a standardized structure for each variant type
                result.append({
                    'id': variant_type,
                    'value': variant_type,
                    'abbrev': variant_type[:3].lower(),  # Simple abbreviation
                    'description': {'en': f'{variant_type} variant'}
                })
                
            self.logger.info(f"Extracted {len(result)} variant types from LIFT file")
            return result
            
        except Exception as e:
            self.logger.error(f"Error extracting variant types from LIFT: {e}", exc_info=True)
            return []
            
    def extract_language_codes_from_file(self, xml_string: str) -> List[str]:
        """
        Extract all unique language codes used in the LIFT file.
        
        This scans all elements with 'lang' attributes to find the actual 
        language codes used in the project, rather than using a predefined list.
        
        Args:
            xml_string: LIFT XML string
            
        Returns:
            List of unique language codes found in the LIFT file
        """
        self.logger.info("Extracting language codes from LIFT file")
        try:
            root = ET.fromstring(xml_string)
            # Find all elements with lang attributes
            language_codes: set[str] = set()
            
            # Function to collect lang attributes from any element
            def collect_lang_attrs(element: ET.Element) -> None:
                lang = element.get('lang')
                if lang and lang.strip():
                    language_codes.add(lang.strip())
                for child in element:
                    collect_lang_attrs(child)
            
            # Traverse the XML tree
            collect_lang_attrs(root)
            
            # Always include seh-fonipa for IPA pronunciations if not already found
            if 'seh-fonipa' not in language_codes:
                language_codes.add('seh-fonipa')
                
            self.logger.info(f"Extracted {len(language_codes)} language codes from LIFT file")
            return sorted(list(language_codes))
            
        except Exception as e:
            self.logger.error(f"Error extracting language codes from LIFT: {e}", exc_info=True)
            # Return a minimal default set
            return ['seh-fonipa']
'''
        
        # Insert the methods
        new_content = content[:insert_position] + methods_text + content[insert_position:]
        
        # Write the updated content back to the file
        with open(lift_parser_path, 'w', encoding='utf-8') as file:
            file.write(new_content)
        
        print("Methods added successfully!")
    else:
        print("Could not find LIFTRangesParser class in the file")
else:
    print("Methods already exist in the file")
