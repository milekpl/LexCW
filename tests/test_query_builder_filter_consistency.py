#!/usr/bin/env python3

"""
Unit tests to ensure filter condition consistency in query builder.
Tests that dynamically added filters have same options as the first filter.
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient
from bs4 import BeautifulSoup


class TestQueryBuilderFilterConsistency:
    """Test that all filter conditions have identical options."""

    def test_initial_filter_has_comprehensive_fields(self, client: FlaskClient) -> None:
        """Test that the initial filter condition has all expected field options."""
        response = client.get('/workbench/query-builder')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.get_data(as_text=True), 'html.parser')
        
        # Find the first field select
        first_field_select = soup.find('select', class_='field-select')
        assert first_field_select is not None
        
        # Extract all option values
        field_options = [option.get('value') for option in first_field_select.find_all('option')]
        
        # Verify we have comprehensive LIFT schema coverage
        expected_fields = [
            # Entry fields
            'lexical_unit', 'headword', 'grammatical_info', 'pos', 
            'pronunciation', 'pronunciation.ipa', 'citation', 'note',
            
            # Etymology fields
            'etymology.source', 'etymology.type', 'etymology.form', 'etymology.gloss',
            
            # Relation fields
            'relation.type', 'relation.ref',
            
            # Variant fields
            'variant.form', 'variant.type',
            
            # Sense fields
            'sense.definition', 'sense.gloss', 'sense.grammatical_info',
            'sense.semantic_domain', 'sense.note', 'sense.example', 'sense.example.translation',
            
            # Advanced/similarity fields
            'similar_headword', 'contains_headword', 'normalized_headword',
            'duplicate_candidate', 'compound_component'
        ]
        
        for expected_field in expected_fields:
            assert expected_field in field_options, f"Missing field option: {expected_field}"

    def test_initial_filter_has_comprehensive_operators(self, client: FlaskClient) -> None:
        """Test that the initial filter condition has all expected operator options."""
        response = client.get('/workbench/query-builder')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.get_data(as_text=True), 'html.parser')
        
        # Find the first operator select
        first_operator_select = soup.find('select', class_='operator-select')
        assert first_operator_select is not None
        
        # Extract all option values
        operator_options = [option.get('value') for option in first_operator_select.find_all('option')]
        
        # Verify we have comprehensive operator coverage
        expected_operators = [
            # Basic string operators
            'equals', 'contains', 'starts_with', 'ends_with', 
            'not_equals', 'not_contains', 'regex',
            
            # Numerical operators
            'greater_than', 'less_than', 'greater_equal', 'less_equal',
            
            # List operators
            'in', 'not_in', 'contains_any', 'contains_all',
            
            # Similarity operators
            'similar_to', 'fuzzy_match', 'normalized_equals', 
            'levenshtein_distance', 'phonetic_similar',
            
            # Cross-entry operators
            'headword_contained_in', 'contains_as_component', 
            'shares_root_with', 'same_pos_as',
            
            # Existence operators
            'exists', 'not_exists', 'is_empty', 'is_not_empty'
        ]
        
        for expected_operator in expected_operators:
            assert expected_operator in operator_options, f"Missing operator option: {expected_operator}"

    def test_javascript_creates_identical_filter_options(self, client: FlaskClient) -> None:
        """Test that the JavaScript addFilterCondition function preserves all options."""
        response = client.get('/workbench/query-builder')
        assert response.status_code == 200
        
        html = response.get_data(as_text=True)
        
        # Verify the JavaScript function exists and uses innerHTML copying
        assert 'firstFieldSelect.innerHTML' in html, "JavaScript should copy field options from first select"
        assert 'firstOperatorSelect.innerHTML' in html, "JavaScript should copy operator options from first select"
        assert 'fieldOptionsHtml' in html, "JavaScript should use copied field options"
        assert 'operatorOptionsHtml' in html, "JavaScript should use copied operator options"

    def test_no_hardcoded_options_in_javascript(self, client: FlaskClient) -> None:
        """Test that JavaScript doesn't have hardcoded limited options."""
        response = client.get('/workbench/query-builder')
        assert response.status_code == 200
        
        html = response.get_data(as_text=True)
        
        # These were the old hardcoded options that should NOT be in the addFilterCondition function
        bad_patterns = [
            'value="lexical_unit">Lexical Unit</option>',
            'value="pos">Part of Speech</option>',
            'value="semantic_domain">Semantic Domain</option>',
            'value="etymologies">Etymology</option>',
            'value="pronunciation">Pronunciation</option>',
            'value="definition">Definition</option>'
        ]
        
        # Extract just the addFilterCondition function
        start_marker = 'function addFilterCondition() {'
        end_marker = 'updateQueryPreview();\n        }'
        
        start_index = html.find(start_marker)
        end_index = html.find(end_marker, start_index) + len(end_marker)
        
        if start_index != -1 and end_index != -1:
            function_content = html[start_index:end_index]
            
            for bad_pattern in bad_patterns:
                assert bad_pattern not in function_content, f"Found hardcoded option in JavaScript: {bad_pattern}"

    def test_optgroup_structure_preservation(self, client: FlaskClient) -> None:
        """Test that optgroup structure is preserved in dynamic filters."""
        response = client.get('/workbench/query-builder')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.get_data(as_text=True), 'html.parser')
        
        # Find the first field select
        first_field_select = soup.find('select', class_='field-select')
        assert first_field_select is not None
        
        # Verify optgroups exist
        optgroups = first_field_select.find_all('optgroup')
        assert len(optgroups) > 0, "Should have optgroups for field organization"
        
        # Verify key optgroups exist
        optgroup_labels = [optgroup.get('label') for optgroup in optgroups]
        expected_groups = ['Entry Fields', 'Etymology', 'Relations', 'Variants', 'Sense Fields', 'Advanced/Similarity']
        
        for expected_group in expected_groups:
            assert expected_group in optgroup_labels, f"Missing optgroup: {expected_group}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
