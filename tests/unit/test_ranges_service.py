"""Unit tests for RangesService."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.services.ranges_service import RangesService
from app.utils.exceptions import NotFoundError, ValidationError


class TestRangesService:
    """Test RangesService class."""
    
    @pytest.fixture
    def mock_connector(self):
        """Create mock BaseX connector."""
        connector = Mock()
        connector.database = 'test_db'
        connector.execute_query = Mock()
        connector.execute_update = Mock()
        return connector
    
    @pytest.fixture
    def service(self, mock_connector):
        """Create RangesService with mock connector."""
        return RangesService(mock_connector)
    
    def test_get_all_ranges_success(self, service, mock_connector):
        """Test retrieving all ranges successfully."""
        # Mock BaseX response
        mock_connector.execute_query.return_value = """
        <lift-ranges>
          <range id="test-range" guid="12345">
            <label><form lang="en"><text>Test Range</text></form></label>
          </range>
        </lift-ranges>
        """
        
        ranges = service.get_all_ranges()
        
        assert 'test-range' in ranges
        assert ranges['test-range']['id'] == 'test-range'
        assert ranges['test-range']['guid'] == '12345'
    
    def test_get_all_ranges_empty(self, service, mock_connector):
        """Test retrieving ranges when database is empty."""
        mock_connector.execute_query.return_value = ''
        
        ranges = service.get_all_ranges()
        
        assert ranges == {}
    
    def test_get_range_success(self, service, mock_connector):
        """Test getting a specific range by ID."""
        # Mock BaseX response
        mock_connector.execute_query.return_value = """
        <lift-ranges>
          <range id="test-range" guid="12345">
            <label><form lang="en"><text>Test Range</text></form></label>
          </range>
        </lift-ranges>
        """
        
        range_data = service.get_range('test-range')
        
        assert range_data['id'] == 'test-range'
        assert range_data['guid'] == '12345'
    
    def test_get_range_not_found(self, service, mock_connector):
        """Test getting a non-existent range raises NotFoundError."""
        mock_connector.execute_query.return_value = """
        <lift-ranges>
          <range id="test-range" guid="12345">
            <label><form lang="en"><text>Test Range</text></form></label>
          </range>
        </lift-ranges>
        """
        
        with pytest.raises(NotFoundError, match="Range 'nonexistent' not found"):
            service.get_range('nonexistent')
    
    def test_validate_range_id_unique(self, service, mock_connector):
        """Test range ID uniqueness check - ID does not exist."""
        # Mock: ID does not exist
        mock_connector.execute_query.return_value = 'false'
        
        result = service.validate_range_id('new-range')
        
        assert result is True
    
    def test_validate_range_id_duplicate(self, service, mock_connector):
        """Test range ID uniqueness check - ID already exists."""
        # Mock: ID exists
        mock_connector.execute_query.return_value = 'true'
        
        result = service.validate_range_id('existing-range')
        
        assert result is False
    
    @patch('app.services.ranges_service.uuid.uuid4')
    def test_create_range_valid(self, mock_uuid, service, mock_connector):
        """Test creating a new range with valid data."""
        # Mock UUID generation
        mock_uuid.return_value = Mock(hex='123456789abc')
        mock_uuid.return_value.__str__ = Mock(return_value='12345678-9abc-def0-1234-56789abcdef0')
        
        # Mock: ID is unique
        mock_connector.execute_query.return_value = 'false'
        
        range_data = {
            'id': 'custom-range',
            'labels': {'en': 'Custom Range'},
            'descriptions': {'en': 'A custom range for testing'}
        }
        
        guid = service.create_range(range_data)
        
        # Verify GUID generated
        assert guid is not None
        assert len(guid) == 36  # UUID format
        
        # Verify XQuery executed
        mock_connector.execute_update.assert_called_once()
        query = mock_connector.execute_update.call_args[0][0]
        assert 'custom-range' in query
        assert guid in query
    
    def test_create_range_missing_id(self, service, mock_connector):
        """Test creating range without ID raises ValidationError."""
        range_data = {
            'labels': {'en': 'Test Range'}
        }
        
        with pytest.raises(ValidationError, match="Range ID is required"):
            service.create_range(range_data)
    
    def test_create_range_duplicate_id(self, service, mock_connector):
        """Test creating range with duplicate ID raises ValidationError."""
        # Mock: ID already exists
        mock_connector.execute_query.return_value = 'true'
        
        range_data = {
            'id': 'existing-range',
            'labels': {'en': 'Existing Range'}
        }
        
        with pytest.raises(ValidationError, match="already exists"):
            service.create_range(range_data)
    
    def test_update_range_success(self, service, mock_connector):
        """Test updating an existing range."""
        # Mock: Range exists
        mock_connector.execute_query.return_value = """
        <lift-ranges>
          <range id="test-range" guid="12345">
            <label><form lang="en"><text>Test Range</text></form></label>
          </range>
        </lift-ranges>
        """
        
        range_data = {
            'id': 'test-range',
            'guid': '12345',
            'labels': {'en': 'Updated Range'},
            'descriptions': {'en': 'Updated description'}
        }
        
        service.update_range('test-range', range_data)
        
        # Verify delete and insert were called
        assert mock_connector.execute_update.call_count == 2
    
    def test_update_range_not_found(self, service, mock_connector):
        """Test updating non-existent range raises NotFoundError."""
        mock_connector.execute_query.return_value = '<lift-ranges></lift-ranges>'
        
        range_data = {
            'labels': {'en': 'Updated Range'}
        }
        
        with pytest.raises(NotFoundError):
            service.update_range('nonexistent', range_data)
    
    def test_delete_range_no_usage(self, service, mock_connector):
        """Test deleting a range that is not in use."""
        # Mock: Range exists
        mock_connector.execute_query.side_effect = [
            """<lift-ranges>
              <range id="test-range" guid="12345">
                <label><form lang="en"><text>Test Range</text></form></label>
              </range>
            </lift-ranges>""",
            ''  # No usage
        ]
        
        service.delete_range('test-range')
        
        # Verify delete was called
        mock_connector.execute_update.assert_called_once()
    
    def test_delete_range_with_usage_no_migration(self, service, mock_connector):
        """Test deleting range that is in use without migration raises ValidationError."""
        # Mock: Range exists and is in use
        mock_connector.execute_query.side_effect = [
            """<lift-ranges>
              <range id="test-range" guid="12345">
                <label><form lang="en"><text>Test Range</text></form></label>
              </range>
            </lift-ranges>""",
            'entry1|headword1|1'  # Has usage
        ]
        
        with pytest.raises(ValidationError, match="is used in .* entries"):
            service.delete_range('test-range')
    
    def test_delete_range_with_migration_remove(self, service, mock_connector):
        """Test deleting range with remove migration."""
        # Mock: Range exists and is in use
        mock_connector.execute_query.side_effect = [
            """<lift-ranges>
              <range id="test-range" guid="12345">
                <label><form lang="en"><text>Test Range</text></form></label>
              </range>
            </lift-ranges>""",
            'entry1|headword1|1',  # Has usage for delete check
            'entry1|headword1|1'   # Has usage for migration
        ]
        
        migration = {'operation': 'remove'}
        
        service.delete_range('test-range', migration=migration)
        
        # Verify migration and delete were called
        assert mock_connector.execute_update.call_count == 2
    
    def test_validate_element_id_unique(self, service, mock_connector):
        """Test element ID uniqueness within range."""
        mock_connector.execute_query.return_value = 'false'
        
        result = service.validate_element_id('test-range', 'new-element')
        
        assert result is True
    
    def test_validate_element_id_duplicate(self, service, mock_connector):
        """Test element ID already exists within range."""
        mock_connector.execute_query.return_value = 'true'
        
        result = service.validate_element_id('test-range', 'existing-element')
        
        assert result is False
    
    def test_validate_parent_reference_valid(self, service, mock_connector):
        """Test valid parent reference (no circular dependency)."""
        # Mock: Range with hierarchical elements
        mock_connector.execute_query.return_value = """
        <lift-ranges>
          <range id="test-range" guid="12345">
            <range-element id="parent" guid="p1"></range-element>
            <range-element id="child" guid="c1" parent="parent"></range-element>
          </range>
        </lift-ranges>
        """
        
        # Test setting child's parent to parent (valid)
        result = service.validate_parent_reference('test-range', 'child', 'parent')
        
        assert result is True
    
    def test_validate_parent_reference_circular(self, service, mock_connector):
        """Test circular parent reference is detected."""
        # Mock: Range with elements
        mock_connector.execute_query.return_value = """
        <lift-ranges>
          <range id="test-range" guid="12345">
            <range-element id="elem1" guid="e1" parent="elem2"></range-element>
            <range-element id="elem2" guid="e2"></range-element>
          </range>
        </lift-ranges>
        """
        
        # Test setting elem2's parent to elem1 (circular)
        result = service.validate_parent_reference('test-range', 'elem2', 'elem1')
        
        assert result is False
    
    def test_validate_parent_reference_nonexistent_parent(self, service, mock_connector):
        """Test reference to non-existent parent raises ValidationError."""
        # Mock: Range with elements
        mock_connector.execute_query.return_value = """
        <lift-ranges>
          <range id="test-range" guid="12345">
            <range-element id="elem1" guid="e1"></range-element>
          </range>
        </lift-ranges>
        """
        
        with pytest.raises(ValidationError, match="Parent element .* not found"):
            service.validate_parent_reference('test-range', 'elem1', 'nonexistent')
    
    @patch('app.services.ranges_service.uuid.uuid4')
    def test_create_range_element_valid(self, mock_uuid, service, mock_connector):
        """Test creating a new range element."""
        # Mock UUID
        mock_uuid.return_value = Mock(hex='abc123')
        mock_uuid.return_value.__str__ = Mock(return_value='abcdef12-3456-7890-abcd-ef1234567890')
        
        # Mock: Range exists, element ID is unique
        mock_connector.execute_query.side_effect = [
            """<lift-ranges>
              <range id="test-range" guid="12345"></range>
            </lift-ranges>""",
            'false'  # Element ID is unique
        ]
        
        element_data = {
            'id': 'new-element',
            'labels': {'en': 'New Element'},
            'descriptions': {'en': 'A new element'}
        }
        
        guid = service.create_range_element('test-range', element_data)
        
        assert guid is not None
        assert len(guid) == 36
        
        # Verify insert was called
        mock_connector.execute_update.assert_called_once()
    
    def test_create_range_element_missing_id(self, service, mock_connector):
        """Test creating element without ID raises ValidationError."""
        # Mock: Range exists
        mock_connector.execute_query.return_value = """
        <lift-ranges>
          <range id="test-range" guid="12345"></range>
        </lift-ranges>
        """
        
        element_data = {
            'labels': {'en': 'New Element'}
        }
        
        with pytest.raises(ValidationError, match="Element ID is required"):
            service.create_range_element('test-range', element_data)
    
    def test_create_range_element_duplicate_id(self, service, mock_connector):
        """Test creating element with duplicate ID raises ValidationError."""
        # Mock: Range exists, element ID is not unique
        mock_connector.execute_query.side_effect = [
            """<lift-ranges>
              <range id="test-range" guid="12345"></range>
            </lift-ranges>""",
            'true'  # Element ID already exists
        ]
        
        element_data = {
            'id': 'existing-element',
            'labels': {'en': 'Element'}
        }
        
        with pytest.raises(ValidationError, match="already exists"):
            service.create_range_element('test-range', element_data)
    
    def test_find_range_usage_grammatical_info(self, service, mock_connector):
        """Test finding usage of grammatical-info range."""
        mock_connector.execute_query.return_value = 'entry1|headword1|2\nentry2|headword2|1'
        
        usage = service.find_range_usage('grammatical-info', 'Noun')
        
        assert len(usage) == 2
        assert usage[0]['entry_id'] == 'entry1'
        assert usage[0]['headword'] == 'headword1'
        assert usage[0]['count'] == 2
        assert usage[1]['count'] == 1
    
    def test_find_range_usage_no_usage(self, service, mock_connector):
        """Test finding usage when there is none."""
        mock_connector.execute_query.return_value = ''
        
        usage = service.find_range_usage('custom-range', 'value1')
        
        assert usage == []
    
    def test_migrate_range_values_replace(self, service, mock_connector):
        """Test migrating range values with replace operation."""
        # Mock: Find usage and execute migration
        mock_connector.execute_query.return_value = 'entry1|headword1|1\nentry2|headword2|1'
        
        result = service.migrate_range_values(
            'grammatical-info',
            'Noun',
            'replace',
            'Substantive',
            dry_run=False
        )
        
        assert result['entries_affected'] == 2
        assert result['fields_updated'] == 2
        
        # Verify update was called
        mock_connector.execute_update.assert_called_once()
    
    def test_migrate_range_values_remove(self, service, mock_connector):
        """Test migrating range values with remove operation."""
        # Mock: Find usage and execute migration
        mock_connector.execute_query.return_value = 'entry1|headword1|1'
        
        result = service.migrate_range_values(
            'custom-range',
            'old-value',
            'remove',
            dry_run=False
        )
        
        assert result['entries_affected'] == 1
        
        # Verify delete was called
        mock_connector.execute_update.assert_called_once()
    
    def test_migrate_range_values_dry_run(self, service, mock_connector):
        """Test dry run of migration only counts affected entries."""
        # Mock: Find usage
        mock_connector.execute_query.return_value = 'entry1|headword1|1\nentry2|headword2|1'
        
        result = service.migrate_range_values(
            'grammatical-info',
            'Noun',
            'replace',
            'Substantive',
            dry_run=True
        )
        
        assert result['entries_affected'] == 2
        assert result['fields_updated'] == 0
        
        # Verify no update was executed
        mock_connector.execute_update.assert_not_called()
    
    def test_migrate_range_values_replace_without_new_value(self, service, mock_connector):
        """Test replace operation without new_value raises ValidationError."""
        with pytest.raises(ValidationError, match="new_value required"):
            service.migrate_range_values(
                'test-range',
                'old-value',
                'replace',
                new_value=None,
                dry_run=False
            )
    
    def test_build_multilingual_xml(self, service):
        """Test building multilingual XML structure."""
        content = {
            'en': 'English text',
            'pl': 'Polish text'
        }
        
        xml_str = service._build_multilingual_xml('label', content)
        
        assert '<label>' in xml_str
        assert 'lang="en"' in xml_str
        assert 'lang="pl"' in xml_str
        assert '<text>English text</text>' in xml_str
        assert '<text>Polish text</text>' in xml_str
    
    def test_build_multilingual_xml_empty(self, service):
        """Test building multilingual XML with empty content."""
        xml_str = service._build_multilingual_xml('label', {})
        
        assert xml_str == ''
    
    def test_build_range_element_xml(self, service):
        """Test building range element XML."""
        element_data = {
            'id': 'test-element',
            'guid': '12345',
            'parent': 'parent-element',
            'labels': {'en': 'Test Element'},
            'descriptions': {'en': 'Description'},
            'abbrevs': {'en': 'TE'},
            'traits': {'trait1': 'value1'}
        }
        
        xml_str = service._build_range_element_xml(element_data)
        
        assert '<range-element' in xml_str
        assert 'id="test-element"' in xml_str
        assert 'guid="12345"' in xml_str
        assert 'parent="parent-element"' in xml_str
        assert '<label>' in xml_str
        assert '<description>' in xml_str
        assert '<abbrev>' in xml_str
        assert '<trait' in xml_str
        assert 'name="trait1"' in xml_str
        assert 'value="value1"' in xml_str
