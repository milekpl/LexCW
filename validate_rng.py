
import sys
from lxml import etree

def validate_rng(rng_file, xml_file):
    try:
        rng_doc = etree.parse(rng_file)
        relaxng = etree.RelaxNG(rng_doc)
        
        xml_doc = etree.parse(xml_file)
        
        if relaxng.validate(xml_doc):
            print(f"Validation successful: '{xml_file}' is valid against '{rng_file}'.")
            return True
        else:
            print(f"Validation failed: '{xml_file}' is not valid against '{rng_file}'.")
            for error in relaxng.error_log:
                print(f"  - {error}")
            return False
    except etree.XMLSyntaxError as e:
        print(f"XML Syntax Error: Could not parse '{e.filename}': {e.msg}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python validate_rng.py <rng_file> <xml_file>")
        sys.exit(1)
        
    rng_file = sys.argv[1]
    xml_file = sys.argv[2]
    
    if not validate_rng(rng_file, xml_file):
        sys.exit(1)
