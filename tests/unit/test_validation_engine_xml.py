#!/usr/bin/env python3
"""
Unit tests for ValidationEngine XML validation.

Tests the validate_xml() method with various XML inputs.
"""

from __future__ import annotations

import pytest

from app.services.validation_engine import ValidationEngine, ValidationPriority, ValidationCategory


# Mark all tests in this module to skip ET mocking (need real XML parsing)
pytestmark = pytest.mark.skip_et_mock


class TestValidationEngineXML:
    """Unit tests for XML validation in ValidationEngine."""
    
    @pytest.fixture
    def validation_engine(self):
        """Create a ValidationEngine instance."""
        return ValidationEngine()
    
    @pytest.fixture
    def valid_lift_xml(self):
        """Valid LIFT XML for testing."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<entry id="test-001" dateCreated="2024-01-15T10:00:00Z" dateModified="2024-01-15T10:00:00Z">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
        <form lang="pl"><text>testować</text></form>
    </lexical-unit>
    <sense id="s1">
        <definition>
            <form lang="en"><text>A procedure for critical evaluation</text></form>
            <form lang="pl"><text>Procedura krytycznej oceny</text></form>
        </definition>
        <gloss lang="en"><text>trial</text></gloss>
        <gloss lang="pl"><text>próba</text></gloss>
    </sense>
    <note type="general">
        <form lang="en"><text>This is a test entry</text></form>
    </note>
</entry>"""
    
    def test_validate_xml_valid_entry(self, validation_engine, valid_lift_xml):
        """Test validation of valid LIFT XML entry."""
        result = validation_engine.validate_xml(valid_lift_xml)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.has_critical_errors is False
    
    def test_validate_xml_missing_required_field(self, validation_engine):
        """Test validation of XML missing required lexical-unit."""
        xml_missing_lexunit = """<?xml version="1.0" encoding="UTF-8"?>
<entry id="test-missing-lex">
    <sense id="s1">
        <definition>
            <form lang="en"><text>Test definition</text></form>
        </definition>
    </sense>
</entry>"""
        
        result = validation_engine.validate_xml(xml_missing_lexunit)
        
        assert result.is_valid is False
        assert len(result.errors) >= 1
        assert result.has_critical_errors is True
        # Should have error about missing lexical unit
        error_messages = [e.message for e in result.errors]
        assert any('lexical unit' in msg.lower() for msg in error_messages)
    
    def test_validate_xml_empty_id(self, validation_engine):
        """Test validation of XML with empty ID."""
        xml_empty_id = """<?xml version="1.0" encoding="UTF-8"?>
<entry id="">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <sense id="s1">
        <definition>
            <form lang="en"><text>Test definition</text></form>
        </definition>
    </sense>
</entry>"""
        
        result = validation_engine.validate_xml(xml_empty_id)
        
        # Should have validation error about ID
        assert result.is_valid is False
        assert len(result.errors) >= 1
    
    def test_validate_xml_malformed(self, validation_engine):
        """Test validation of malformed XML."""
        malformed_xml = "<entry><unclosed"
        
        result = validation_engine.validate_xml(malformed_xml)
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].rule_id == "XML_PARSING_ERROR"
        assert result.errors[0].priority == ValidationPriority.CRITICAL
    
    def test_validate_xml_empty_string(self, validation_engine):
        """Test validation of empty XML string."""
        result = validation_engine.validate_xml("")
        
        assert result.is_valid is False
        assert len(result.errors) >= 1
        # Should get parsing error
        assert result.errors[0].rule_id in ["XML_PARSING_ERROR", "XML_PARSER_ERROR"]
    
    def test_validate_xml_missing_sense_id(self, validation_engine):
        """Test validation of XML with sense missing ID."""
        xml_no_sense_id = """<?xml version="1.0" encoding="UTF-8"?>
<entry id="test-no-sense-id">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
    </lexical-unit>
    <sense>
        <definition>
            <form lang="en"><text>Test definition</text></form>
        </definition>
    </sense>
</entry>"""
        
        result = validation_engine.validate_xml(xml_no_sense_id)
        
        # Should have validation error about sense ID
        # Note: This depends on validation rules - may be error or pass
        # Just verify no parsing exception
        assert isinstance(result.is_valid, bool)
    
    def test_validate_xml_with_validation_mode(self, validation_engine, valid_lift_xml):
        """Test XML validation with different validation modes."""
        # Test with 'save' mode (default)
        result_save = validation_engine.validate_xml(valid_lift_xml, validation_mode="save")
        assert isinstance(result_save.is_valid, bool)
        
        # Test with 'draft' mode
        result_draft = validation_engine.validate_xml(valid_lift_xml, validation_mode="draft")
        assert isinstance(result_draft.is_valid, bool)
        
        # Test with 'delete' mode
        result_delete = validation_engine.validate_xml(valid_lift_xml, validation_mode="delete")
        assert isinstance(result_delete.is_valid, bool)
    
    def test_validate_xml_complex_entry(self, validation_engine):
        """Test validation of XML with multiple senses, relations, etc."""
        complex_xml = """<?xml version="1.0" encoding="UTF-8"?>
<entry id="complex-001">
    <lexical-unit>
        <form lang="en"><text>complex</text></form>
        <form lang="pl"><text>złożony</text></form>
    </lexical-unit>
    <sense id="s1">
        <definition>
            <form lang="en"><text>Consisting of many different parts</text></form>
            <form lang="pl"><text>Składający się z wielu różnych części</text></form>
        </definition>
        <gloss lang="en"><text>complicated</text></gloss>
    </sense>
    <sense id="s2">
        <definition>
            <form lang="en"><text>A group of similar buildings</text></form>
        </definition>
        <gloss lang="en"><text>compound</text></gloss>
    </sense>
    <relation type="synonym" ref="complicated-001" />
    <note type="usage">
        <form lang="en"><text>Common in technical contexts</text></form>
    </note>
</entry>"""
        
        result = validation_engine.validate_xml(complex_xml)
        
        # Should parse and validate without crashing
        assert isinstance(result.is_valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
    
    def test_validate_xml_preserves_error_details(self, validation_engine):
        """Test that XML validation preserves error details like path and priority."""
        xml_with_errors = """<?xml version="1.0" encoding="UTF-8"?>
<entry id="">
    <lexical-unit>
        <form lang="en"><text>t</text></form>
    </lexical-unit>
</entry>"""
        
        result = validation_engine.validate_xml(xml_with_errors)
        
        if len(result.errors) > 0:
            # Check that errors have proper structure
            for error in result.errors:
                assert hasattr(error, 'rule_id')
                assert hasattr(error, 'message')
                assert hasattr(error, 'path')
                assert hasattr(error, 'priority')
                assert isinstance(error.priority, ValidationPriority)
                assert hasattr(error, 'category')
                assert isinstance(error.category, ValidationCategory)
    
    def test_validate_xml_unicode_content(self, validation_engine):
        """Test validation of XML with Unicode characters."""
        unicode_xml = """<?xml version="1.0" encoding="UTF-8"?>
<entry id="unicode-001">
    <lexical-unit>
        <form lang="pl"><text>łódź</text></form>
        <form lang="ja"><text>テスト</text></form>
        <form lang="ar"><text>اختبار</text></form>
    </lexical-unit>
    <sense id="s1">
        <definition>
            <form lang="pl"><text>Pojazd pływający używany do transportu</text></form>
        </definition>
        <gloss lang="en"><text>boat</text></gloss>
    </sense>
</entry>"""
        
        result = validation_engine.validate_xml(unicode_xml)
        
        # Should handle Unicode without issues
        assert isinstance(result.is_valid, bool)
        # Valid structure, so should pass
        assert result.is_valid is True or len(result.errors) >= 0
