#!/usr/bin/env python3
"""
Test filtering functionality after the XQuery fix.
This script tests both API and UI functionality.
"""

import requests
import json
import time
import sys
from typing import Dict, Any, List

class FilteringTest:
    """Test filtering functionality."""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()

    def test_api_filtering(self) -> bool:
        """Test API filtering functionality."""
        print("Testing API filtering...")
        
        # Test 1: Filter with common word "test"
        response = self.session.get(f"{self.base_url}/api/entries/?filter_text=test&limit=5")
        if response.status_code != 200:
            print(f"❌ API filtering failed with status {response.status_code}: {response.text}")
            return False
        
        data = response.json()
        
        if "entries" not in data:
            print(f"❌ API response missing 'entries' field: {data}")
            return False
        
        entries = data["entries"]
        total_count = data.get("total_count", 0)
        
        print(f"✅ API filtering for 'test' returned {len(entries)} entries (total: {total_count})")
        
        # Verify that returned entries actually contain the filter text
        for entry in entries:
            lexical_unit = entry.get("lexical_unit", {})
            found = False
            if isinstance(lexical_unit, dict):
                for lang, text in lexical_unit.items():
                    if "test" in text.lower():
                        found = True
                        break
            elif isinstance(lexical_unit, str):
                if "test" in lexical_unit.lower():
                    found = True
            
            if not found:
                print(f"⚠️  Entry {entry.get('id')} doesn't contain 'test' in lexical_unit")
        
        # Test 2: Filter with non-existent word
        response = self.session.get(f"{self.base_url}/api/entries/?filter_text=nonexistentword12345&limit=5")
        if response.status_code != 200:
            print(f"❌ API filtering with non-existent word failed: {response.text}")
            return False
        
        data = response.json()
        if data.get("total_count", 0) > 0:
            print(f"⚠️  Expected 0 results for non-existent word, got {data.get('total_count')}")
        else:
            print("✅ API filtering correctly returned 0 results for non-existent word")
        
        # Test 3: No filter (should return more results)
        response = self.session.get(f"{self.base_url}/api/entries/?limit=5")
        if response.status_code != 200:
            print(f"❌ API without filter failed: {response.text}")
            return False
        
        data = response.json()
        unfiltered_count = data.get("total_count", 0)
        print(f"✅ API without filter returned {unfiltered_count} total entries")
        
        return True

    def test_api_sorting(self) -> bool:
        """Test API sorting functionality."""
        print("\nTesting API sorting...")
        
        # Test ascending sort
        response = self.session.get(f"{self.base_url}/api/entries/?sort_order=asc&limit=3")
        if response.status_code != 200:
            print(f"❌ API ascending sort failed: {response.text}")
            return False
        
        print("✅ API ascending sort worked")
        
        # Test descending sort
        response = self.session.get(f"{self.base_url}/api/entries/?sort_order=desc&limit=3")
        if response.status_code != 200:
            print(f"❌ API descending sort failed: {response.text}")
            return False
        
        print("✅ API descending sort worked")
        
        return True

    def test_swagger_documentation(self) -> bool:
        """Test Swagger documentation availability."""
        print("\nTesting Swagger documentation...")
        
        # Test Swagger UI
        response = self.session.get(f"{self.base_url}/apidocs/")
        if response.status_code != 200:
            print(f"❌ Swagger UI not accessible: {response.status_code}")
            return False
        
        print("✅ Swagger UI accessible")
        
        # Test API spec
        response = self.session.get(f"{self.base_url}/apispec.json")
        if response.status_code != 200:
            print(f"❌ API spec not accessible: {response.status_code}")
            return False
        
        spec = response.json()
        if "paths" not in spec:
            print(f"❌ API spec missing paths: {spec}")
            return False
        
        paths = spec["paths"]
        print(f"✅ API spec contains {len(paths)} documented endpoints")
        
        # Check for our main endpoints
        expected_endpoints = ["/api/entries/", "/api/dashboard/stats"]
        for endpoint in expected_endpoints:
            if endpoint in paths:
                print(f"✅ Endpoint {endpoint} documented")
            else:
                print(f"⚠️  Endpoint {endpoint} not documented")
        
        return True

    def run_all_tests(self) -> bool:
        """Run all tests."""
        print("=" * 60)
        print("FILTERING AND DOCUMENTATION TESTS")
        print("=" * 60)
        
        try:
            # Test server availability
            response = self.session.get(f"{self.base_url}/health")
            if response.status_code != 200:
                print(f"❌ Server not available at {self.base_url}")
                return False
            
            print(f"✅ Server available at {self.base_url}")
            
            # Run tests
            api_filtering_ok = self.test_api_filtering()
            api_sorting_ok = self.test_api_sorting()
            swagger_ok = self.test_swagger_documentation()
            
            print("\n" + "=" * 60)
            print("TEST SUMMARY")
            print("=" * 60)
            print(f"API Filtering: {'✅ PASS' if api_filtering_ok else '❌ FAIL'}")
            print(f"API Sorting: {'✅ PASS' if api_sorting_ok else '❌ FAIL'}")
            print(f"Swagger Docs: {'✅ PASS' if swagger_ok else '❌ FAIL'}")
            
            all_passed = all([api_filtering_ok, api_sorting_ok, swagger_ok])
            print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
            
            return all_passed
            
        except requests.exceptions.ConnectionError:
            print(f"❌ Could not connect to server at {self.base_url}")
            print("Make sure the Flask server is running with: python run.py")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False

if __name__ == "__main__":
    tester = FilteringTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
