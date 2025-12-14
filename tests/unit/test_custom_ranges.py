"""Unit tests for custom ranges functionality."""

import pytest
from unittest.mock import Mock, patch
from app.models.custom_ranges import CustomRange, CustomRangeValue
from app.services.ranges_service import RangesService


class TestCustomRangeModel:
    """Test CustomRange model."""

    def test_custom_range_creation(self):
        """Test creating a CustomRange instance."""
        custom_range = CustomRange(
            project_id=1,
            range_type='relation',
            range_name='lexical-relation',
            element_id='synonym',
            element_label='Synonym',
            element_description='A synonym relation'
        )

        assert custom_range.project_id == 1
        assert custom_range.range_type == 'relation'
        assert custom_range.range_name == 'lexical-relation'
        assert custom_range.element_id == 'synonym'
        assert custom_range.element_label == 'Synonym'
        assert custom_range.element_description == 'A synonym relation'

    def test_custom_range_to_dict(self):
        """Test CustomRange to_dict method."""
        custom_range = CustomRange(
            id=1,
            project_id=1,
            range_type='relation',
            range_name='lexical-relation',
            element_id='synonym',
            element_label='Synonym',
            element_description='A synonym relation'
        )

        data = custom_range.to_dict()
        assert data['id'] == 1
        assert data['project_id'] == 1
        assert data['range_type'] == 'relation'
        assert data['range_name'] == 'lexical-relation'
        assert data['element_id'] == 'synonym'
        assert data['element_label'] == 'Synonym'
        assert data['element_description'] == 'A synonym relation'
        assert 'values' in data


class TestCustomRangeValueModel:
    """Test CustomRangeValue model."""

    def test_custom_range_value_creation(self):
        """Test creating a CustomRangeValue instance."""
        value = CustomRangeValue(
            custom_range_id=1,
            value='synonym',
            label='Synonym',
            description='Synonym relation'
        )

        assert value.custom_range_id == 1
        assert value.value == 'synonym'
        assert value.label == 'Synonym'
        assert value.description == 'Synonym relation'

    def test_custom_range_value_to_dict(self):
        """Test CustomRangeValue to_dict method."""
        value = CustomRangeValue(
            id=1,
            custom_range_id=1,
            value='synonym',
            label='Synonym',
            description='Synonym relation'
        )

        data = value.to_dict()
        assert data['id'] == 1
        assert data['custom_range_id'] == 1
        assert data['value'] == 'synonym'
        assert data['label'] == 'Synonym'
        assert data['description'] == 'Synonym relation'


