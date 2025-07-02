#!/usr/bin/env python3

"""
Debug script to test API pagination behavior.
"""

import json
import sys
import os

# Add app directory to Python path  
sys.path.insert(0, os.path.abspath('.'))

def test_api_behavior():
    """Test API behavior with invalid parameters."""
    
    print("Testing API behavior with invalid parameters...")
    
    try:
        from tests.conftest import *
        
        # Get app fixture 
        dict_service = None
        for fixture in [dict_service_with_db]:
            try:
                dict_service = fixture()
                break
            except:
                continue
        
        if not dict_service:
            print("Could not get dictionary service, using basic app")
            from app import create_app
            app = create_app('testing')
        else:
            # Use the actual fixture system
            import pytest
            pytest.main(['-v', 'tests/debug_api_behavior.py::test_debug'])
            
    except Exception as e:
        print("Test error:", e)

if __name__ == '__main__':
    test_api_behavior()
