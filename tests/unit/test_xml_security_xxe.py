import pytest


from app.services.validation_engine import SchematronValidator, ValidationPriority


def test_rejects_doctype_entity_payloads() -> None:
    validator = SchematronValidator()

    # Provide a minimal entry-like XML payload with DOCTYPE + ENTITY.
    # We are not asserting schema result; we assert security rejection.
    payload = """<?xml version="1.0"?>
    <!DOCTYPE entry [
      <!ENTITY xxe SYSTEM "file:///etc/passwd">
    ]>
    <entry id="e1">
      <lexical-unit>
        <form lang="en"><text>&xxe;</text></form>
      </lexical-unit>
      <sense id="s1">
        <definition>
          <form lang="en"><text>def</text></form>
        </definition>
        <gloss lang="en"><text>g</text></gloss>
      </sense>
    </entry>
    """

    result = validator.validate_xml(payload)

    assert result.is_valid is False
    assert len(result.errors) >= 1
    assert result.errors[0].rule_id == "XML_SECURITY_ERROR"
    assert result.errors[0].priority == ValidationPriority.CRITICAL
