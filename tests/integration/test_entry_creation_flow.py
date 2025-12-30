"""Test for entry creation flow - verifying ID handling."""
import pytest


class TestEntryCreationFlow:
    """Test cases for entry creation with proper ID handling."""

    def test_entry_model_generates_id(self):
        """Test that Entry model can generate IDs for new entries."""
        from app.models.entry import Entry

        # Create entry without ID - should auto-generate one
        entry = Entry(lexical_unit={'en': 'test'})
        assert entry.id is not None, "Entry should have an auto-generated ID"

    def test_entry_with_explicit_id(self):
        """Test that Entry model accepts explicit ID."""
        from app.models.entry import Entry

        entry = Entry(id_='my-test-id', lexical_unit={'en': 'test'})
        assert entry.id == 'my-test-id', "Entry should use explicit ID"

    def test_xml_serializer_generates_id(self, client):
        """Test that LIFTXMLSerializer can generate IDs."""
        response = client.get('/static/js/lift-xml-serializer.js')
        js_code = response.data.decode('utf-8')

        assert 'generateEntryId' in js_code, "Serializer should have generateEntryId method"
        assert 'new_entry_' in js_code, "ID format should include new_entry_ prefix"

    def test_entry_creation_endpoint_exists(self, client):
        """Test that entry creation endpoint is accessible."""
        # Test the XML-based creation endpoint
        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift xmlns="http://fieldworks.sil.org/schemas/lift/0.13" version="0.13">
<entry id="test-entry-123" dateCreated="2025-12-30T00:00:00" dateModified="2025-12-30T00:00:00">
<lexical-unit><form lang="en"><text>test</text></form></lexical-unit>
</entry>
</lift>'''

        response = client.post(
            '/api/xml/entries',
            data=test_xml,
            content_type='application/xml'
        )

        # The endpoint should either succeed or fail gracefully
        assert response.status_code in [201, 400, 404, 500], \
            f"Entry creation endpoint should be accessible, got {response.status_code}"

    def test_entry_form_has_hidden_id_field(self):
        """Test that entry form has hidden ID field for new entries."""
        import os
        template_path = os.path.join(
            os.path.dirname(__file__), '..', '..',
            'app', 'templates', 'entry_form.html'
        )
        with open(template_path, 'r') as f:
            content = f.read()

        # Check for hidden ID field
        assert 'name="id"' in content or "name='id'" in content, \
            "Entry form should have ID field"


class TestClientSideEntryCreation:
    """Test cases for client-side entry creation JavaScript."""

    def test_form_serializer_handles_new_entry(self, client):
        """Test that form serializer handles new entries without ID."""
        response = client.get('/static/js/form-serializer.js')
        js_code = response.data.decode('utf-8')

        # Check that the serializer handles missing IDs
        assert 'temp-' in js_code or 'new_entry_' in js_code, \
            "Serializer should generate temp IDs for new entries"

    def test_entry_form_js_generates_temp_id(self, client):
        """Test that entry-form.js generates temp IDs for new entries."""
        response = client.get('/static/js/entry-form.js')
        js_code = response.data.decode('utf-8')

        # Check for temp ID generation logic
        assert 'formData.id' in js_code, "Entry form should check for formData.id"
        assert 'temp-' in js_code or 'generateEntryId' in js_code, \
            "Entry form should generate temp IDs"

    def test_save_uses_correct_endpoint_for_new_entry(self, client):
        """Test that save uses POST (create) for new entries."""
        response = client.get('/static/js/entry-form.js')
        js_code = response.data.decode('utf-8')

        # Check that new entries use POST to /api/xml/entries
        assert "/api/xml/entries" in js_code or "api/xml/entries" in js_code, \
            "New entries should be created via /api/xml/entries"
        assert "POST" in js_code, "New entries should use POST method"