class TestRangesServiceCustomRanges:
    """Test RangesService custom ranges functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db_connector = Mock()
        self.service = RangesService(self.mock_db_connector)

    def test_load_custom_ranges(self):
        """Test loading custom ranges from database."""
        from unittest.mock import Mock
        # Safely replace class attribute without triggering the SQLAlchemy descriptor
        orig = CustomRange.__dict__.get('query', None)
        setattr(CustomRange, 'query', Mock())
        try:
            # Mock the query results
            mock_range = Mock()
            mock_range.range_name = 'lexical-relation'
            mock_range.values = [
                Mock(value='synonym', label='Synonym', description='A synonym'),
                Mock(value='antonym', label='Antonym', description='An antonym')
            ]

            CustomRange.query.filter_by.return_value.all.return_value = [mock_range]

            result = self.service._load_custom_ranges(1)

            assert 'lexical-relation' in result
            assert len(result['lexical-relation']) == 2
            assert result['lexical-relation'][0]['id'] == 'synonym'
            assert result['lexical-relation'][0]['label'] == 'Synonym'
            assert result['lexical-relation'][0]['custom'] is True
        finally:
            # Restore original attribute
            if orig is None:
                delattr(CustomRange, 'query')
            else:
                setattr(CustomRange, 'query', orig)

    def test_load_custom_ranges_empty(self):
        """Test loading custom ranges when none exist."""
        from unittest.mock import Mock
        orig = CustomRange.__dict__.get('query', None)
        setattr(CustomRange, 'query', Mock())
        try:
            CustomRange.query.filter_by.return_value.all.return_value = []

            result = self.service._load_custom_ranges(1)

            assert result == {}
        finally:
            if orig is None:
                delattr(CustomRange, 'query')
            else:
                setattr(CustomRange, 'query', orig)

    def test_load_custom_ranges_error(self):
        """Test loading custom ranges with database error."""
        from unittest.mock import Mock
        orig = CustomRange.__dict__.get('query', None)
        setattr(CustomRange, 'query', Mock())
        try:
            CustomRange.query.filter_by.side_effect = Exception("Database error")

            result = self.service._load_custom_ranges(1)

            assert result == {}
        finally:
            if orig is None:
                delattr(CustomRange, 'query')
            else:
                setattr(CustomRange, 'query', orig)

    def test_get_all_ranges_with_custom(self):
        """Test get_all_ranges includes custom ranges."""
        # Mock the database query to return empty ranges
        self.mock_db_connector.execute_query.return_value = None

        with patch.object(self.service, '_load_custom_ranges') as mock_load_custom:
            mock_load_custom.return_value = {
                'lexical-relation': [
                    {
                        'id': 'synonym',
                        'label': 'Synonym',
                        'description': 'A synonym',
                        'custom': True,
                        'range_id': 1
                    }
                ]
            }

            result = self.service.get_all_ranges(1)

            # Should have the custom range
            assert 'lexical-relation' in result
            assert len(result['lexical-relation']['values']) == 1
            assert result['lexical-relation']['values'][0]['id'] == 'synonym'
            assert result['lexical-relation']['values'][0]['custom'] is True


class TestUndefinedRangeDetection:
    """Test undefined range detection functionality."""

    def test_identify_undefined_ranges_relations(self):
        """Test identifying undefined relations in LIFT XML."""
        from app.parsers.undefined_ranges_parser import UndefinedRangesParser

        parser = UndefinedRangesParser()

        # Mock LIFT XML with undefined relation
        lift_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <lift>
            <entry id="test">
                <relation type="custom-relation" ref="other"/>
            </entry>
        </lift>"""

        # Mock ranges XML without the custom relation
        ranges_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <lift-ranges>
            <range id="lexical-relation">
                <range-element id="synonym"/>
            </range>
        </lift-ranges>"""

        # Mock list XML
        list_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <lists>
            <list id="custom-relation">
                <label>Custom Relation</label>
            </list>
        </lists>"""

        undefined_relations, undefined_traits = parser.identify_undefined_ranges(
            lift_xml, ranges_xml, list_xml
        )

        assert 'custom-relation' in undefined_relations
        assert len(undefined_relations) == 1

    def test_identify_undefined_ranges_traits(self):
        """Test identifying undefined traits in LIFT XML."""
        from app.parsers.undefined_ranges_parser import UndefinedRangesParser

        parser = UndefinedRangesParser()

        # Mock LIFT XML with undefined trait
        lift_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <lift>
            <entry id="test">
                <sense>
                    <trait name="custom-trait" value="custom-value"/>
                </sense>
            </entry>
        </lift>"""

        # Mock ranges XML without the custom trait
        ranges_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <lift-ranges>
            <range id="status">
                <range-element id="draft"/>
            </range>
        </lift-ranges>"""

        # Mock list XML
        list_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <lists>
            <list id="custom-trait">
                <label>Custom Trait</label>
                <item id="custom-value">
                    <label>Custom Value</label>
                </item>
            </list>
        </lists>"""

        undefined_relations, undefined_traits = parser.identify_undefined_ranges(
            lift_xml, ranges_xml, list_xml
        )

        assert 'custom-trait' in undefined_traits
        assert 'custom-value' in undefined_traits['custom-trait']
        assert len(undefined_traits) == 1