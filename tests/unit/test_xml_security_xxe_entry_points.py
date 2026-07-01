import pytest


from app.parsers.lift_parser import LIFTParser
from app.parsers.enhanced_lift_parser import EnhancedLiftParser
from app.services.xml_entry_service import XMLEntryService, InvalidXMLError


XXE_PAYLOAD = """<?xml version="1.0"?>
<!DOCTYPE entry [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<entry id="e1" xmlns="http://fieldworks.sil.org/schemas/lift/0.13">
  <lexical-unit>
    <form lang="en"><text>&xxe;</text></form>
  </lexical-unit>
  <sense id="s1">
    <definition><form lang="en"><text>def</text></form></definition>
    <gloss lang="en"><text>g</text></gloss>
  </sense>
</entry>
"""


def test_rejects_xxe_in_lift_parser() -> None:
    parser = LIFTParser(validate=False)
    with pytest.raises(ValueError):
        parser.parse_string(XXE_PAYLOAD)


def test_rejects_xxe_in_enhanced_lift_parser() -> None:
    parser = EnhancedLiftParser(validate=False)
    with pytest.raises(ValueError):
        parser.parse_string(XXE_PAYLOAD)


def test_rejects_xxe_in_xml_entry_service() -> None:
    # Service constructor uses BaseXClient session lazily; validation happens
    # before any DB call.
    service = XMLEntryService()
    with pytest.raises(InvalidXMLError):
        service._validate_lift_xml(XXE_PAYLOAD)
