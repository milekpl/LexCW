#!/usr/bin/env python3

from __future__ import annotations

import pytest
import yaml
import os
from unittest.mock import patch, MagicMock


@pytest.mark.integration
def test_install_recommended_ranges_endpoint(app, client):
    # Patch the service to avoid touching the real DB
    with patch('app.services.dictionary_service.DictionaryService.install_recommended_ranges') as mock_install:
        mock_install.return_value = {'grammatical-info': {'id': 'grammatical-info', 'values': []}}

        resp = client.post('/api/ranges/install_recommended')
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True
    @pytest.mark.integration
    def test_create_project_and_wizard(client, app):
        # Create a new project via API and ensure it gets created
        payload = {
            'project_name': 'Wizard Test',
            'source_language_code': 'en',
            'source_language_name': 'English',
            'target_language_code': 'es',
            'target_language_name': 'Spanish',
            'install_recommended_ranges': False
        }
        resp = client.post('/settings/projects/create', json=payload)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True

        # Check projects page lists it
        resp2 = client.get('/settings/projects')
        html = resp2.data.decode('utf-8')
        assert 'Wizard Test' in html


@pytest.mark.integration
def test_entry_form_shows_ranges_missing_banner(app, client):
    # Simulate no ranges by patching get_ranges to return empty dict
    with patch('app.services.dictionary_service.DictionaryService.get_lift_ranges') as mock_get_ranges:
        mock_get_ranges.return_value = {}
        resp = client.get('/entries/add')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Ranges Not Configured' in html
        assert 'Install recommended ranges' in html or 'install-recommended-ranges-btn' in html


def test_install_recommended_when_ranges_exist(app, client):
    # Ensure installer is idempotent: when ranges already exist, the endpoint
    # should return success and the existing ranges rather than erroring.
    with patch('app.services.dictionary_service.DictionaryService.get_lift_ranges') as mock_get_ranges:
        mock_get_ranges.return_value = {'grammatical-info': {'id': 'grammatical-info', 'values': []}}
        resp = client.post('/api/ranges/install_recommended')
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['success'] is True
        assert 'data' in data
        assert 'grammatical-info' in data['data']


@pytest.mark.integration
def test_recommended_traits_yaml_content():
    """Test that recommended_traits.yaml has correct structure and content."""
    yaml_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'recommended_traits.yaml')
    
    # Verify file exists
    assert os.path.exists(yaml_path), f"recommended_traits.yaml not found at {yaml_path}"
    
    # Load and validate YAML content
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Verify structure
    assert 'variant-types' in data, "variant-types section missing from recommended_traits.yaml"
    assert 'complex-form-types' in data, "complex-form-types section missing from recommended_traits.yaml"
    assert 'recommended-traits' not in data, "recommended-traits should not be in YAML (they're in LIFT ranges)"
    
    # Verify variant-types content
    variant_types = data['variant-types']
    assert len(variant_types) > 0, "variant-types should not be empty"
    required_variant_ids = {'dialectal', 'free', 'irregular', 'spelling'}
    actual_variant_ids = {vt['id'] for vt in variant_types}
    assert required_variant_ids.issubset(actual_variant_ids), \
        f"Missing required variant types. Expected: {required_variant_ids}, Got: {actual_variant_ids}"
    
    # Verify complex-form-types content
    complex_form_types = data['complex-form-types']
    assert len(complex_form_types) > 0, "complex-form-types should not be empty"
    required_complex_ids = {'compound', 'derivative', 'idiom', 'phrasal-verb', 'contraction', 'saying'}
    actual_complex_ids = {cft['id'] for cft in complex_form_types}
    assert required_complex_ids.issubset(actual_complex_ids), \
        f"Missing required complex form types. Expected: {required_complex_ids}, Got: {actual_complex_ids}"
    
    # Verify each item has required fields
    for section_name, items in [('variant-types', variant_types), ('complex-form-types', complex_form_types)]:
        for item in items:
            assert 'id' in item, f"{section_name} item missing 'id': {item}"
            assert 'label' in item, f"{section_name} item missing 'label': {item}"
            assert 'definition' in item, f"{section_name} item missing 'definition': {item}"


@pytest.mark.integration
def test_minimal_lift_ranges_content():
    """Test that minimal.lift-ranges has required ranges and structure."""
    ranges_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'minimal.lift-ranges')
    
    # Verify file exists
    assert os.path.exists(ranges_path), f"minimal.lift-ranges not found at {ranges_path}"
    
    # Parse XML and verify structure
    import xml.etree.ElementTree as ET
    tree = ET.parse(ranges_path)
    root = tree.getroot()
    
    # Verify required ranges exist
    range_ids = {r.get('id') for r in root.findall('range')}
    required_ranges = {
        'grammatical-info', 'lexical-relation', 'complex-form-types', 
        'variant-type', 'usage-labels', 'recommended-traits'
    }
    assert required_ranges.issubset(range_ids), \
        f"Missing required ranges. Expected: {required_ranges}, Got: {range_ids}"
    
    # Verify grammatical-info has enhanced POS categories
    gram_info_range = root.find("range[@id='grammatical-info']")
    assert gram_info_range is not None, "grammatical-info range not found"
    pos_labels = {elem.findtext('label/form/text') for elem in gram_info_range.findall('range-element')}
    required_pos = {'Proper Noun', 'Auxiliary Verb', 'Adposition', 'Coordinating Conjunction'}
    assert required_pos.issubset(pos_labels), \
        f"Missing required POS categories. Expected: {required_pos}, Got: {pos_labels}"
    
    # Verify _component-lexeme relation exists
    lexical_relation_range = root.find("range[@id='lexical-relation']")
    assert lexical_relation_range is not None, "lexical-relation range not found"
    component_lexeme = lexical_relation_range.find("range-element[@id='_component-lexeme']")
    assert component_lexeme is not None, "_component-lexeme relation not found"
    
    # Verify recommended-traits doesn't have reverse-label
    traits_range = root.find("range[@id='recommended-traits']")
    assert traits_range is not None, "recommended-traits range not found"
    trait_names = {elem.get('value') for elem in traits_range.findall('.//trait[@name="trait-name"]')}
    assert 'reverse-label' not in trait_names, "reverse-label trait should not be in recommended-traits"
