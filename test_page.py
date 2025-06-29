#!/usr/bin/env python3
"""
Test the corpus management page by making a direct HTTP request.
"""
import requests
import sys

def test_corpus_management_page():
    """Test the corpus management page directly."""
    try:
        response = requests.get('http://localhost:5000/corpus-management', timeout=10)
        
        print(f'Status Code: {response.status_code}')
        print(f'Content-Type: {response.headers.get("Content-Type", "N/A")}')
        
        if response.status_code == 200:
            content = response.text
            
            # Check if the page contains the expected corpus stats
            if '74,723,856' in content or '74723856' in content:
                print('✓ SUCCESS: Page contains the corpus record count!')
                
            if 'Connected' in content and 'PostgreSQL Status' in content:
                print('✓ SUCCESS: Page shows PostgreSQL as connected!')
                
            if 'Could not fetch stats' in content or 'nie istnieje' in content:
                print('✗ FAILURE: Page still shows the error message!')
                return False
            else:
                print('✓ SUCCESS: No error messages found!')
                
            # Print a sample of the content to verify
            print('\nPage content sample:')
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'PostgreSQL Status' in line or 'total_records' in line.lower() or 'records' in line.lower():
                    start = max(0, i-2)
                    end = min(len(lines), i+3)
                    for j in range(start, end):
                        prefix = '>>> ' if j == i else '    '
                        print(f'{prefix}{lines[j].strip()}')
                    print()
                    
            return True
        else:
            print(f'✗ FAILURE: HTTP {response.status_code}')
            print(response.text[:500])
            return False
            
    except requests.exceptions.RequestException as e:
        print(f'✗ FAILURE: Request failed: {e}')
        return False

if __name__ == '__main__':
    success = test_corpus_management_page()
    sys.exit(0 if success else 1)
