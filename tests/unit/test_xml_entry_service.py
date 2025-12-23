"""
Unit tests for XML Entry Service

Tests all CRUD operations, validation, and error handling.
Uses mocks to avoid requiring actual BaseX database connection.
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, MagicMock, patch
from xml.etree import ElementTree as ET

from app.services.xml_entry_service import (
    XMLEntryService,
    XMLEntryServiceError,
    EntryNotFoundError,
    InvalidXMLError,
    DatabaseConnectionError,
    LIFT_NS
)


# Sample valid LIFT XML for testing
VALID_ENTRY_XML = f'''
<entry xmlns="{LIFT_NS}" id="test_001" guid="test_guid_001" dateCreated="2024-01-01T12:00:00Z">
    <lexical-unit>
        <form lang="en"><text>testword</text></form>
    </lexical-unit>
    <sense id="sense_001" order="0">
        <gloss lang="en"><text>a test word</text></gloss>
    </sense>
</entry>
'''.strip()

# Sample valid LIFT XML with namespace prefixes (for namespace-aware tests)
VALID_ENTRY_XML_WITH_PREFIXES = f'''
<lift:entry xmlns:lift="{LIFT_NS}" id="test_001" guid="test_guid_001" dateCreated="2024-01-01T12:00:00Z">
    <lift:lexical-unit>
        <lift:form lang="en"><lift:text>testword</lift:text></lift:form>
    </lift:lexical-unit>
    <lift:sense id="sense_001" order="0">
        <lift:gloss lang="en"><lift:text>a test word</lift:text></lift:gloss>
    </lift:sense>
</lift:entry>
'''.strip()

INVALID_XML_NO_ID = f'''
<entry xmlns="{LIFT_NS}">
    <lexical-unit>
        <form lang="en"><text>testword</text></form>
    </lexical-unit>
</entry>
'''.strip()

INVALID_XML_NO_CONTENT = f'''
<entry xmlns="{LIFT_NS}" id="test_002">
</entry>
'''.strip()

MALFORMED_XML = "<entry id='test_003'><unclosed>"


@pytest.fixture
def mock_basex_session():
    """Create a mock BaseX session."""
    session = MagicMock()
    session.execute = MagicMock(return_value="")
    session.close = MagicMock()
    
    # Mock query object
    query_mock = MagicMock()
    query_mock.execute = MagicMock(return_value="")
    query_mock.close = MagicMock()
    
    session.query = MagicMock(return_value=query_mock)
    
    return session


@pytest.fixture
def xml_service(mock_basex_session):
    """Create XMLEntryService with mocked BaseX connection."""
    with patch('app.services.xml_entry_service.BaseXClient.Session') as mock_session_class:
        # Always return the same mock session
        mock_session_class.return_value = mock_basex_session
        
        # Force namespace detection to work correctly in tests
        # Set up the mock BEFORE creating the service so it can detect namespaces properly
        detection_query_mock = MagicMock()
        detection_query_mock.execute.return_value = 'true'
        detection_query_mock.close.return_value = None
        mock_basex_session.query.return_value = detection_query_mock
        
        service = XMLEntryService()
        
        # Patch _get_session to always return our mock
        service._get_session = Mock(return_value=mock_basex_session)
        
        yield service


class TestXMLEntryServiceInit:
    """Test service initialization."""
    
    def test_init_with_default_params(self, mock_basex_session):
        """Test initialization with default parameters."""
        with patch('app.services.xml_entry_service.BaseXClient.Session') as mock_session_class:
            mock_session_class.return_value = mock_basex_session
            service = XMLEntryService()
            
            assert service.host == 'localhost'
            assert service.port == 1984
            assert service.username == 'admin'
            assert service.password == 'admin'
            # Should use TEST_DB_NAME if set, otherwise 'dictionary'
            import os
            expected_db = os.environ.get('TEST_DB_NAME') or 'dictionary'
            assert service.database == expected_db
    
    def test_init_with_custom_params(self, mock_basex_session):
        """Test initialization with custom parameters."""
        with patch('app.services.xml_entry_service.BaseXClient.Session') as mock_session_class:
            mock_session_class.return_value = mock_basex_session
            service = XMLEntryService(
                host='testhost',
                port=9999,
                username='testuser',
                password='testpass',
                database='testdb'
            )
            
            assert service.host == 'testhost'
            assert service.port == 9999
            assert service.username == 'testuser'
            assert service.password == 'testpass'
            assert service.database == 'testdb'
    
    def test_init_connection_failure(self):
        """Test initialization fails with bad connection."""
        with patch('app.services.xml_entry_service.BaseXClient.Session') as mock_session_class:
            mock_session_class.side_effect = Exception("Connection failed")
            
            with pytest.raises(DatabaseConnectionError):
                XMLEntryService()


class TestValidation:
    """Test XML validation methods."""
    
    def test_validate_valid_xml(self, xml_service):
        """Test validation of valid LIFT XML."""
        root = xml_service._validate_lift_xml(VALID_ENTRY_XML)
        
        assert root is not None
        assert root.attrib['id'] == 'test_001'
    
    def test_validate_malformed_xml(self, xml_service):
        """Test validation rejects malformed XML."""
        with pytest.raises(InvalidXMLError, match="Malformed XML"):
            xml_service._validate_lift_xml(MALFORMED_XML)
    
    def test_validate_missing_id(self, xml_service):
        """Test validation rejects entry without ID."""
        with pytest.raises(InvalidXMLError, match="must have 'id' attribute"):
            xml_service._validate_lift_xml(INVALID_XML_NO_ID)
    
    def test_validate_missing_content(self, xml_service):
        """Test validation rejects entry without lexical-unit or sense."""
        with pytest.raises(InvalidXMLError, match="must have at least one"):
            xml_service._validate_lift_xml(INVALID_XML_NO_CONTENT)
    
    def test_validate_wrong_root_element(self, xml_service):
        """Test validation rejects non-entry root."""
        wrong_root = '<lift xmlns="http://fieldworks.sil.org/schemas/lift/0.13" id="test"></lift>'
        with pytest.raises(InvalidXMLError, match="Root element must be <entry>"):
            xml_service._validate_lift_xml(wrong_root)


class TestCreateEntry:
    """Test entry creation."""
    
    def test_create_entry_success(self, xml_service, mock_basex_session):
        """Test successful entry creation."""
        # Mock entry_exists to return False
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.side_effect = ['false', '']  # First for exists check, second for add
        
        result = xml_service.create_entry(VALID_ENTRY_XML)
        
        assert result['id'] == 'test_001'
        assert result['status'] == 'created'
        assert 'filename' in result
        
        # Verify query was called
        assert mock_basex_session.query.called
    
    def test_create_entry_invalid_xml(self, xml_service):
        """Test creation fails with invalid XML."""
        with pytest.raises(InvalidXMLError):
            xml_service.create_entry(MALFORMED_XML)
    
    def test_create_entry_already_exists(self, xml_service, mock_basex_session):
        """Test creation fails if entry already exists."""
        # Mock entry_exists to return True
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.return_value = 'true'
        
        with pytest.raises(XMLEntryServiceError, match="already exists"):
            xml_service.create_entry(VALID_ENTRY_XML)
    
    def test_create_entry_database_error(self, xml_service, mock_basex_session):
        """Test creation handles database errors."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.side_effect = ['false', Exception("DB error")]
        
        with pytest.raises(XMLEntryServiceError, match="Failed to create"):
            xml_service.create_entry(VALID_ENTRY_XML)


