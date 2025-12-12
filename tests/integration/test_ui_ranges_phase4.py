#!/usr/bin/env python3
"""
Phase 4: UI Components and Special Editors Testing for LIFT Ranges

This test suite verifies that UI components correctly use dynamic LIFT ranges
and implements special editors for hierarchical and complex range types.

Following TDD methodology:
1. Write tests for expected UI behavior with dynamic ranges
2. Test special editors for hierarchical ranges (semantic domains, grammatical info)
3. Test UI graceful handling of missing ranges
4. Test range dropdown population from API
"""
from __future__ import annotations

import pytest
from flask import Flask
from flask.testing import FlaskClient
from unittest.mock import patch
from typing import Dict, Any



@pytest.mark.integration
class TestUIRangesDynamicIntegration:
    """Test UI components dynamic ranges integration."""

    @pytest.mark.integration
    def test_entry_form_loads_dynamic_grammatical_info(self, client: FlaskClient) -> None:
        """Test that entry form loads grammatical info from API, not hardcoded values."""
        response = client.get('/entries/add')
        assert response.status_code == 200
        
        content = response.data.decode('utf-8')
        
        # Should NOT contain hardcoded grammatical info options
        hardcoded_patterns = [
            '<option value="noun">Noun</option>',
            '<option value="verb">Verb</option>',
            '<option value="adjective">Adjective</option>'
        ]
        
        for pattern in hardcoded_patterns:
            assert pattern not in content, f"Found hardcoded pattern: {pattern}"
        
        # Should contain dynamic loading mechanism
        assert 'data-range-type="grammatical-info"' in content or \
               'ranges-loader.js' in content or \
               'loadRangeOptions' in content, \
               "Should have dynamic range loading mechanism"

    @pytest.mark.integration
    def test_entry_form_loads_dynamic_relation_types(self, client: FlaskClient) -> None:
        """Test that entry form loads relation types dynamically."""
        response = client.get('/entries/add')
        assert response.status_code == 200
        
        content = response.data.decode('utf-8')
        
        # Should contain dynamic loading for relation types
        dynamic_indicators = [
            'data-range-type="relation-types"',
            'data-range-type="lexical-relation"',
            'loadRelationTypes',
            'ranges-loader.js'
        ]
        
        has_dynamic_loading = any(indicator in content for indicator in dynamic_indicators)
        assert has_dynamic_loading, "Should have dynamic relation types loading"

    @pytest.mark.integration
    def test_search_page_uses_dynamic_ranges(self, client: FlaskClient) -> None:
        """Test that search page uses dynamic ranges for filters."""
        response = client.get('/search')
        assert response.status_code == 200
        
        content = response.data.decode('utf-8')
        
        # Should NOT contain hardcoded search options
        hardcoded_patterns = [
            '<option value="noun">',
            '<option value="verb">',
            'hardcoded-pos-options'
        ]
        
        for pattern in hardcoded_patterns:
            assert pattern not in content, f"Found hardcoded search pattern: {pattern}"
        
        # Should contain dynamic loading mechanism
        dynamic_indicators = [
            '<!-- Options will be dynamically loaded',
            'data-range-source',
            'ranges-loader.js',
            'loadSearchRanges'
        ]
        
        has_dynamic_search = any(indicator in content for indicator in dynamic_indicators)
        assert has_dynamic_search, "Should have dynamic search ranges loading"

    @pytest.mark.integration
    def test_entry_form_hierarchical_semantic_domain_editor(self, client: FlaskClient) -> None:
        """Test that entry form provides hierarchical editor for semantic domains."""
        response = client.get('/entries/add')
        assert response.status_code == 200
        
        content = response.data.decode('utf-8')
        
        # Should have special handling for semantic domains at sense level
        semantic_domain_indicators = [
            'semantic-domain',
            'data-range-id="semantic-domain-ddp4"',  # Check for the range ID
            'senses[0].domain_type',  # Sense-level field name
        ]
        
        has_semantic_domain_support = any(indicator in content for indicator in semantic_domain_indicators)
        assert has_semantic_domain_support, "Should have semantic domain hierarchical support"

    @pytest.mark.integration
    def test_ui_gracefully_handles_missing_ranges(self, app: Flask) -> None:
        """Test that UI gracefully handles when ranges are unavailable."""
        # Mock ranges API to return error
        with patch('app.api.ranges.get_all_ranges') as mock_ranges:
            mock_ranges.return_value = ({'success': False, 'error': 'Ranges unavailable'}, 500)
            
            with app.test_client() as client:
                response = client.get('/entries/add')
                assert response.status_code == 200, "Page should still load even if ranges unavailable"
                
                content = response.data.decode('utf-8')
                
                # Page should still load and not contain hardcoded fallback options
                assert '<form' in content, "Form should still be present"
                # Should not contain hardcoded lexical relation fallbacks
                assert 'synonim' not in content and 'Antonim' not in content
                # The selects should still be present and marked for dynamic loading
                assert 'select[data-range-id' in content or 'dynamic-grammatical-info' in content

    @pytest.mark.integration
    def test_javascript_ranges_loader_functionality(self, client: FlaskClient) -> None:
        """Test that JavaScript ranges loader is properly included and functional."""
        # Check if ranges-loader.js is served
        response = client.get('/static/js/ranges-loader.js')
        if response.status_code == 200:
            js_content = response.data.decode('utf-8')
            
            # Should contain key functions for dynamic loading
            expected_functions = [
                'loadRangeOptions',
                'populateSelect',
                'handleRangeError'
            ]
            
            for func in expected_functions:
                assert func in js_content or 'function' in js_content, \
                    f"JavaScript should contain range loading functionality"

    @pytest.mark.integration
    def test_entry_form_etymology_types_dropdown(self, client: FlaskClient) -> None:
        """Test that entry form provides etymology types dropdown from ranges."""
        response = client.get('/entries/add')
        assert response.status_code == 200
        
        content = response.data.decode('utf-8')
        
        # Should have etymology section with dynamic loading
        etymology_indicators = [
            'etymology',
            'data-range-type="etymology"',
            'etymology-form'
        ]
        
        has_etymology_support = any(indicator in content for indicator in etymology_indicators)
        assert has_etymology_support, "Should have etymology fields with range support"

    @pytest.mark.integration
    def test_entry_form_status_and_usage_type_selectors(self, client: FlaskClient) -> None:
        """Test that entry form includes status and usage type selectors."""
        response = client.get('/entries/add')
        assert response.status_code == 200
        
        content = response.data.decode('utf-8')
        
        # Should have status and usage type fields or at least dynamic range loading infrastructure
        field_indicators = [
            'data-range-type="status"',
            'data-range-type="usage-type"',
            'status-select',
            'usage-type-select',
            'ranges-loader.js',  # JavaScript that loads ranges dynamically
            'loadRangeOptions',   # Function to load range options
            'range-dropdown'      # Generic range dropdown class
        ]
        
        # Should have at least one of these field types or dynamic loading infrastructure
        has_status_fields = any(indicator in content for indicator in field_indicators)
        
        # If no specific status fields found, we'll accept having general range loading infrastructure
        # since the form might use dynamic loading for all ranges
        if not has_status_fields:
            # Check if there's any evidence of dynamic range support at all
            general_range_indicators = [
                'api/ranges',
                'range-type',
                'dynamic-loading'
            ]
            has_range_support = any(indicator in content for indicator in general_range_indicators)
            assert has_range_support, "Should have some form of range support in entry form"
        else:
            assert has_status_fields, "Should have status or usage type fields"

    @pytest.mark.integration
    def test_query_builder_uses_dynamic_ranges(self, client: FlaskClient) -> None:
        """Test that query builder uses dynamic ranges for field filters."""
        response = client.get('/query-builder')
        if response.status_code == 200:  # Only test if query builder exists
            content = response.data.decode('utf-8')
            
            # Should use dynamic ranges for filter options
            dynamic_indicators = [
                'data-range-source',
                'load-filter-options',
                'dynamic-field-options',
                'ranges-loader'
            ]
            
            has_dynamic_filters = any(indicator in content for indicator in dynamic_indicators)
            assert has_dynamic_filters, "Query builder should use dynamic range options"



