"""Unit tests for multilingual LIFT range element support."""

from __future__ import annotations

import pytest
from unittest.mock import Mock
from typing import Dict, Any

from app.services.ranges_service import RangesService
from app.utils.exceptions import ValidationError


@pytest.fixture
def mock_connector() -> Mock:
    """Create a mock BaseX connector."""
    connector = Mock()
    connector.database = 'test_db'
    connector.is_connected.return_value = True
    connector.execute_query.reset_mock()
    connector.execute_update.reset_mock()
    return connector


@pytest.fixture
def ranges_service(mock_connector: Mock) -> RangesService:
    """Create a RangesService with mock connector."""
    return RangesService(db_connector=mock_connector)


class TestMultilingualElementCreation:
    """Test creating range elements with multilingual properties."""
    
    def test_create_element_with_multilingual_labels(
        self, ranges_service: RangesService, mock_connector: Mock
    ) -> None:
        """Should create element with labels in multiple languages."""
        # Reset and setup new mock for this test
        mock_connector.reset_mock()
        
        # Mock execute_query for three calls:
        # 1. get_all_ranges - return ranges XML
        # 2. validate_element_id - return 'false' (element doesn't exist)
        # 3. execute_update - for inserting element
        mock_connector.execute_query.side_effect = [
            """
            <lift-ranges>
                <range id="test-range" guid="range-guid">
                    <label><form lang="en"><text>Test Range</text></form></label>
                </range>
            </lift-ranges>
            """,
            'false'  # validate_element_id returns false (element doesn't exist)
        ]
        
        # Mock the ranges_parser to return parsed data
        ranges_service.ranges_parser.parse_string = Mock(return_value={
            'test-range': {
                'id': 'test-range',
                'guid': 'range-guid',
                'labels': {'en': 'Test Range'},
                'values': []
            }
        })
        
        element_data: Dict[str, Any] = {
            'id': 'ml-test-element-1',
            'labels': {
                'en': 'English Label',
                'pl': 'Etykieta Polska',
                'pt': 'Rótulo Português'
            },
            'description': {},
            'abbrevs': {},
            'parent': '',
            'traits': {}
        }
        
        # Execute
        guid = ranges_service.create_range_element('test-range', element_data)
        
        # Verify
        assert guid is not None
        assert len(guid) > 0
        mock_connector.execute_update.assert_called_once()
        call_args = mock_connector.execute_update.call_args[0][0]
        assert 'English Label' in call_args
        assert 'Etykieta Polska' in call_args
        assert 'Rótulo Português' in call_args
    
    def test_create_element_with_multilingual_descriptions(
        self, ranges_service: RangesService, mock_connector: Mock
    ) -> None:
        """Should create element with descriptions in multiple languages."""
        # Reset and setup new mock for this test
        mock_connector.reset_mock()
        
        # Mock execute_query for two calls
        mock_connector.execute_query.side_effect = [
            """
            <lift-ranges>
                <range id="test-range" guid="range-guid">
                    <label><form lang="en"><text>Test Range</text></form></label>
                </range>
            </lift-ranges>
            """,
            'false'  # validate_element_id returns false (element doesn't exist)
        ]
        
        ranges_service.ranges_parser.parse_string = Mock(return_value={
            'test-range': {
                'id': 'test-range',
                'guid': 'range-guid',
                'labels': {'en': 'Test Range'},
                'values': []
            }
        })
        
        element_data: Dict[str, Any] = {
            'id': 'ml-test-element-2',
            'labels': {'en': 'Test'},
            'description': {
                'en': 'English description',
                'pl': 'Polski opis',
                'pt': 'Descrição em português'
            },
            'abbrevs': {},
            'parent': '',
            'traits': {}
        }
        
        # Execute
        guid = ranges_service.create_range_element('test-range', element_data)
        
        # Verify
        assert guid is not None
        mock_connector.execute_update.assert_called_once()
        call_args = mock_connector.execute_update.call_args[0][0]
        assert 'English description' in call_args
        assert 'Polski opis' in call_args
        assert 'Descrição em português' in call_args
    
    def test_create_element_with_multilingual_abbreviations(
        self, ranges_service: RangesService, mock_connector: Mock
    ) -> None:
        """Should create element with abbreviations in multiple languages."""
        # Reset and setup new mock for this test
        mock_connector.reset_mock()
        
        # Mock execute_query for two calls
        mock_connector.execute_query.side_effect = [
            """
            <lift-ranges>
                <range id="test-range" guid="range-guid">
                    <label><form lang="en"><text>Test Range</text></form></label>
                </range>
            </lift-ranges>
            """,
            'false'  # validate_element_id returns false (element doesn't exist)
        ]
        
        ranges_service.ranges_parser.parse_string = Mock(return_value={
            'test-range': {
                'id': 'test-range',
                'guid': 'range-guid',
                'labels': {'en': 'Test Range'},
                'values': []
            }
        })
        
        element_data: Dict[str, Any] = {
            'id': 'ml-test-element-3',
            'labels': {'en': 'Test'},
            'description': {},
            'abbrevs': {
                'en': 'TST',
                'pl': 'TEST',
                'pt': 'TST'
            },
            'parent': '',
            'traits': {}
        }
        
        # Execute
        guid = ranges_service.create_range_element('test-range', element_data)
        
        # Verify
        assert guid is not None
        mock_connector.execute_update.assert_called_once()
        call_args = mock_connector.execute_update.call_args[0][0]
        assert 'TST' in call_args
        assert 'TEST' in call_args
    
    def test_create_element_with_all_multilingual_properties(
        self, ranges_service: RangesService, mock_connector: Mock
    ) -> None:
        """Should create element with all multilingual properties."""
        # Reset and setup new mock for this test
        mock_connector.reset_mock()
        
        # Mock execute_query for two calls
        mock_connector.execute_query.side_effect = [
            """
            <lift-ranges>
                <range id="test-range" guid="range-guid">
                    <label><form lang="en"><text>Test Range</text></form></label>
                </range>
            </lift-ranges>
            """,
            'false'  # validate_element_id returns false (element doesn't exist)
        ]
        
        ranges_service.ranges_parser.parse_string = Mock(return_value={
            'test-range': {
                'id': 'test-range',
                'guid': 'range-guid',
                'labels': {'en': 'Test Range'},
                'values': []
            }
        })
        
        element_data: Dict[str, Any] = {
            'id': 'ml-comprehensive-element',
            'labels': {
                'en': 'Comprehensive Label',
                'pl': 'Kompleksowa Etykieta'
            },
            'description': {
                'en': 'A comprehensive test',
                'pl': 'Kompleksowy test'
            },
            'abbrevs': {
                'en': 'CMP',
                'pl': 'KMPL'
            },
            'parent': '',
            'traits': {}
        }
        
        # Execute
        guid = ranges_service.create_range_element('test-range', element_data)
        
        # Verify
        assert guid is not None
        mock_connector.execute_update.assert_called_once()
        call_args = mock_connector.execute_update.call_args[0][0]
        assert 'Comprehensive Label' in call_args
        assert 'Kompleksowa Etykieta' in call_args
        assert 'A comprehensive test' in call_args
        assert 'Kompleksowy test' in call_args
        assert 'CMP' in call_args
        assert 'KMPL' in call_args


