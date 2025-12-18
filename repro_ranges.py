import xml.etree.ElementTree as ET
from app.parsers.lift_parser import LIFTRangesParser

ranges_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift-ranges>
    <range id="grammatical-info">
        <range-element id="Noun" label="Noun" abbrev="n"/>
        <range-element id="Verb" label="Verb" abbrev="v"/>
        <range-element id="Adjective" label="Adjective" abbrev="adj"/>
    </range>
    <range id="variant-type">
        <range-element id="spelling" label="Spelling Variant"/>
        <range-element id="dialectal" label="Dialectal Variant"/>
    </range>
</lift-ranges>'''

parser = LIFTRangesParser()
parsed = parser.parse_string(ranges_xml)

print(f"Parsed keys: {list(parsed.keys())}")
if 'variant-type' in parsed:
    print(f"Variant-type values: {parsed['variant-type'].get('values')}")
    for v in parsed['variant-type'].get('values', []):
        print(f"  Element: {v['id']}, value: {v['value']}, labels: {v['labels']}")