class TestGetEntry:
    """Test entry retrieval."""
    
    def test_get_entry_success(self, xml_service, mock_basex_session):
        """Test successful entry retrieval."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.return_value = VALID_ENTRY_XML_WITH_PREFIXES
        
        result = xml_service.get_entry('test_001')
        
        assert result['id'] == 'test_001'
        assert result['guid'] == 'test_guid_001'
        assert 'xml' in result
        assert len(result['lexical_units']) > 0
        assert len(result['senses']) > 0
    
    def test_get_entry_not_found(self, xml_service, mock_basex_session):
        """Test retrieval of non-existent entry."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.return_value = ''  # Empty result means not found
        
        with pytest.raises(EntryNotFoundError):
            xml_service.get_entry('nonexistent')
    
    def test_get_entry_database_error(self, xml_service, mock_basex_session):
        """Test retrieval handles database errors."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.side_effect = Exception("DB error")
        
        with pytest.raises(XMLEntryServiceError, match="Failed to retrieve"):
            xml_service.get_entry('test_001')


class TestUpdateEntry:
    """Test entry updates."""
    
    def test_update_entry_success(self, xml_service, mock_basex_session):
        """Test successful entry update."""
        # Mock entry_exists to return True, then execute update checks
        query_mock = mock_basex_session.query.return_value
        # Order: entry_exists(), delete, insert, flush
        query_mock.execute.side_effect = ['true', '', '', '']
        
        updated_xml = VALID_ENTRY_XML.replace('testword', 'updatedword')
        result = xml_service.update_entry('test_001', updated_xml)
        
        assert result['id'] == 'test_001'
        assert result['status'] == 'updated'
        assert 'filename' not in result  # update doesn't create files
    
    def test_update_entry_not_found(self, xml_service, mock_basex_session):
        """Test update fails if entry doesn't exist."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.return_value = 'false'
        
        with pytest.raises(EntryNotFoundError):
            xml_service.update_entry('test_001', VALID_ENTRY_XML)
    
    def test_update_entry_id_mismatch(self, xml_service, mock_basex_session):
        """Test update fails if IDs don't match."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.return_value = 'true'
        
        with pytest.raises(InvalidXMLError, match="ID mismatch"):
            xml_service.update_entry('different_id', VALID_ENTRY_XML)
    
    def test_update_entry_invalid_xml(self, xml_service):
        """Test update fails with invalid XML."""
        with pytest.raises(InvalidXMLError):
            xml_service.update_entry('test_001', MALFORMED_XML)
    
    def test_update_entry_database_error(self, xml_service, mock_basex_session):
        """Test update handles database errors."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.side_effect = ['true', Exception("DB error")]
        
        with pytest.raises(XMLEntryServiceError, match="Failed to update"):
            xml_service.update_entry('test_001', VALID_ENTRY_XML)


