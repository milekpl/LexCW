"""
Integration tests for XML-based entry form submission.

Tests the complete flow:
1. Form serialization to JSON
2. JSON to LIFT XML conversion  
3. XML submission to API
4. XMLEntryService processing
5. BaseX storage
"""

import pytest
import uuid


def gen_id():
    """Generate unique test ID."""
    return f"integration_test_form_{uuid.uuid4().hex[:8]}"


class TestXMLFormSubmission:
    """Test XML-based form submission flow."""
    
    def test_create_entry_via_xml_api(self, client, basex_available, app):
        """Test creating an entry via XML API endpoint."""
        if not basex_available:
            pytest.skip("BaseX not available")
        
        # Generate unique ID
        test_id = gen_id()
        
        # Sample LIFT XML for testing
        sample_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{test_id}" dateCreated="2024-12-01T12:00:00Z" dateModified="2024-12-01T12:00:00Z">
    <lexical-unit>
        <form lang="en"><text>test word</text></form>
    </lexical-unit>
    <sense id="sense_001" order="0">
        <grammatical-info value="noun"/>
        <gloss lang="en"><text>a test word for form integration</text></gloss>
        <definition>
            <form lang="en"><text>A word used for testing the XML form submission flow.</text></form>
        </definition>
    </sense>
