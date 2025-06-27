#!/usr/bin/env python3
"""Debug script to test API routes directly."""

import sys
import os

sys.path.insert(0, os.path.abspath("."))

from app import create_app


def test_routes():
    """Test API routes to debug the 308 redirect issue."""
    app = create_app("testing")

    with app.test_client() as client:
        print("Testing routes:")

        # Test basic route
        response = client.get("/")
        print(f"GET /: {response.status_code}")

        # Test health check
        response = client.get("/health")
        print(f"GET /health: {response.status_code}")

        # Test API entries without trailing slash
        response = client.get("/api/entries")
        print(f"GET /api/entries: {response.status_code}")
        if response.status_code == 308:
            print(f"  Redirect location: {response.headers.get('Location', 'None')}")

        # Test API entries with trailing slash
        response = client.get("/api/entries/")
        print(f"GET /api/entries/: {response.status_code}")
        if response.data:
            print(f"  Response: {response.get_data(as_text=True)[:200]}")

    # Print all registered routes
    print("\nRegistered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint} ({', '.join(rule.methods or [])})")


if __name__ == "__main__":
    test_routes()