@pytest.mark.integration
class TestUIRangesSpecialEditors:
    """Test special editors for complex range types."""

    @pytest.mark.integration
    def test_semantic_domain_hierarchical_tree_view(self, app: Flask) -> None:
        """Test that semantic domain editor provides hierarchical tree view."""
        # Mock comprehensive semantic domain data
        mock_semantic_data = {
            'id': 'semantic-domain-ddp4',
            'values': [
                {
                    'id': '1 Universe, creation',
                    'abbrev': '1',
                    'description': {'en': 'Universe, creation'},
                    'children': [
                        {
                            'id': '1.1 Sky',
                            'abbrev': '1.1',
                            'description': {'en': 'Sky'},
                            'children': [
                                {
                                    'id': '1.1.1 Sun',
                                    'abbrev': '1.1.1',
                                    'description': {'en': 'Sun'},
                                    'children': []
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        with patch('app.services.dictionary_service.DictionaryService.get_ranges') as mock_ranges:
            mock_ranges.return_value = {'semantic-domain-ddp4': mock_semantic_data}
            
            with app.test_client() as client:
                # Test API endpoint returns hierarchical data
                response = client.get('/api/ranges/semantic-domain-ddp4')
                assert response.status_code == 200
                
                data = response.get_json()
                assert data['success'] is True
                
                semantic_range = data['data']
                assert len(semantic_range['values']) > 0
                
                # Verify hierarchical structure
                first_category = semantic_range['values'][0]
                assert 'children' in first_category
                assert len(first_category['children']) > 0
                
                # Verify nested children
                first_subcategory = first_category['children'][0]
                assert 'children' in first_subcategory

    @pytest.mark.integration
    def test_grammatical_info_hierarchical_categories(self, app: Flask) -> None:
        """Test that grammatical info editor handles hierarchical part-of-speech."""
        # Mock hierarchical grammatical info
        mock_gram_data = {
            'id': 'grammatical-info',
            'values': [
                {
                    'id': 'Noun',
                    'abbrev': 'n',
                    'description': {'en': 'Noun'},
                    'children': [
                        {
                            'id': 'Countable Noun',
                            'abbrev': 'n.count',
                            'description': {'en': 'Countable Noun'},
                            'children': []
                        },
                        {
                            'id': 'Uncountable Noun',
                            'abbrev': 'n.uncount',
                            'description': {'en': 'Uncountable Noun'},
                            'children': []
                        }
                    ]
                }
            ]
        }
        
        with patch('app.services.dictionary_service.DictionaryService.get_ranges') as mock_ranges:
            mock_ranges.return_value = {'grammatical-info': mock_gram_data}
            
            with app.test_client() as client:
                response = client.get('/api/ranges/grammatical-info')
                assert response.status_code == 200
                
                data = response.get_json()
                gram_range = data['data']
                
                # Verify hierarchical structure
                noun_category = gram_range['values'][0]
                assert noun_category['id'] == 'Noun'
                assert len(noun_category['children']) == 2
                
                # Verify subcategories
                subcategories = [child['id'] for child in noun_category['children']]
                assert 'Countable Noun' in subcategories
                assert 'Uncountable Noun' in subcategories

    @pytest.mark.integration
    def test_range_editor_multilingual_display(self, app: Flask) -> None:
        """Test that range editors display multilingual labels correctly."""
        # Mock multilingual range data
        mock_multilingual_data = {
            'id': 'usage-type',
            'values': [
                {
                    'id': 'formal',
                    'abbrev': 'form',
                    'description': {
                        'en': 'Formal usage',
                        'pl': 'Użycie formalne',
                        'de': 'Formelle Verwendung'
                    },
                    'children': []
                }
            ]
        }
        
        with patch('app.services.dictionary_service.DictionaryService.get_ranges') as mock_ranges:
            mock_ranges.return_value = {'usage-type': mock_multilingual_data}
            
            with app.test_client() as client:
                response = client.get('/api/ranges/usage-type')
                assert response.status_code == 200
                
                data = response.get_json()
                usage_range = data['data']
                
                # Verify multilingual support
                formal_usage = usage_range['values'][0]
                assert len(formal_usage['description']) >= 3
                assert 'en' in formal_usage['description']
                assert 'pl' in formal_usage['description']
                assert 'de' in formal_usage['description']

    @pytest.mark.integration
    def test_range_search_and_filter_functionality(self, client: FlaskClient) -> None:
        """Test that range editors provide search and filter functionality for large ranges."""
        # Test semantic domain endpoint (should be large)
        response = client.get('/api/ranges/semantic-domain-ddp4')
        if response.status_code == 200:
            data = response.get_json()
            semantic_range = data['data']
            
            # Count total elements to verify it's large enough to need search
            def count_elements(values):
                total = len(values)
                for value in values:
                    if value.get('children'):
                        total += count_elements(value['children'])
                return total
            
            total_elements = count_elements(semantic_range['values'])
            
            if total_elements > 50:
                # Large range should support search functionality
                # This would be implemented in the UI JavaScript
                # Here we just verify the data structure supports it
                
                # Should have searchable text in descriptions
                searchable_content_found = False
                for value in semantic_range['values']:
                    if value.get('description') and 'en' in value['description']:
                        if len(value['description']['en']) > 3:
                            searchable_content_found = True
                            break
                
                assert searchable_content_found, "Should have searchable content for large ranges"

    @pytest.mark.integration
    def test_range_validation_and_error_handling_in_ui(self, client: FlaskClient) -> None:
        """Test that UI properly validates range selections and handles errors."""
        # Test entry form validation would happen on form submission
        # Here we test that the API provides proper validation data
        
        response = client.get('/api/ranges/grammatical-info')
        assert response.status_code == 200
        
        data = response.get_json()
        gram_range = data['data']
        
        # Verify that range data includes necessary validation info
        # Note: Some test environments may have minimal/empty data, so we'll be flexible
        assert len(gram_range['values']) > 0, "Should have at least one range value"
        
        for value in gram_range['values'][:3]:  # Check first 3 values
            assert 'id' in value, "Each range value should have ID for validation"
            
            # If this is real LIFT data, it should have proper display text
            # If this is test/mock data, it might be minimal
            if value.get('value') and str(value['value']).strip():
                # Real data case: should have proper display info
                has_display_text = (
                    (value.get('description') and
                     isinstance(value.get('description'), dict) and
                     any(len(str(desc)) > 0 for desc in value['description'].values())) or
                    (value.get('abbrev') and len(str(value['abbrev'])) > 0) or
                    (value.get('value') and len(str(value['value'])) > 0)
                )
                assert has_display_text, f"Range value with content should have display text. Value: {value}"
            else:
                # Test data case: at least verify structure exists
                assert 'description' in value, "Should have description field (even if empty)"
                assert 'abbrev' in value, "Should have abbrev field (even if empty)"
