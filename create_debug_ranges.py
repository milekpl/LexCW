#!/usr/bin/env python3

"""
Create a modified version of ranges-loader.js with debugging to understand what's happening.
"""

def add_debugging_to_ranges_loader():
    """Add console.log statements to ranges-loader.js for debugging."""
    
    # Read the current ranges-loader.js file
    with open('app/static/js/ranges-loader.js', 'r') as f:
        original_content = f.read()
    
    # Add debugging statements
    modified_content = original_content.replace(
        'async loadRange(rangeId) {',
        '''async loadRange(rangeId) {
        console.log('[RANGES DEBUG] Loading range:', rangeId);'''
    ).replace(
        'const response = await fetch(`${this.baseUrl}/${rangeId}`);',
        '''console.log('[RANGES DEBUG] Fetching:', `${this.baseUrl}/${rangeId}`);
        const response = await fetch(`${this.baseUrl}/${rangeId}`);
        console.log('[RANGES DEBUG] Response status:', response.status);'''
    ).replace(
        'async populateSelect(selectElement, rangeId, options = {}) {',
        '''async populateSelect(selectElement, rangeId, options = {}) {
        console.log('[RANGES DEBUG] Populating select for range:', rangeId, 'element:', selectElement);'''
    ).replace(
        'async populateSelectWithFallback(selectElement, rangeId, options = {}) {',
        '''async populateSelectWithFallback(selectElement, rangeId, options = {}) {
        console.log('[RANGES DEBUG] PopulateSelectWithFallback called for:', rangeId);'''
    ).replace(
        'const success = await this.populateSelect(selectElement, rangeId, options);',
        '''const success = await this.populateSelect(selectElement, rangeId, options);
        console.log('[RANGES DEBUG] PopulateSelect result:', success);'''
    ).replace(
        'console.warn(`Using fallback values for range ${rangeId}`);',
        '''console.warn(`[RANGES DEBUG] Using fallback values for range ${rangeId}`);'''
    )
    
    # Write the modified content to a debug version
    with open('app/static/js/ranges-loader-debug.js', 'w') as f:
        f.write(modified_content)
    
    print("✅ Created debug version: app/static/js/ranges-loader-debug.js")
    
    # Also create a minimal test HTML file
    test_html = '''<!DOCTYPE html>
<html>
<head>
    <title>Ranges Loader Test</title>
</head>
<body>
    <h1>Ranges Loader Debug Test</h1>
    <select id="test-select" class="dynamic-grammatical-info" data-range-id="grammatical-info">
        <option value="">Loading...</option>
    </select>
    
    <script>
    console.log('[TEST] Starting ranges loader test');
    </script>
    <script src="/static/js/ranges-loader-debug.js"></script>
    <script>
    document.addEventListener('DOMContentLoaded', async function() {
        console.log('[TEST] DOM loaded, rangesLoader available:', !!window.rangesLoader);
        
        if (window.rangesLoader) {
            const select = document.getElementById('test-select');
            console.log('[TEST] Found select element:', select);
            
            try {
                await window.rangesLoader.populateSelectWithFallback(select, 'grammatical-info', {
                    emptyOption: 'Select part of speech',
                    selectedValue: '',
                    valueField: 'value',
                    labelField: 'value'
                });
                console.log('[TEST] Successfully populated select');
            } catch (error) {
                console.error('[TEST] Error populating select:', error);
            }
        } else {
            console.error('[TEST] rangesLoader not available!');
        }
    });
    </script>
</body>
</html>'''
    
    with open('app/templates/ranges_test.html', 'w') as f:
        f.write(test_html)
    
    print("✅ Created test page: app/templates/ranges_test.html")


if __name__ == '__main__':
    add_debugging_to_ranges_loader()