class TestDeleteEntry:
    """Test entry deletion."""
    
    def test_delete_entry_success(self, xml_service, mock_basex_session):
        """Test successful entry deletion."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.side_effect = ['true', '']  # exists, delete
        
        result = xml_service.delete_entry('test_001')
        
        assert result['id'] == 'test_001'
        assert result['status'] == 'deleted'
    
    def test_delete_entry_not_found(self, xml_service, mock_basex_session):
        """Test deletion fails if entry doesn't exist."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.return_value = 'false'
        
        with pytest.raises(EntryNotFoundError):
            xml_service.delete_entry('nonexistent')
    
    def test_delete_entry_database_error(self, xml_service, mock_basex_session):
        """Test deletion handles database errors."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.side_effect = ['true', Exception("DB error")]
        
        with pytest.raises(XMLEntryServiceError, match="Failed to delete"):
            xml_service.delete_entry('test_001')


class TestEntryExists:
    """Test entry existence check."""
    
    def test_entry_exists_true(self, xml_service, mock_basex_session):
        """Test entry_exists returns True for existing entry."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.return_value = 'true'
        
        assert xml_service.entry_exists('test_001') is True
    
    def test_entry_exists_false(self, xml_service, mock_basex_session):
        """Test entry_exists returns False for non-existent entry."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.return_value = 'false'
        
        assert xml_service.entry_exists('nonexistent') is False
    
    def test_entry_exists_error(self, xml_service, mock_basex_session):
        """Test entry_exists returns False on error."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.side_effect = Exception("DB error")
        
        # Should return False on error, not raise
        assert xml_service.entry_exists('test_001') is False


