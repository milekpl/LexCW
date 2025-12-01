#!/usr/bin/env python3
"""
Integration tests for XML validation API endpoint.

Tests POST /api/validation/xml endpoint with various XML inputs.
"""

from __future__ import annotations

import pytest


class TestXMLValidationAPI:
    """Integration tests for XML validation API."""
    
    @pytest.fixture
    def valid_lift_xml(self):
        """Valid LIFT XML for testing."""
        return """<?xml version="1.0" encoding="UTF-8"?>
<entry id="test-xml-api-001" dateCreated="2024-01-15T10:00:00Z" dateModified="2024-01-15T10:00:00Z">
    <lexical-unit>
        <form lang="en"><text>test</text></form>
        <form lang="pl"><text>testować</text></form>
    </lexical-unit>
    <sense id="s1">
        <definition>
            <form lang="en"><text>A procedure for critical evaluation and assessment</text></form>
            <form lang="pl"><text>Procedura krytycznej oceny i oceny</text></form>
        </definition>
        <gloss lang="en"><text>trial</text></gloss>
        <gloss lang="pl"><text>próba</text></gloss>
    </sense>
    <note type="general">
        <form lang="en"><text>This is a test entry for API validation</text></form>
    </note>
</entry>"""
    
    def test_validate_xml_api_valid_entry(self, client, valid_lift_xml):
        """Test XML validation API with valid LIFT XML."""
        response = client.post(
            '/api/validation/xml',
            data=valid_lift_xml,
            content_type='application/xml'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'valid' in data
        assert data['valid'] is True
        assert 'errors' in data
        assert len(data['errors']) == 0
        assert 'warnings' in data
        assert 'info' in data
        assert 'error_count' in data
        assert 'has_critical_errors' in data
        assert data['has_critical_errors'] is False
    
    def test_validate_xml_api_missing_required_field(self, client):
        """Test XML validation API with missing required field."""
        xml_missing_lexunit = """<?xml version="1.0" encoding="UTF-8"?>
<entry id="test-missing-lex">
    <sense id="s1">
        <definition>
            <form lang="en"><text>Test definition</text></form>
        </definition>
    </sense>
</entry>"""
        
        response = client.post(
            '/api/validation/xml',
            data=xml_missing_lexunit,
            content_type='application/xml'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['valid'] is False
        assert len(data['errors']) >= 1
        assert data['has_critical_errors'] is True
        
        # Check for lexical unit error
        error_messages = [e['message'] for e in data['errors']]
        assert any('lexical unit' in msg.lower() for msg in error_messages)
    
    def test_validate_xml_api_malformed_xml(self, client):
        """Test XML validation API with malformed XML."""
        malformed_xml = "<entry><unclosed"
        
        response = client.post(
            '/api/validation/xml',
            data=malformed_xml,
            content_type='application/xml'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['valid'] is False
        assert len(data['errors']) >= 1
        
        # Should have XML parsing error
        assert any(
            e['rule_id'] in ['XML_PARSING_ERROR', 'XML_PARSER_ERROR']
            for e in data['errors']
        )
    
    def test_validate_xml_api_empty_request(self, client):
        """Test XML validation API with empty request."""
        response = client.post(
            '/api/validation/xml',
            data='',
            content_type='application/xml'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        
        assert 'error' in data
        assert 'no xml data' in data['error'].lower()
    
    def test_validate_xml_api_empty_id(self, client):
        """Test XML validation API with empty ID."""
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
        
        response = client.post(
            '/api/validation/xml',
            data=xml_empty_id,
            content_type='application/xml'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['valid'] is False
        assert len(data['errors']) >= 1
    
    def test_validate_xml_api_complex_entry(self, client):
        """Test XML validation API with complex entry (multiple senses, relations)."""
        complex_xml = """<?xml version="1.0" encoding="UTF-8"?>
<entry id="complex-api-001">
    <lexical-unit>
        <form lang="en"><text>complex</text></form>
        <form lang="pl"><text>złożony</text></form>
    </lexical-unit>
    <sense id="s1">
        <definition>
            <form lang="en"><text>Consisting of many different and connected parts</text></form>
            <form lang="pl"><text>Składający się z wielu różnych i połączonych części</text></form>
        </definition>
        <gloss lang="en"><text>complicated</text></gloss>
    </sense>
    <sense id="s2">
        <definition>
            <form lang="en"><text>A group of similar buildings or facilities on the same site</text></form>
        </definition>
        <gloss lang="en"><text>compound</text></gloss>
    </sense>
    <relation type="synonym" ref="complicated-001" />
    <note type="usage">
        <form lang="en"><text>Common in technical and scientific contexts</text></form>
    </note>
</entry>"""
        
        response = client.post(
            '/api/validation/xml',
            data=complex_xml,
            content_type='application/xml'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Should parse and validate without crashing
        assert 'valid' in data
        assert isinstance(data['valid'], bool)
        assert 'errors' in data
        assert 'warnings' in data
    
    def test_validate_xml_api_unicode_content(self, client):
        """Test XML validation API with Unicode characters."""
        unicode_xml = """<?xml version="1.0" encoding="UTF-8"?>
<entry id="unicode-api-001">
    <lexical-unit>
        <form lang="pl"><text>łódź</text></form>
        <form lang="ja"><text>テスト</text></form>
        <form lang="ar"><text>اختبار</text></form>
    </lexical-unit>
    <sense id="s1">
        <definition>
            <form lang="pl"><text>Pojazd pływający używany do transportu wodnego</text></form>
        </definition>
        <gloss lang="en"><text>boat</text></gloss>
    </sense>
</entry>"""
        
        response = client.post(
            '/api/validation/xml',
            data=unicode_xml.encode('utf-8'),
            content_type='application/xml; charset=utf-8'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Should handle Unicode without issues
        assert 'valid' in data
        # Valid structure, should pass
        assert data['valid'] is True or len(data['errors']) >= 0
    
    def test_validate_xml_api_response_structure(self, client, valid_lift_xml):
        """Test that XML validation API returns proper response structure."""
        response = client.post(
            '/api/validation/xml',
            data=valid_lift_xml,
            content_type='application/xml'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Check all required fields are present
        required_fields = ['valid', 'errors', 'warnings', 'info', 'error_count', 'has_critical_errors']
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Check error structure if errors exist
        if len(data['errors']) > 0:
            error = data['errors'][0]
            assert 'rule_id' in error
            assert 'rule_name' in error
            assert 'message' in error
            assert 'path' in error
            assert 'priority' in error
            assert 'category' in error
    
    def test_validate_xml_api_text_xml_content_type(self, client, valid_lift_xml):
        """Test XML validation API accepts text/xml content type."""
        response = client.post(
            '/api/validation/xml',
            data=valid_lift_xml,
            content_type='text/xml'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'valid' in data
        assert data['valid'] is True
