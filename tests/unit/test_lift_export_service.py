from __future__ import annotations
import xml.etree.ElementTree as ET
from app.services.lift_export_service import LIFTExportService


class DummyDB:
    def __init__(self):
        self.database = 'testdb'


class EmptyRangesService:
    def get_all_ranges(self):
        return {}


def test_export_ranges_generates_defaults(tmp_path):
    db = DummyDB()
    rs = EmptyRangesService()
    svc = LIFTExportService(db, rs)

    out = tmp_path / "ranges.xml"
    svc.export_ranges_file(1, str(out))

    assert out.exists()
    tree = ET.parse(str(out))
    root = tree.getroot()
    # Ensure at least one range element exists
    ranges = root.findall('range')
    assert len(ranges) > 0
    # Ensure at least one range-element exists somewhere
    elems = root.findall('.//range-element')
    assert len(elems) > 0
