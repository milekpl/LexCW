import xml.etree.ElementTree as ET

root = ET.parse('sample-lift-file/sample-lift-file.lift-ranges').getroot()
ranges = root.findall('.//range[@id="lexical-relation"]')
print(f'Found lexical-relation ranges: {len(ranges)}')

elems = ranges[0].findall('.//range-element[@id="skrot"]')
print(f'Found skrot elements: {len(elems)}')

fields = elems[0].findall('./field')
print(f'Fields in skrot (direct children): {len(fields)}')

all_fields = elems[0].findall('.//field')
print(f'All fields in skrot (descendants): {len(all_fields)}')

for f in all_fields:
    print(f'  Field type: {f.get("type")}')
    forms = f.findall('./form')
    print(f'    Forms: {len(forms)}')
