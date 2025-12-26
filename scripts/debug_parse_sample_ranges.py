from app.parsers.lift_parser import LIFTRangesParser
parser = LIFTRangesParser()
ranges = parser.parse_file('sample-lift-file/sample-lift-file.lift-ranges')
print('Parsed range count:', len(ranges))
print(sorted(list(ranges.keys()))[:50])
print('domain-type' in ranges)
if 'domain-type' in ranges:
    print('domain-type values:', [v['id'] for v in ranges['domain-type']['values'][:10]])
