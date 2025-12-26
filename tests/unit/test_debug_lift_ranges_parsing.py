import pytest
from app.parsers.lift_parser import LIFTRangesParser


@pytest.mark.skip_et_mock
def test_parse_sample_ranges_file():
    parser = LIFTRangesParser()
    ranges = parser.parse_file('sample-lift-file/sample-lift-file.lift-ranges')
    print('Parsed ranges:', sorted(list(ranges.keys()))[:50])
    assert 'domain-type' in ranges, "domain-type should be present in sample ranges"
    assert 'usage-type' in ranges, "usage-type should be present in sample ranges"