</entry>'''
        
        # Debug: print all routes
        print("\n=== Available routes ===")
        for rule in app.url_map.iter_rules():
            print(f"{rule.rule} -> {rule.endpoint}")
        
        # Submit XML to create endpoint
        response = client.post(
            '/api/xml/entries',
            data=sample_xml,
            content_type='application/xml'
        )
        
        print(f"\n=== Response status: {response.status_code} ===")
        print(f"Response data: {response.data}")
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['entry_id'] == test_id
        assert 'filename' in data
    
    def test_update_entry_via_xml_api(self, client, basex_available):
        """Test updating an entry via XML API endpoint."""
        if not basex_available:
            pytest.skip("BaseX not available")
        
        # Generate unique ID
        test_id = gen_id()
        
        # Sample LIFT XML for testing
        sample_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{test_id}" dateCreated="2024-12-01T12:00:00Z" dateModified="2024-12-01T12:00:00Z">
    <lexical-unit>
        <form lang="en"><text>test word</text></form>
    </lexical-unit>
    <sense id="sense_001" order="0">
        <grammatical-info value="noun"/>
        <gloss lang="en"><text>a test word for form integration</text></gloss>
        <definition>
            <form lang="en"><text>A word used for testing the XML form submission flow.</text></form>
        </definition>
    </sense>
</entry>'''
        
        # First create an entry
        client.post(
            '/api/xml/entries',
            data=sample_xml,
            content_type='application/xml'
        )
        
        # Update the entry
        updated_xml = sample_xml.replace('test word', 'updated test word')
        response = client.put(
            f'/api/xml/entries/{test_id}',
            data=updated_xml,
            content_type='application/xml'
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['entry_id'] == test_id
    
    def test_get_entry_via_xml_api(self, client, basex_available):
        """Test retrieving an entry via XML API endpoint."""
        if not basex_available:
            pytest.skip("BaseX not available")
        
        # Generate unique ID
        test_id = gen_id()
        sample_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{test_id}" dateCreated="2024-12-01T12:00:00Z" dateModified="2024-12-01T12:00:00Z">
    <lexical-unit>
        <form lang="en"><text>test word</text></form>
    </lexical-unit>
    <sense id="sense_001" order="0">
        <grammatical-info value="noun"/>
        <gloss lang="en"><text>a test word for form integration</text></gloss>
        <definition>
            <form lang="en"><text>A word used for testing the XML form submission flow.</text></form>
        </definition>
    </sense>
</entry>'''
        
        # First create an entry
        client.post(
            '/api/xml/entries',
            data=sample_xml,
            content_type='application/xml'
        )
        
        # Retrieve as XML
        response = client.get(f'/api/xml/entries/{test_id}')
        assert response.status_code == 200
        assert response.content_type == 'application/xml; charset=utf-8'
        assert test_id.encode() in response.data
        
        # Retrieve as JSON
        response = client.get(f'/api/xml/entries/{test_id}?format=json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['id'] == test_id
        assert 'xml' in data
        assert 'lexical_units' in data
        assert 'senses' in data
    
    def test_delete_entry_via_xml_api(self, client, basex_available):
        """Test deleting an entry via XML API endpoint."""
        if not basex_available:
            pytest.skip("BaseX not available")
        
        # Generate unique ID
        test_id = gen_id()
        sample_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{test_id}" dateCreated="2024-12-01T12:00:00Z" dateModified="2024-12-01T12:00:00Z">
    <lexical-unit>
        <form lang="en"><text>test word</text></form>
    </lexical-unit>
    <sense id="sense_001" order="0">
        <grammatical-info value="noun"/>
        <gloss lang="en"><text>a test word for form integration</text></gloss>
        <definition>
            <form lang="en"><text>A word used for testing the XML form submission flow.</text></form>
        </definition>
    </sense>
</entry>'''
        
        # First create an entry
        client.post(
            '/api/xml/entries',
            data=sample_xml,
            content_type='application/xml'
        )
        
        # Delete the entry
        response = client.delete(f'/api/xml/entries/{test_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['entry_id'] == test_id
        
        # Verify it's gone
        response = client.get(f'/api/xml/entries/{test_id}')
        assert response.status_code == 404
    
    def test_search_entries_via_xml_api(self, client, basex_available):
        """Test searching entries via XML API endpoint."""
        if not basex_available:
            pytest.skip("BaseX not available")
        
        # Create multiple test entries
        search_base_id = f"integration_test_form_search_{uuid.uuid4().hex[:8]}"
        for i in range(3):
            test_id = f"{search_base_id}_{i:03d}"
            xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{test_id}" dateCreated="2024-12-01T12:00:00Z" dateModified="2024-12-01T12:00:00Z">
    <lexical-unit>
        <form lang="en"><text>test word</text></form>
    </lexical-unit>
    <sense id="sense_001" order="0">
        <grammatical-info value="noun"/>
        <gloss lang="en"><text>a test word for form integration</text></gloss>
        <definition>
            <form lang="en"><text>A word used for testing the XML form submission flow.</text></form>
        </definition>
    </sense>
</entry>'''
            response = client.post(
                '/api/xml/entries',
                data=xml,
                content_type='application/xml'
            )
            assert response.status_code == 201, f"Failed to create entry {i}: {response.get_json()}"
        
        # Search for entries
        response = client.get('/api/xml/entries?q=test&limit=10')
        assert response.status_code == 200
        data = response.get_json()
        assert 'entries' in data
        assert data['total'] >= 3, f"Expected >= 3 results, got {data['total']}"
        assert 'count' in data
        assert 'limit' in data
        assert 'offset' in data
    
    def test_get_stats_via_xml_api(self, client, basex_available):
        """Test getting database statistics via XML API endpoint."""
        if not basex_available:
            pytest.skip("BaseX not available")
        
        response = client.get('/api/xml/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert 'entries' in data
        assert 'senses' in data
        assert isinstance(data['entries'], int)
        assert isinstance(data['senses'], int)
    
    def test_invalid_xml_rejected(self, client, basex_available):
        """Test that invalid XML is rejected."""
        if not basex_available:
            pytest.skip("BaseX not available")
        
        invalid_xml = '<entry>invalid - no namespace or id</entry>'
        response = client.post(
            '/api/xml/entries',
            data=invalid_xml,
            content_type='application/xml'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid XML' in data['error']
    
    def test_empty_xml_rejected(self, client):
        """Test that empty XML is rejected."""
        response = client.post(
            '/api/xml/entries',
            data='',
            content_type='application/xml'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'No XML data' in data['error']
    
    def test_id_mismatch_in_update_rejected(self, client, basex_available):
        """Test that ID mismatch in update is rejected."""
        if not basex_available:
            pytest.skip("BaseX not available")
        
        # Generate unique ID
        test_id = gen_id()
        sample_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<entry xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="{test_id}" dateCreated="2024-12-01T12:00:00Z" dateModified="2024-12-01T12:00:00Z">
    <lexical-unit>
        <form lang="en"><text>test word</text></form>
    </lexical-unit>
    <sense id="sense_001" order="0">
        <grammatical-info value="noun"/>
        <gloss lang="en"><text>a test word for form integration</text></gloss>
        <definition>
            <form lang="en"><text>A word used for testing the XML form submission flow.</text></form>
        </definition>
    </sense>
</entry>'''
        
        # Create an entry
        client.post(
            '/api/xml/entries',
            data=sample_xml,
            content_type='application/xml'
        )
        
        # Try to update with different ID in XML
        wrong_xml = sample_xml.replace(test_id, 'different_id')
        response = client.put(
            f'/api/xml/entries/{test_id}',
            data=wrong_xml,
            content_type='application/xml'
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_nonexistent_entry_returns_404(self, client, basex_available):
        """Test that getting nonexistent entry returns 404."""
        if not basex_available:
            pytest.skip("BaseX not available")
        
        response = client.get('/api/xml/entries/nonexistent_entry_999')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()


@pytest.fixture(scope='module')
def basex_available():
    """Check if BaseX is available for testing."""
    from BaseXClient import BaseXClient
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        session.close()
        return True
    except Exception:
        return False


@pytest.fixture(autouse=True)
def cleanup_test_entries(basex_available):
    """Clean up test entries before and after each test."""
    if not basex_available:
        yield
        return
    
    from BaseXClient import BaseXClient
    
    # Cleanup before test
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        # Delete all integration test entries
        for prefix in ['integration_test_form_001', 'integration_test_form_search_']:
            try:
                query = f'''
                declare namespace lift="http://fieldworks.sil.org/schemas/lift/0.13";
                for $entry in db:open("dictionary")//lift:entry[starts-with(@id, "{prefix}")]
                let $filename := db:path($entry)
                return db:delete("dictionary", $filename)
                '''
                session.execute(f'XQUERY {query}')
            except:
                pass
        session.close()
    except:
        pass
    
    yield
    
    # Cleanup after test
    try:
        session = BaseXClient.Session('localhost', 1984, 'admin', 'admin')
        for prefix in ['integration_test_form_001', 'integration_test_form_search_']:
            try:
                query = f'''
                declare namespace lift="http://fieldworks.sil.org/schemas/lift/0.13";
                for $entry in db:open("dictionary")//lift:entry[starts-with(@id, "{prefix}")]
                let $filename := db:path($entry)
                return db:delete("dictionary", $filename)
                '''
                session.execute(f'XQUERY {query}')
            except:
                pass
        session.close()
    except:
        pass
