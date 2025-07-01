#!/usr/bin/env python3

"""
Tests for cross-reference query functionality.
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock
from typing import Dict, Any, List

from app.services.query_builder_service import QueryBuilderService


class TestCrossReferenceQueries:
    """Test cross-reference query parsing and validation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = QueryBuilderService()
    
    def test_parse_cross_reference_syntax(self):
        """Test parsing of [ELEMENT n:field] syntax."""
        query_data = {
            'filters': [
                {
                    'field': 'lexical_unit',
                    'operator': 'equals',
                    'value': 'test'
                },
                {
                    'field': 'etymology.source',
                    'operator': 'similar_to',
                    'value': '[ELEMENT 1:lexical_unit]'
                }
            ]
        }
        
        # Parse cross-references
        parsed_filters = self.service._parse_cross_references(query_data['filters'])
        
        # First filter should remain unchanged
        assert parsed_filters[0]['value'] == 'test'
        
        # Second filter should have parsed cross-reference
        assert isinstance(parsed_filters[1]['value'], dict)
        assert parsed_filters[1]['value']['type'] == 'element_reference'
        assert parsed_filters[1]['value']['element_index'] == 1
        assert parsed_filters[1]['value']['field'] == 'lexical_unit'
    
    def test_validate_cross_reference_exists(self):
        """Test validation that referenced elements exist."""
        query_data = {
            'filters': [
                {
                    'field': 'lexical_unit',
                    'operator': 'equals',
                    'value': 'test'
                },
                {
                    'field': 'etymology.source',
                    'operator': 'similar_to',
                    'value': '[ELEMENT 3:lexical_unit]'  # References non-existent element
                }
            ]
        }
        
        result = self.service.validate_query(query_data)
        
        assert not result['valid']
        assert any('Element 3 does not exist' in error for error in result['validation_errors'])
    
    def test_validate_cross_reference_field_compatibility(self):
        """Test validation of field compatibility between referenced elements."""
        query_data = {
            'filters': [
                {
                    'field': 'lexical_unit',
                    'operator': 'equals',
                    'value': 'test'
                },
                {
                    'field': 'pronunciation.ipa',
                    'operator': 'equals',
                    'value': '[ELEMENT 1:lexical_unit]'
                }
            ]
        }
        
        result = self.service.validate_query(query_data)
        
        # Should be valid - both are text fields
        assert result['valid']
    
    def test_cross_reference_circular_dependency(self):
        """Test detection of circular dependencies in cross-references."""
        query_data = {
            'filters': [
                {
                    'field': 'lexical_unit',
                    'operator': 'equals',
                    'value': '[ELEMENT 2:etymology.source]'
                },
                {
                    'field': 'etymology.source',
                    'operator': 'similar_to',
                    'value': '[ELEMENT 1:lexical_unit]'
                }
            ]
        }
        
        result = self.service.validate_query(query_data)
        
        assert not result['valid']
        assert any('Circular dependency detected' in error for error in result['validation_errors'])
    
    def test_cross_reference_execution_order(self):
        """Test that filters are executed in proper dependency order."""
        query_data = {
            'filters': [
                {
                    'field': 'etymology.source',
                    'operator': 'similar_to',
                    'value': '[ELEMENT 2:lexical_unit]'
                },
                {
                    'field': 'lexical_unit',
                    'operator': 'equals',
                    'value': 'test'
                }
            ]
        }
        
        # Mock dictionary service
        mock_dict_service = Mock()
        mock_dict_service.search_entries.return_value = ([], 0)
        
        # Should reorder filters to resolve dependencies
        execution_plan = self.service._plan_execution_order(query_data['filters'])
        
        # Element 2 (index 1) should be executed before element 1 (index 0)
        assert execution_plan[0]['original_index'] == 1
        assert execution_plan[1]['original_index'] == 0
    
    def test_complex_cross_reference_query(self):
        """Test complex query with multiple cross-references."""
        query_data = {
            'filters': [
                {
                    'field': 'lexical_unit',
                    'operator': 'contains',
                    'value': 'root'
                },
                {
                    'field': 'etymology.source',
                    'operator': 'similar_to',
                    'value': '[ELEMENT 1:lexical_unit]'
                },
                {
                    'field': 'sense.definition',
                    'operator': 'contains',
                    'value': '[ELEMENT 1:lexical_unit]'
                }
            ]
        }
        
        result = self.service.validate_query(query_data)
        
        # Should be valid - no circular dependencies
        assert result['valid']
        
        # Should identify cross-references correctly
        parsed_filters = self.service._parse_cross_references(query_data['filters'])
        assert isinstance(parsed_filters[1]['value'], dict)
        assert isinstance(parsed_filters[2]['value'], dict)
    
    def test_invalid_cross_reference_syntax(self):
        """Test handling of invalid cross-reference syntax."""
        invalid_references = [
            '[ELEMENT abc:field]',  # Non-numeric index
            '[ELEMENT 1]',          # Missing field
            '[ELEMENT :field]',     # Missing index
            '[INVALID 1:field]',    # Wrong prefix
            'ELEMENT 1:field]',     # Missing opening bracket
            '[ELEMENT 1:field',     # Missing closing bracket
        ]
        
        for invalid_ref in invalid_references:
            query_data = {
                'filters': [
                    {
                        'field': 'lexical_unit',
                        'operator': 'equals',
                        'value': 'test'
                    },
                    {
                        'field': 'etymology.source',
                        'operator': 'similar_to',
                        'value': invalid_ref
                    }
                ]
            }
            
            result = self.service.validate_query(query_data)
            
            if invalid_ref.startswith('[ELEMENT'):
                assert not result['valid'], f"Should reject invalid syntax: {invalid_ref}"
            else:
                # Non-cross-reference values should be treated as literals
                assert result['valid'], f"Should treat as literal: {invalid_ref}"


class TestCrossReferenceUI:
    """Test cross-reference UI functionality."""
    
    def test_element_reference_dropdown_population(self):
        """Test that element reference dropdown shows available elements."""
        # This would test JavaScript functionality
        # For now, we'll test the backend data needed for the UI
        
        query_data = {
            'filters': [
                {
                    'field': 'lexical_unit',
                    'operator': 'equals',
                    'value': 'test'
                },
                {
                    'field': 'etymology.source',
                    'operator': 'similar_to',
                    'value': ''
                }
            ]
        }
        
        service = QueryBuilderService()
        available_refs = service.get_available_references(query_data['filters'], current_index=1)
        
        # Should return element 1 as available reference
        assert len(available_refs) == 1
        assert available_refs[0]['index'] == 1
        assert available_refs[0]['field'] == 'lexical_unit'
        assert available_refs[0]['display'] == 'Element 1: lexical_unit'
    
    def test_cross_reference_value_substitution(self):
        """Test UI helper for showing cross-reference values."""
        service = QueryBuilderService()
        
        cross_ref = {
            'type': 'element_reference',
            'element_index': 1,
            'field': 'lexical_unit'
        }
        
        display_value = service.format_cross_reference_display(cross_ref)
        assert display_value == '[ELEMENT 1:lexical_unit]'