class TestMultilingualElementUpdate:
    """Test updating range elements with multilingual properties."""
    
    def test_update_element_multilingual_labels(
        self, ranges_service: RangesService, mock_connector: Mock
    ) -> None:
        """Should update element labels in multiple languages."""
        # Setup
        mock_connector.execute_query.return_value = """
        <lift-ranges>
            <range id="test-range" guid="range-guid">
                <range-element id="test-element" guid="elem-guid">
                    <label><form lang="en"><text>Old Label</text></form></label>
                </range-element>
            </range>
        </lift-ranges>
        """
        
        ranges_service.ranges_parser.parse_string = Mock(return_value={
            'test-range': {
                'id': 'test-range',
                'guid': 'range-guid',
                'labels': {},
                'values': [{
                    'id': 'test-element',
                    'guid': 'elem-guid',
                    'labels': {'en': 'Old Label'},
                    'description': {},
                    'abbrevs': {}
                }]
            }
        })
        
        element_data: Dict[str, Any] = {
            'id': 'test-element',
            'guid': 'elem-guid',
            'labels': {
                'en': 'Updated Label',
                'pl': 'Zaktualizowana Etykieta'
            },
            'description': {},
            'abbrevs': {},
            'parent': '',
            'traits': {}
        }
        
        # Execute
        ranges_service.update_range_element('test-range', 'test-element', element_data)
        
        # Verify
        assert mock_connector.execute_update.call_count == 2  # delete + insert
        insert_call = mock_connector.execute_update.call_args_list[1][0][0]
        assert 'Updated Label' in insert_call
        assert 'Zaktualizowana Etykieta' in insert_call
    
    def test_update_element_all_multilingual_properties(
        self, ranges_service: RangesService, mock_connector: Mock
    ) -> None:
        """Should update all multilingual properties together."""
        # Setup
        mock_connector.execute_query.return_value = """
        <lift-ranges>
            <range id="test-range" guid="range-guid">
                <range-element id="test-element" guid="elem-guid">
                    <label><form lang="en"><text>Old</text></form></label>
                </range-element>
            </range>
        </lift-ranges>
        """
        
        ranges_service.ranges_parser.parse_string = Mock(return_value={
            'test-range': {
                'id': 'test-range',
                'guid': 'range-guid',
                'labels': {},
                'values': [{
                    'id': 'test-element',
                    'guid': 'elem-guid',
                    'labels': {'en': 'Old'},
                    'description': {},
                    'abbrevs': {}
                }]
            }
        })
        
        element_data: Dict[str, Any] = {
            'id': 'test-element',
            'guid': 'elem-guid',
            'labels': {
                'en': 'New Label EN',
                'pl': 'Nowa Etykieta PL'
            },
            'description': {
                'en': 'New Description EN',
                'pl': 'Nowy Opis PL'
            },
            'abbrevs': {
                'en': 'NL',
                'pl': 'NE'
            },
            'parent': '',
            'traits': {}
        }
        
        # Execute
        ranges_service.update_range_element('test-range', 'test-element', element_data)
        
        # Verify
        assert mock_connector.execute_update.call_count == 2
        insert_call = mock_connector.execute_update.call_args_list[1][0][0]
        assert 'New Label EN' in insert_call
        assert 'Nowa Etykieta PL' in insert_call
        assert 'New Description EN' in insert_call
        assert 'Nowy Opis PL' in insert_call
        assert 'NL' in insert_call
        assert 'NE' in insert_call


