#!/usr/bin/env python3

"""
Debug corpus stats endpoint
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app

def test_corpus_endpoint():
    """Test corpus endpoint directly."""
    app = create_app('testing')
    
    print("Available corpus routes:")
    for rule in app.url_map.iter_rules():
        if 'corpus' in rule.rule:
            print(f"  {rule.rule} -> {rule.endpoint} [{','.join(rule.methods or [])}]")
    
    # Test the endpoint
    with app.test_client() as client:
        print("\nTesting /api/corpus/stats endpoint:")
        response = client.get('/api/corpus/stats')
        print(f"Status Code: {response.status_code}")
        if response.status_code != 404:
            print(f"Response: {response.get_json()}")
        else:
            print("Endpoint not found!")

if __name__ == '__main__':
    test_corpus_endpoint()
