#!/usr/bin/env python3
"""Check the rendered HTML for range attributes."""

from app import create_app

def main():
    app = create_app()
    with app.test_client() as client:
        response = client.get('/entries/add')
        html = response.get_data(as_text=True)
        
        print("Looking for data-range-id attributes:")
        lines = html.split('\n')
        for i, line in enumerate(lines):
            if 'data-range-id' in line:
                print(f'Line {i+1}: {line.strip()}')
        
        print("\nLooking for dynamic-lift-range classes:")
        for i, line in enumerate(lines):
            if 'dynamic-lift-range' in line:
                print(f'Line {i+1}: {line.strip()}')
        
        print("\nLooking for dynamic-grammatical-info classes:")
        for i, line in enumerate(lines):
            if 'dynamic-grammatical-info' in line:
                print(f'Line {i+1}: {line.strip()}')

if __name__ == "__main__":
    main()