class TestMultilingualElementValidation:
    """Test validation of multilingual element properties."""
    
    def test_create_element_requires_id(
        self, ranges_service: RangesService, mock_connector: Mock
    ) -> None:
        """Should require element ID."""
        # Setup
        mock_connector.execute_query.return_value = """
        <lift-ranges>
            <range id="test-range">
            </range>
        </lift-ranges>
        """
        
        ranges_service.ranges_parser.parse_string = Mock(return_value={
            'test-range': {
                'id': 'test-range',
                'labels': {},
                'values': []
            }
        })
        
        element_data: Dict[str, Any] = {
            'labels': {'en': 'Test'},
            'description': {},
            'abbrevs': {}
        }
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="Element ID is required"):
            ranges_service.create_range_element('test-range', element_data)
    
    def test_create_element_duplicate_id_fails(
        self, ranges_service: RangesService, mock_connector: Mock
    ) -> None:
        """Should reject duplicate element IDs."""
        # Setup - element with same ID already exists
        mock_connector.execute_query.return_value = """
        <lift-ranges>
            <range id="test-range">
                <range-element id="duplicate-id">
                    <label><form lang="en"><text>Existing</text></form></label>
                </range-element>
            </range>
        </lift-ranges>
        """
        
        ranges_service.ranges_parser.parse_string = Mock(return_value={
            'test-range': {
                'id': 'test-range',
                'labels': {},
                'values': [{
                    'id': 'duplicate-id',
                    'labels': {'en': 'Existing'},
                    'description': {},
                    'abbrevs': {}
                }]
            }
        })
        
        element_data: Dict[str, Any] = {
            'id': 'duplicate-id',
            'labels': {'en': 'New'},
            'description': {},
            'abbrevs': {},
            'parent': '',
            'traits': {}
        }
        
        # Execute & Verify
        with pytest.raises(ValidationError, match="already exists"):
            ranges_service.create_range_element('test-range', element_data)


class TestMultilingualElementXMLGeneration:
    """Test XML generation for multilingual elements."""
    
    def test_build_element_with_multilingual_labels(
        self, ranges_service: RangesService
    ) -> None:
        """Should generate correct XML for multilingual labels."""
        element_data: Dict[str, Any] = {
            'id': 'test',
            'guid': 'test-guid',
            'labels': {
                'en': 'English',
                'pl': 'Polski'
            },
            'description': {},
            'abbrevs': {},
            'parent': '',
            'traits': {}
        }
        
        # Execute
        xml = ranges_service._build_range_element_xml(element_data)
        
        # Verify
        assert '<range-element' in xml
        assert 'id="test"' in xml
        assert 'guid="test-guid"' in xml
        assert '<label>' in xml
        assert '<form lang="en">' in xml
        assert '<form lang="pl">' in xml
        assert 'English' in xml
        assert 'Polski' in xml
    
    def test_build_element_with_multilingual_abbreviations(
        self, ranges_service: RangesService
    ) -> None:
        """Should generate correct XML for multilingual abbreviations."""
        element_data: Dict[str, Any] = {
            'id': 'test',
            'guid': 'test-guid',
            'labels': {},
            'description': {},
            'abbrevs': {
                'en': 'ENG',
                'pl': 'POL'
            },
            'parent': '',
            'traits': {}
        }
        
        # Execute
        xml = ranges_service._build_range_element_xml(element_data)
        
        # Verify
        assert '<abbrev>' in xml
        assert '<form lang="en">' in xml
        assert '<form lang="pl">' in xml
        assert 'ENG' in xml
        assert 'POL' in xml
    
    def test_build_element_with_all_multilingual_properties(
        self, ranges_service: RangesService
    ) -> None:
        """Should generate complete XML with all properties."""
        element_data: Dict[str, Any] = {
            'id': 'complete',
            'guid': 'complete-guid',
            'labels': {'en': 'Label', 'pl': 'Etykieta'},
            'description': {'en': 'Desc', 'pl': 'Opis'},
            'abbrevs': {'en': 'LBL', 'pl': 'ETY'},
            'parent': 'parent-id',
            'traits': {'color': 'red'}
        }
        
        # Execute
        xml = ranges_service._build_range_element_xml(element_data)
        
        # Verify
        assert 'id="complete"' in xml
        assert 'parent="parent-id"' in xml
        assert '<label>' in xml
        assert '<description>' in xml
        assert '<abbrev>' in xml
        assert '<trait name="color" value="red"' in xml
        assert 'Label' in xml
        assert 'Etykieta' in xml
        assert 'Desc' in xml
        assert 'Opis' in xml
        assert 'LBL' in xml
        assert 'ETY' in xml
