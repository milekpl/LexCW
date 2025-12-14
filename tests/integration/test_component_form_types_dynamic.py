"""
Integration test to ensure component form types are loaded from LIFT ranges, not hardcoded.

This test prevents the inadmissible situation where component.complex_form_type
is preset to a hardcoded list instead of being loaded dynamically from LIFT ranges,
just like relation types are.
"""

import pytest


class TestComponentFormTypesDynamicLoading:
    """Test that component form types are loaded dynamically from LIFT ranges."""

    def test_no_hardcoded_component_types_when_ranges_empty(self, client, app):
        """Test that no hardcoded component type options exist when LIFT ranges are empty."""
        
        with app.test_request_context():
            # Make request to add entry page (no existing entry needed)
            response = client.get("/entries/add")
            
            # Verify response is successful
            assert response.status_code == 200
            
            # Get rendered HTML content
            html_content = response.get_data(as_text=True)
            
            # CRITICAL TEST: Verify component type dropdown exists
            assert 'id="new-component-type"' in html_content, \
                "Component type dropdown should exist"
            
            # With no ranges configured, there should be NO hardcoded options
            # If hardcoded options existed, they would appear even with empty ranges
            assert '<option value="compound">' not in html_content, \
                "Hardcoded 'compound' option found when ranges are empty - INADMISSIBLE!"
            assert '<option value="phrase">' not in html_content, \
                "Hardcoded 'phrase' option found when ranges are empty - INADMISSIBLE!"
            assert '<option value="idiom">' not in html_content, \
                "Hardcoded 'idiom' option found when ranges are empty - INADMISSIBLE!"
            
            # The select should be properly marked for dynamic loading
            assert 'data-range-id="complex-form-type"' in html_content or \
                   'class="dynamic-lift-range"' in html_content, \
                   "Component type select should be marked for dynamic LIFT range loading!"

    def test_inadmissible_hardcoded_component_types_detection(self, client, app):
        """Test specifically designed to catch the inadmissible hardcoded component types issue."""
        
        with app.test_request_context():
            response = client.get("/entries/add")
            html_content = response.get_data(as_text=True)
            
            # This test specifically checks for the inadmissible pattern identified
            # where component.complex_form_type is hardcoded instead of dynamic
            
            component_select_exists = 'id="new-component-type"' in html_content
            assert component_select_exists, "Component type dropdown should exist"
            
            # Check for tell-tale signs of hardcoding
            hardcoded_indicators = [
                '<option value="compound">',
                '<option value="phrase">', 
                '<option value="idiom">'
            ]
            
            found_hardcoded = []
            for indicator in hardcoded_indicators:
                if indicator in html_content:
                    found_hardcoded.append(indicator)
            
            # If we found hardcoded options, this is the inadmissible situation
            if found_hardcoded:
                pytest.fail(
                    f"INADMISSIBLE: Found hardcoded component type options: {found_hardcoded}. "
                    "Component types must be loaded dynamically from LIFT ranges, "
                    "just like relation types and other form fields."
                )
            
            # Verify it's configured for dynamic loading (using complex-form-type range)
            dynamic_indicators = [
                'data-range-id="complex-form-type"',
                'class="dynamic-lift-range"',
                'data-hierarchical="true"'
            ]
            
            found_dynamic = [ind for ind in dynamic_indicators if ind in html_content]
            assert len(found_dynamic) >= 1, \
                f"Component type select configured for dynamic loading. Found: {found_dynamic}"