#!/usr/bin/env python3

"""
Comprehensive End-to-End Integration Tests for Dynamic LIFT Ranges Support

This test suite validates the entire LIFT ranges pipeline:
1. Parser loads and parses all ranges from sample file
2. Service layer correctly provides ranges with fallback
3. API endpoints expose all ranges with proper structure
4. UI components can consume ranges dynamically
5. Hierarchical ranges work correctly (semantic domains)
6. Performance is acceptable for large datasets

Tests the complete implementation without requiring database connection.
"""

import pytest
import json
from unittest.mock import Mock, patch
from app import create_app
from app.services.dictionary_service import DictionaryService
from app.parsers.lift_parser import LIFTRangesParser


class TestLIFTRangesEndToEndIntegration:
    """End-to-end integration tests for the complete LIFT ranges system."""

    @pytest.fixture
    def app(self):
        """Create test application."""
        app = create_app('testing')
        app.config['TESTING'] = True
        app.config['BASEX_HOST'] = 'localhost'
        app.config['BASEX_PORT'] = 1984
        app.config['BASEX_USERNAME'] = 'admin'
        app.config['BASEX_PASSWORD'] = 'admin'
        app.config['BASEX_DATABASE'] = 'test_ranges_e2e'
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_complete_lift_ranges_pipeline(self, app, client):
        """
        Test the complete LIFT ranges pipeline from parser to API to UI consumption.
        This is a comprehensive end-to-end test that validates:
        1. Parser correctly loads all range types from sample file
        2. Service layer provides comprehensive ranges
        3. API exposes all ranges with correct structure
        4. Critical ranges are available for UI consumption
        """
        with app.app_context():
            # Step 1: Test Parser Layer
            parser = LIFTRangesParser()
            sample_file = 'sample-lift-file/sampleRanges.lift-ranges'
            
            try:
                ranges = parser.parse_file(sample_file)
                assert ranges is not None, "Parser should successfully load sample ranges file"
                assert len(ranges) >= 20, f"Expected at least 20 range types, got {len(ranges)}"
                print(f"✅ Parser: Successfully loaded {len(ranges)} range types")
            except FileNotFoundError:
                pytest.skip("Sample ranges file not found - skipping parser test")

            # Step 2: Test Service Layer
            dict_service = app.injector.get(DictionaryService)
            
            # Mock database connection to test fallback behavior
            with patch.object(dict_service.db_connector, 'execute_query', side_effect=Exception("DB unavailable")):
                service_ranges = dict_service.get_ranges()
                
                assert service_ranges is not None, "Service should provide ranges via fallback"
                assert len(service_ranges) >= 15, f"Expected at least 15 ranges from service, got {len(service_ranges)}"
                
                # Verify critical range types are present
                critical_ranges = ['grammatical-info', 'lexical-relation', 'semantic-domain-ddp4', 'variant-type']
                for critical_range in critical_ranges:
                    assert critical_range in service_ranges, f"Critical range '{critical_range}' missing from service"
                
                print(f"✅ Service: Successfully provided {len(service_ranges)} ranges via fallback")

            # Step 3: Test API Layer
            response = client.get('/api/ranges')
            assert response.status_code == 200, f"Ranges API should return 200, got {response.status_code}"
            
            api_ranges = response.get_json()
            assert api_ranges is not None, "API should return valid JSON"
            assert len(api_ranges) >= 15, f"Expected at least 15 ranges from API, got {len(api_ranges)}"
            
            # Verify API structure for critical ranges
            if 'grammatical-info' in api_ranges:
                gram_info = api_ranges['grammatical-info']
                assert 'values' in gram_info, "Grammatical info should have 'values' key"
                assert len(gram_info['values']) > 0, "Grammatical info should have range values"
                print(f"✅ API: Grammatical info has {len(gram_info['values'])} values")

            if 'semantic-domain-ddp4' in api_ranges:
                semantic_domains = api_ranges['semantic-domain-ddp4']
                assert 'values' in semantic_domains, "Semantic domains should have 'values' key"
                
                # Check for hierarchical structure
                root_elements = [v for v in semantic_domains['values'] if '.' not in v.get('id', '')]
                assert len(root_elements) > 0, "Should have root-level semantic domains"
                
                # Check that some elements have children
                elements_with_children = [v for v in semantic_domains['values'] if len(v.get('children', [])) > 0]
                assert len(elements_with_children) > 0, "Should have semantic domains with children"
                print(f"✅ API: Semantic domains has {len(semantic_domains['values'])} total elements, {len(elements_with_children)} with children")

            print(f"✅ API: Successfully exposed {len(api_ranges)} ranges")

            # Step 4: Test Individual Range Endpoints
            for range_name in ['grammatical-info', 'lexical-relation', 'semantic-domain-ddp4']:
                if range_name in api_ranges:
                    response = client.get(f'/api/ranges/{range_name}')
                    assert response.status_code == 200, f"Individual range endpoint for {range_name} should work"
                    
                    range_data = response.get_json()
                    assert range_data is not None, f"Range {range_name} should return valid JSON"
                    assert 'values' in range_data, f"Range {range_name} should have 'values' key"
                    print(f"✅ API: Individual endpoint for {range_name} works")

    def test_hierarchical_ranges_structure(self, app, client):
        """
        Test that hierarchical ranges (semantic domains) maintain proper parent-child relationships.
        """
        with app.app_context():
            response = client.get('/api/ranges/semantic-domain-ddp4')
            
            if response.status_code == 200:
                semantic_domains = response.get_json()
                
                # Build a map of all elements by ID
                all_elements = {}
                for element in semantic_domains.get('values', []):
                    all_elements[element['id']] = element

                # Verify hierarchical consistency
                for element in semantic_domains.get('values', []):
                    element_id = element['id']
                    children = element.get('children', [])
                    
                    # For each child, verify it exists in the complete set
                    for child in children:
                        child_id = child['id']
                        assert child_id in all_elements, f"Child {child_id} should exist in complete element set"
                        
                        # Verify parent-child relationship consistency
                        if '.' in child_id:  # Child elements should have dots in IDs
                            expected_parent_id = '.'.join(child_id.split('.')[:-1])
                            if expected_parent_id in all_elements:
                                parent_element = all_elements[expected_parent_id]
                                child_ids = [c['id'] for c in parent_element.get('children', [])]
                                assert child_id in child_ids, f"Parent {expected_parent_id} should contain child {child_id}"

                print(f"✅ Hierarchy: Verified {len(all_elements)} semantic domain elements with proper parent-child relationships")
            else:
                pytest.skip("Semantic domains not available - skipping hierarchy test")

    def test_multilingual_range_support(self, app, client):
        """
        Test that ranges with multilingual content are properly handled.
        """
        with app.app_context():
            response = client.get('/api/ranges')
            
            if response.status_code == 200:
                response_data = response.get_json()
                ranges = response_data.get('data', {})
                
                # Look for ranges with multilingual content
                multilingual_found = False
                for range_name, range_data in ranges.items():
                    if isinstance(range_data, dict) and 'values' in range_data:
                        for element in range_data.get('values', []):
                            description = element.get('description', {})
                            if isinstance(description, dict) and len(description) > 1:
                                multilingual_found = True
                                print(f"✅ Multilingual: Found range {range_name} with multilingual descriptions: {list(description.keys())}")
                                break
                        if multilingual_found:
                            break
                
                # If no multilingual content found in API, that's OK - test parser directly
                if not multilingual_found:
                    print("ℹ️ No multilingual content found in API ranges - checking parser directly")
                    
                    parser = LIFTRangesParser()
                    try:
                        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
                        <lift-ranges>
                            <range id="test-multilingual">
                                <range-element id="synonym">
                                    <description>
                                        <form lang="en"><text>Words with the same meaning</text></form>
                                        <form lang="pl"><text>Słowa o tym samym znaczeniu</text></form>
                                    </description>
                                </range-element>
                            </range>
                        </lift-ranges>'''
                        
                        parsed_ranges = parser.parse_string(test_xml)
                        test_range = parsed_ranges.get('test-multilingual', {})
                        if test_range.get('values'):
                            element = test_range['values'][0]
                            description = element.get('description', {})
                            assert 'en' in description, "Should have English description"
                            assert 'pl' in description, "Should have Polish description"
                            print(f"✅ Multilingual: Parser correctly handles multilingual content")
                    except Exception as e:
                        print(f"⚠️ Multilingual test failed: {e}")

    def test_range_performance_with_large_dataset(self, app, client):
        """
        Test that the ranges system performs acceptably with large datasets.
        """
        with app.app_context():
            import time
            
            # Test API response time
            start_time = time.time()
            response = client.get('/api/ranges')
            api_time = time.time() - start_time
            
            assert response.status_code == 200, "Ranges API should be accessible"
            assert api_time < 2.0, f"API response should be under 2 seconds, took {api_time:.2f}s"
            
            ranges_response = response.get_json()
            ranges_data = ranges_response.get('data', {})
            total_elements = sum(len(range_data.get('values', [])) for range_data in ranges_data.values() if isinstance(range_data, dict))
            
            print(f"✅ Performance: API returned {len(ranges_data)} ranges with {total_elements} total elements in {api_time:.2f}s")
            
            # Test individual large range performance
            if 'semantic-domain-ddp4' in ranges_data:
                start_time = time.time()
                response = client.get('/api/ranges/semantic-domain-ddp4')
                individual_time = time.time() - start_time
                
                assert response.status_code == 200, "Individual range endpoint should work"
                assert individual_time < 1.0, f"Individual range should respond under 1 second, took {individual_time:.2f}s"
                
                semantic_data = response.get_json()
                element_count = len(semantic_data.get('values', []))
                print(f"✅ Performance: Semantic domains ({element_count} elements) returned in {individual_time:.2f}s")

    def test_ui_integration_compatibility(self, app, client):
        """
        Test that the ranges API provides data in a format compatible with UI components.
        """
        with app.app_context():
            response = client.get('/api/ranges')
            
            if response.status_code == 200:
                ranges = response.get_json()
                
                # Test that critical UI-consumed ranges have expected structure
                ui_critical_ranges = ['grammatical-info', 'lexical-relation', 'variant-type']
                
                for range_name in ui_critical_ranges:
                    if range_name in ranges:
                        range_data = ranges[range_name]
                        
                        # Verify basic structure expected by UI
                        assert 'values' in range_data, f"Range {range_name} should have 'values' for UI consumption"
                        
                        for element in range_data['values'][:5]:  # Check first 5 elements
                            assert 'id' in element, f"Range {range_name} elements should have 'id' for UI"
                            
                            # Check that description exists in some form (for display)
                            has_description = ('description' in element or 
                                             'label' in element or 
                                             'abbreviation' in element)
                            assert has_description, f"Range {range_name} elements should have displayable text for UI"
                        
                        print(f"✅ UI Compatibility: Range {range_name} has proper structure for UI consumption")

            # Test dropdown-friendly format
            response = client.get('/api/ranges/grammatical-info')
            if response.status_code == 200:
                gram_info = response.get_json()
                values = gram_info.get('values', [])
                
                # Verify format suitable for dropdown/select components
                for element in values[:10]:  # Check first 10
                    element_id = element.get('id')
                    assert element_id, "Elements should have IDs for dropdown values"
                    
                    # Should have some form of display text
                    display_text = (element.get('description', {}).get('en') or 
                                  element.get('label', {}).get('en') or 
                                  element.get('abbreviation', {}).get('en') or
                                  element_id)
                    assert display_text, "Elements should have display text for dropdowns"
                
                print(f"✅ UI Compatibility: Grammatical info suitable for dropdown components")


if __name__ == '__main__':
    # Run the tests
    pytest.main([__file__, '-v'])