class TestSearchEntries:
    """Test entry search."""
    
    def test_search_entries_with_query(self, xml_service, mock_basex_session):
        """Test searching entries with query text."""
        search_results = '''
        <entry id="test_001">
            <lexical-unit><text>testword</text></lexical-unit>
        </entry>
        '''
        
        query_mock = mock_basex_session.query.return_value
        # First call returns search results, second call returns count
        query_mock.execute.side_effect = [search_results, '1']
        
        result = xml_service.search_entries(query_text='test', limit=50, offset=0)
        
        assert result['total'] == 1
        assert result['count'] == 1
        assert result['limit'] == 50
        assert result['offset'] == 0
        assert len(result['entries']) == 1
        assert result['entries'][0]['id'] == 'test_001'
    
    def test_search_entries_without_query(self, xml_service, mock_basex_session):
        """Test searching all entries without query."""
        search_results = '''
        <entry id="test_001">
            <lexical-unit><text>word1</text></lexical-unit>
        </entry>
        <entry id="test_002">
            <lexical-unit><text>word2</text></lexical-unit>
        </entry>
        '''
        
        query_mock = mock_basex_session.query.return_value
        # First call returns search results, second call returns count
        query_mock.execute.side_effect = [search_results, '2']
        
        result = xml_service.search_entries(query_text='', limit=50, offset=0)
        
        assert result['total'] == 2
        assert result['count'] == 2
        assert len(result['entries']) == 2
    
    def test_search_entries_with_pagination(self, xml_service, mock_basex_session):
        """Test search with pagination."""
        search_results = '''
        <entry id="test_021">
            <lexical-unit><text>word21</text></lexical-unit>
        </entry>
        '''
        
        query_mock = mock_basex_session.query.return_value
        # First call returns search results, second call returns count
        query_mock.execute.side_effect = [search_results, '100']
        
        result = xml_service.search_entries(query_text='word', limit=10, offset=20)
        
        assert result['total'] == 100
        assert result['count'] == 1
        assert result['limit'] == 10
        assert result['offset'] == 20
    
    def test_search_entries_no_results(self, xml_service, mock_basex_session):
        """Test search with no results."""
        search_results = ''  # Empty results
        
        query_mock = mock_basex_session.query.return_value
        # First call returns empty search results, second call returns count of 0
        query_mock.execute.side_effect = [search_results, '0']
        
        result = xml_service.search_entries(query_text='nonexistent')
        
        assert result['total'] == 0
        assert result['count'] == 0
        assert len(result['entries']) == 0
    
    def test_search_entries_database_error(self, xml_service, mock_basex_session):
        """Test search handles database errors."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.side_effect = Exception("DB error")
        
        with pytest.raises(XMLEntryServiceError, match="Search failed"):
            xml_service.search_entries(query_text='test')


class TestGetDatabaseStats:
    """Test database statistics."""
    
    def test_get_stats_success(self, xml_service, mock_basex_session):
        """Test successful stats retrieval."""
        stats_xml = '''
        <stats>
            <entries>100</entries>
            <senses>250</senses>
            <avgSenses>2.5</avgSenses>
        </stats>
        '''
        
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.return_value = stats_xml
        
        result = xml_service.get_database_stats()
        
        assert result['entries'] == 100
        assert result['senses'] == 250
        assert result['avg_senses'] == 2.5
    
    def test_get_stats_empty_database(self, xml_service, mock_basex_session):
        """Test stats for empty database."""
        stats_xml = '''
        <stats>
            <entries>0</entries>
            <senses>0</senses>
            <avgSenses>0</avgSenses>
        </stats>
        '''
        
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.return_value = stats_xml
        
        result = xml_service.get_database_stats()
        
        assert result['entries'] == 0
        assert result['senses'] == 0
        assert result['avg_senses'] == 0.0
    
    def test_get_stats_database_error(self, xml_service, mock_basex_session):
        """Test stats handles database errors."""
        query_mock = mock_basex_session.query.return_value
        query_mock.execute.side_effect = Exception("DB error")
        
        with pytest.raises(XMLEntryServiceError, match="Failed to get database stats"):
            xml_service.get_database_stats()


class TestFilenameGeneration:
    """Test filename generation."""
    
    def test_generate_filename_format(self, xml_service):
        """Test filename generation creates valid format."""
        filename = xml_service._generate_filename('test_entry_001')
        
        assert filename.startswith('test_entry_001_')
        assert filename.endswith('.xml')
        assert '_' in filename
    
    def test_generate_filename_unique(self, xml_service):
        """Test filename generation creates unique names."""
        import time
        
        filename1 = xml_service._generate_filename('test_001')
        time.sleep(0.01)  # Small delay to ensure different timestamp
        filename2 = xml_service._generate_filename('test_001')
        
        # Should be different due to timestamp
        assert filename1 != filename2


class TestSessionManagement:
    """Test BaseX session management."""
    
    def test_get_session_success(self, xml_service, mock_basex_session):
        """Test getting a valid session."""
        with patch('app.services.xml_entry_service.BaseXClient.Session') as mock_session_class:
            mock_session_class.return_value = mock_basex_session
            
            session = xml_service._get_session()
            
            assert session is not None
            assert mock_basex_session.execute.called
    
    def test_get_session_connection_failure(self):
        """Test session creation failure."""
        with patch('app.services.xml_entry_service.BaseXClient.Session') as mock_session_class:
            mock_session_class.side_effect = Exception("Connection failed")
            
            # Create a fresh service instance that will fail on connection test
            with pytest.raises(DatabaseConnectionError):
                XMLEntryService()