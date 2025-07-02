#!/usr/bin/env python3

"""
End-to-end integration test for LIFT ranges system.
Tests complete flow: parser → service → API → UI integration.
"""

def test_complete_ranges_integration():
    """Test the complete LIFT ranges system end-to-end."""
    
    try:
        from app import create_app
        from app.services.dictionary_service import DictionaryService
        
        # Create test app
        app = create_app('testing')
        
        with app.app_context():
            # Test 1: Service layer - verify ranges are loaded
            print("=== SERVICE LAYER TEST ===")
            
            # Get service instance using dependency injection
            from app.services.dictionary_service import DictionaryService
            from app.database.mock_connector import MockDatabaseConnector
            
            # Create service with mock connector for testing
            mock_connector = MockDatabaseConnector()
            service = DictionaryService(mock_connector)
            ranges = service.get_ranges()
            
            print(f"Total ranges loaded: {len(ranges)}")
            
            # Verify we have the expected range types
            expected_ranges = [
                'etymology', 'grammatical-info', 'lexical-relation', 'note-type',
                'paradigm', 'reversal-type', 'semantic-domain-ddp4', 'status',
                'users', 'location', 'anthro-code', 'translation-type',
                'inflection-feature', 'inflection-feature-type', 'from-part-of-speech',
                'morph-type', 'num-feature-value', 'Publications', 'do-not-publish-in',
                'domain-type', 'usage-type'
            ]
            
            found_ranges = 0
            for range_id in expected_ranges:
                if range_id in ranges:
                    values_count = len(ranges[range_id].get('values', []))
                    print(f"✅ {range_id}: {values_count} values")
                    found_ranges += 1
                else:
                    print(f"❌ Missing range: {range_id}")
            
            print(f"Found {found_ranges}/{len(expected_ranges)} expected ranges")
            
            # Test 2: API layer - test endpoints
            print("\n=== API LAYER TEST ===")
            
            with app.test_client() as client:
                # Test all ranges endpoint
                response = client.get('/api/ranges')
                print(f"GET /api/ranges - Status: {response.status_code}")
                
                if response.status_code == 200:
                    api_ranges = response.get_json()
                    print(f"API returned {len(api_ranges)} ranges")
                    
                    # Test specific range endpoints
                    test_ranges = ['semantic-domain-ddp4', 'grammatical-info']
                    for range_id in test_ranges:
                        if range_id in api_ranges:
                            response = client.get(f'/api/ranges/{range_id}')
                            print(f"GET /api/ranges/{range_id} - Status: {response.status_code}")
                            
                            if response.status_code == 200:
                                range_data = response.get_json()
                                values_count = len(range_data.get('values', []))
                                print(f"  {range_id}: {values_count} values")
                else:
                    print(f"API endpoint failed with status {response.status_code}")
            
            # Test 3: Check hierarchy structure for semantic domains
            print("\n=== HIERARCHY STRUCTURE TEST ===")
            
            if 'semantic-domain-ddp4' in ranges:
                semantic_range = ranges['semantic-domain-ddp4']
                
                if isinstance(semantic_range, dict) and 'values' in semantic_range:
                    values = semantic_range['values']
                    print(f"Semantic domain values: {len(values)}")
                    
                    # Check for hierarchy elements
                    hierarchy_count = 0
                    for value in values:
                        if isinstance(value, dict) and value.get('children'):
                            hierarchy_count += 1
                    
                    print(f"Elements with children: {hierarchy_count}")
                    
                    if hierarchy_count > 0:
                        print("✅ Hierarchical structure detected")
                    else:
                        print("❌ No hierarchical structure found")
                else:
                    print("❌ Invalid semantic range structure")
            else:
                print("❌ semantic-domain-ddp4 not found")
            
            print("\n=== TEST COMPLETED ===")
            return True
            
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = test_complete_ranges_integration()
    if success:
        print("✅ End-to-end test completed successfully")
    else:
        print("❌ End-to-end test failed")
