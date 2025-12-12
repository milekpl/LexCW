from app.parsers.lift_parser import LIFTRangesParser
import xml.etree.ElementTree as ET

# Parse the file
parser = LIFTRangesParser()
root = ET.parse('sample-lift-file/sample-lift-file.lift-ranges').getroot()

# Find skrot element
ranges = root.findall('.//range[@id="lexical-relation"]')
elems = ranges[0].findall('.//range-element[@id="skrot"]')
skrot_elem = elems[0]

print("Testing _find_elements method:")
print(f"Element tag: {skrot_elem.tag}")
print(f"Element id: {skrot_elem.get('id')}")

# Test the parser's _find_elements method
fields_ns = parser._find_elements(skrot_elem, './lift:field', './field')
print(f"\nFields found by _find_elements: {len(fields_ns)}")

# Also test direct findall
fields_direct = skrot_elem.findall('./field')
print(f"Fields found by direct findall('./field'): {len(fields_direct)}")

# Check if namespace is the issue
fields_with_ns = skrot_elem.findall('./lift:field', parser.NSMAP)
print(f"Fields found with namespace: {len(fields_with_ns)}")

# List all direct children
print(f"\nAll direct children of skrot:")
for child in skrot_elem:
    print(f"  {child.tag}: {child.get('type', 'no type')}")
