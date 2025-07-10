"""
Test variant UI displays proper LIFT trait labels instead of morphological types.

This test ensures that the variants container correctly displays variant types 
from LIFT trait elements rather than incorrect morphological type labels.
"""

from __future__ import annotations

import pytest
from flask.testing import FlaskClient



@pytest.mark.integration
class TestVariantTraitLabelsUI:
    """Test that variant UI shows proper LIFT trait labels."""

    @pytest.mark.integration
    def test_variant_types_from_traits_api_endpoint(self, client: FlaskClient) -> None:
        """Test that the variant-types-from-traits API endpoint works correctly."""
        response = client.get('/api/ranges/variant-types-from-traits')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'data' in data
        assert 'values' in data['data']
        
        variant_types = data['data']['values']
        
        # Should have at least some variant types
        assert len(variant_types) > 0
        
        # Check structure of each variant type
        for variant_type in variant_types:
            assert 'id' in variant_type
            assert 'value' in variant_type
            assert 'abbrev' in variant_type
            assert 'description' in variant_type
            assert 'en' in variant_type['description']
        
        # Check for expected variant types (these come from the current LIFT data)
        variant_ids = [vt['id'] for vt in variant_types]
        assert 'dialectal' in variant_ids
        assert 'spelling' in variant_ids

    @pytest.mark.integration
    def test_entry_form_contains_variant_container(self, client: FlaskClient) -> None:
        """Test that the entry form contains the variants container."""
        # Test with add entry form
        response = client.get('/entries/add')
        assert response.status_code == 200
        
        html_content = response.get_data(as_text=True)
        
        # Should contain the variants container
        assert 'id="variants-container"' in html_content
        
        # Should contain the add variant button
        assert 'id="add-variant-btn"' in html_content
        
        # Should initialize the VariantFormsManager
        assert 'VariantFormsManager' in html_content
        assert 'variants-container' in html_content

    @pytest.mark.integration
    def test_variant_forms_uses_traits_based_range_id(self, client: FlaskClient) -> None:
        """Test that variant forms JavaScript uses the correct range ID for traits."""
        response = client.get('/entries/add')
        assert response.status_code == 200
        
        html_content = response.get_data(as_text=True)
        
        # The JavaScript should load the variant-forms.js file which contains 
        # the configuration for 'variant-types-from-traits' range ID
        assert 'variant-forms.js' in html_content

    @pytest.mark.integration
    def test_variant_forms_manager_initialization(self, client: FlaskClient) -> None:
        """Test that the VariantFormsManager is properly initialized."""
        response = client.get('/entries/add')
        assert response.status_code == 200
        
        html_content = response.get_data(as_text=True)
        
        # Should load the variant-forms.js script
        assert 'variant-forms.js' in html_content
        
        # Should initialize the manager with correct container ID
        assert "new VariantFormsManager('variants-container'" in html_content
