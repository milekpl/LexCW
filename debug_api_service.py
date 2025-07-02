#!/usr/bin/env python3

"""
Debug script to understand API vs Service difference in ranges.
"""

def debug_api_service_difference():
    """Debug why API returns different data than service."""
    
    try:
        from app import create_app
        from app.services.dictionary_service import DictionaryService
        from app.database.mock_connector import MockDatabaseConnector
        
        # Create test app
        app = create_app('testing')
        
        with app.app_context():
            print("=== DIRECT SERVICE TEST ===")
            mock_connector = MockDatabaseConnector()
            service = DictionaryService(mock_connector)
            service_ranges = service.get_ranges()
            print(f"Direct service ranges: {len(service_ranges)}")
            print(f"Service range keys: {list(service_ranges.keys())}")
            
            print("\n=== API TEST ===")
            with app.test_client() as client:
                response = client.get('/api/ranges')
                print(f"API Status: {response.status_code}")
                
                if response.status_code == 200:
                    api_data = response.get_json()
                    print(f"API Response Keys: {list(api_data.keys())}")
                    
                    if 'data' in api_data:
                        api_ranges = api_data['data']
                        print(f"API ranges count: {len(api_ranges)}")
                        print(f"API range keys: {list(api_ranges.keys())}")
                    else:
                        print("No 'data' key in API response")
                        print(f"Full API response: {api_data}")
                else:
                    print(f"API Error: {response.get_data(as_text=True)}")
            
            print("\n=== DEPENDENCY INJECTION TEST ===")
            try:
                from app import injector
                di_service = injector.get(DictionaryService)
                di_ranges = di_service.get_ranges()
                print(f"DI service ranges: {len(di_ranges)}")
                print(f"DI range keys: {list(di_ranges.keys())}")
            except Exception as e:
                print(f"DI Error: {e}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    debug_api_service_difference()
