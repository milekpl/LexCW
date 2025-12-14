"""Integration tests for custom ranges import functionality."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from app.services.lift_import_service import LIFTImportService
from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector


class TestCustomRangesImportIntegration:
    """Integration tests for importing LIFT files with undefined ranges."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db_connector = Mock(spec=BaseXConnector)
        self.mock_db_connector.database = "test_db"
        self.mock_db_connector.is_connected.return_value = True

        self.dictionary_service = DictionaryService(self.mock_db_connector)

    @patch('app.services.lift_import_service.UndefinedRangesParser')
    @patch('app.models.custom_ranges.db')
    def test_import_with_undefined_relations(self, mock_db, mock_parser_class):
        """Test importing LIFT file with undefined relations creates custom ranges."""
        # Mock the parser to return undefined relations
        mock_parser = Mock()
        mock_parser.identify_undefined_ranges.return_value = (
            {'custom-relation'},  # undefined relations
            {}  # undefined traits
        )
        mock_parser_class.return_value = mock_parser

        # Mock the list XML parsing
        with patch.object(LIFTImportService, '_get_list_values') as mock_get_list:
            mock_get_list.return_value = {}

            import_service = LIFTImportService(self.mock_db_connector)

            # Mock LIFT, ranges, and list XML content
            lift_xml = """<?xml version="1.0" encoding="UTF-8"?>
            <lift>
                <entry id="test">
                    <relation type="custom-relation" ref="other"/>
                </entry>
            </lift>"""

            ranges_xml = """<?xml version="1.0" encoding="UTF-8"?>
            <lift-ranges>
                <range id="lexical-relation">
                    <range-element id="synonym"/>
                </range>
            </lift-ranges>"""

            list_xml = """<?xml version="1.0" encoding="UTF-8"?>
            <lists></lists>"""

            # Mock the database session
            mock_session = Mock()
            mock_db.session = mock_session

            # Call the import method
            import_service.create_custom_ranges(
                project_id=1,
                undefined_relations={'custom-relation'},
                undefined_traits={},
                list_xml=list_xml
            )

            # Verify that a CustomRange was created
            assert mock_session.add.called
            assert mock_session.flush.called

            # Get the added object
            added_objects = [call[0][0] for call in mock_session.add.call_args_list]
            assert len(added_objects) >= 1

            # Check the CustomRange object
            custom_range = added_objects[0]
            assert custom_range.project_id == 1
            assert custom_range.range_type == 'relation'
            assert custom_range.range_name == 'lexical-relation'
            assert custom_range.element_id == 'custom-relation'
            assert custom_range.element_label == 'custom-relation'

            # Check that CustomRangeValue was also added
            assert len(added_objects) >= 2
            custom_value = added_objects[1]
            assert custom_value.custom_range_id == custom_range.id
            assert custom_value.value == 'custom-relation'
            assert custom_value.label == 'custom-relation'

            # Verify commit was called
            assert mock_session.commit.called

    @patch('app.services.lift_import_service.UndefinedRangesParser')
    @patch('app.models.custom_ranges.db')
    def test_import_with_undefined_traits(self, mock_db, mock_parser_class):
        """Test importing LIFT file with undefined traits creates custom ranges."""
        # Mock the parser to return undefined traits
        mock_parser = Mock()
        mock_parser.identify_undefined_ranges.return_value = (
            set(),  # undefined relations
            {'custom-trait': {'value1', 'value2'}}  # undefined traits
        )
        mock_parser_class.return_value = mock_parser

        # Mock the list XML parsing
        with patch.object(LIFTImportService, '_get_list_values') as mock_get_list:
            mock_get_list.return_value = {
                'value1': {'label': 'Value One'},
                'value2': {'label': 'Value Two'}
            }

            import_service = LIFTImportService(self.mock_db_connector)

            list_xml = """<?xml version="1.0" encoding="UTF-8"?>
            <lists>
                <list id="custom-trait">
                    <item id="value1">
                        <label> Value One </label>
                    </item>
                    <item id="value2">
                        <label> Value Two </label>
                    </item>
                </list>
            </lists>"""

            # Mock the database session
            mock_session = Mock()
            mock_db.session = mock_session

            # Call the import method
            import_service.create_custom_ranges(
                project_id=1,
                undefined_relations=set(),
                undefined_traits={'custom-trait': {'value1', 'value2'}},
                list_xml=list_xml
            )

            # Verify that objects were added
            assert mock_session.add.called
            assert mock_session.flush.called

            # Get the added objects
            added_objects = [call[0][0] for call in mock_session.add.call_args_list]

            # Should have CustomRange + 2 CustomRangeValues
            assert len(added_objects) == 3

            # Check the CustomRange object
            custom_range = added_objects[0]
            assert custom_range.project_id == 1
            assert custom_range.range_type == 'trait'
            assert custom_range.range_name == 'custom-trait'
            assert custom_range.element_id == 'custom-trait'

            # Check the CustomRangeValues
            custom_values = added_objects[1:]
            assert len(custom_values) == 2

            # Values should be created for each trait value
            value_ids = {cv.value for cv in custom_values}
            assert value_ids == {'value1', 'value2'}

            # Labels should be taken from list XML
            value_labels = {cv.label for cv in custom_values}
            assert value_labels == {'Value One', 'Value Two'}

            # Verify commit was called
            assert mock_session.commit.called

    @patch('app.services.dictionary_service.RangesService')
    @patch('app.services.dictionary_service.LIFTExportService')
    def test_export_includes_custom_ranges(self, mock_export_service_class, mock_ranges_service_class):
        """Test that export includes custom ranges."""
        # Mock the services
        mock_ranges_service = Mock()
        mock_ranges_service_class.return_value = mock_ranges_service

        mock_export_service = Mock()
        mock_export_service_class.return_value = mock_export_service

        # Mock database connector
        self.mock_db_connector.execute_query.return_value = '<lift><entry id="test"/></lift>'
        self.mock_db_connector.execute_command.return_value = None

        # Call export
        result = self.dictionary_service.export_lift(project_id=1)

        # Verify that export service was created and used
        mock_export_service_class.assert_called_once()
        mock_export_service.export_ranges_file.assert_called_once_with(1, mock_export_service.export_ranges_file.call_args[0][1])

        # Verify result is returned
        assert result == '<lift><entry id="test"/></lift>'

    def test_dictionary_service_get_ranges_with_custom(self):
        """Test that dictionary service get_ranges includes custom ranges."""
        # Mock the database query to return empty ranges
        self.mock_db_connector.execute_query.return_value = None

        with patch('app.services.dictionary_service.RangesService') as mock_ranges_service_class:
            mock_ranges_service = Mock()
            mock_ranges_service_class.return_value = mock_ranges_service
            mock_ranges_service._load_custom_ranges.return_value = {
                'lexical-relation': [
                    {
                        'id': 'custom-rel',
                        'label': 'Custom Relation',
                        'description': 'A custom relation',
                        'custom': True
                    }
                ]
            }

            result = self.dictionary_service.get_ranges(project_id=1)

            # Should include custom ranges
            assert 'lexical-relation' in result
            assert len(result['lexical-relation']['values']) == 1
            assert result['lexical-relation']['values'][0]['id'] == 'custom-rel'
            assert result['lexical-relation']['values'][0]['custom'] is True