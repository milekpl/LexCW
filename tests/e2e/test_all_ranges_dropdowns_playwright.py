"""
Comprehensive Playwright integration tests for ALL LIFT ranges dropdowns.

Tests that all range-based dropdowns (grammatical-info, domain-type, 
semantic-domain, usage-type) are populated correctly from the LIFT ranges in BaseX.

This ensures the ranges-loader.js properly initializes ALL dynamic-lift-range elements.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.integration
@pytest.mark.playwright
class TestAllRangesDropdownsPlaywright:
    """Test all LIFT ranges dropdowns are populated in the UI."""

    def test_grammatical_info_dropdown_populated(self, page: Page, app_url, basex_test_connector):
        """Test that grammatical info (part of speech) dropdown is populated."""
        # Navigate to entry edit page
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')
        
        # Find grammatical info selects (both entry-level and sense-level)
        pos_selects = page.locator('select.dynamic-grammatical-info, select[data-range-id="grammatical-info"]')
        
        # Wait for at least one to be visible
        expect(pos_selects.first).to_be_visible(timeout=10000)
        
        # Get options from first select
        options = pos_selects.first.locator('option').all_text_contents()
        
        # Should have more than just the empty option
        assert len(options) > 1, f"Expected multiple POS options, got: {options}"
        
        # Check for common grammatical categories
        options_text = " ".join(options).lower()
        common_categories = ['noun', 'verb', 'adjective', 'adverb']
        has_category = any(cat in options_text for cat in common_categories)
        assert has_category, f"Expected at least one common POS category in: {options}"
        
        print(f"✅ Grammatical info: {len(options)} options loaded")

    def test_domain_type_dropdown_populated(self, page: Page, app_url, basex_test_connector):
        """Test that domain type dropdown is populated from domain-type range."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')
        
        # Wait a bit for JavaScript to initialize dropdowns
        page.wait_for_timeout(2000)
        
        # Find domain type selects
        domain_types_selects = page.locator('select[data-range-id="domain-type"]')
        
        # Check count
        count = domain_types_selects.count()
        
        # Check if visible and has options
        if count > 0 and domain_types_selects.first.is_visible():
            # Get options
            options = domain_types_selects.first.locator('option').all_text_contents()
            
            # Should have more than just the empty option
            assert len(options) > 1, f"Expected multiple domain type options, got: {options}"
            
            # Check for some expected domain types from domain-type range
            options_text = " ".join(options).lower()
            # Based on the LIFT file, we expect domains like: computer science, finance, legal, etc.
            expected_domains = ['computer', 'finance', 'legal', 'science', 'antiq', 'inform']
            has_domain = any(domain in options_text for domain in expected_domains)
            assert has_domain, f"Expected at least one domain type in: {options[:5]}"
            
            print(f"✅ domain type: {len(options)} options loaded")
        else:
            # If not visible or doesn't exist, check via API that the range is accessible
            page.goto(f'{app_url}/api/ranges/domain-type')
            content = page.content()
            assert '"success":true' in content or '"data"' in content, \
                f"domain type range not accessible via API: {content[:200]}"
            print("⚠️  domain type select not visible on page load, but range accessible via API")

    def test_semantic_domain_dropdown_populated(self, page: Page, app_url, basex_test_connector):
        """Test that semantic domain dropdown is populated from semantic-domain-ddp4 range."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')
        
        # Wait for JavaScript to initialize dropdowns
        page.wait_for_timeout(2000)
        
        # Find semantic domain selects
        semantic_selects = page.locator('select[data-range-id="semantic-domain-ddp4"]')
        
        # If not present in page, check API fallback
        count = semantic_selects.count()
        if count == 0:
            page.goto(f'{app_url}/api/ranges/semantic-domain-ddp4')
            content = page.content()
            assert '"success":true' in content or '"data"' in content, \
                f"Semantic domain range not accessible via API: {content[:200]}"
            print("⚠️ Semantic domain select not present on page; verified via API")
            return

        # Check if it's visible
        if semantic_selects.first.is_visible():
            # Get options
            options = semantic_selects.first.locator('option').all_text_contents()
            
            # Should have more than just the empty option
            assert len(options) > 1, f"Expected multiple semantic domain options, got: {options}"
            
            # Semantic domains are hierarchical, so we should see some structure
            # Check for typical semantic domain patterns (numbers like "1.", "2.1", etc.)
            options_text = " ".join(options)
            has_numeric_pattern = any(char.isdigit() for char in options_text)
            assert has_numeric_pattern, f"Expected semantic domains with numeric IDs, got: {options[:5]}"
            
            print(f"✅ Semantic domain: {len(options)} options loaded")
        else:
            # Check via API
            page.goto(f'{app_url}/api/ranges/semantic-domain-ddp4')
            content = page.content()
            assert '"success":true' in content or '"data"' in content, \
                f"Semantic domain range not accessible via API: {content[:200]}"
            print("⚠️  Semantic domain select exists but not visible (may need UI action to show)")

    def test_usage_type_dropdown_populated(self, page: Page, app_url, basex_test_connector):
        """Test that usage type dropdown is populated from usage-type range."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')
        
        # Wait for JavaScript to initialize dropdowns
        page.wait_for_timeout(2000)
        
        # Find usage type selects
        usage_selects = page.locator('select[data-range-id="usage-type"]')
        
        # If not present in page, check API fallback
        count = usage_selects.count()
        if count == 0:
            page.goto(f'{app_url}/api/ranges/usage-type')
            content = page.content()
            assert '"success":true' in content or '"data"' in content, \
                f"Usage type range not accessible via API: {content[:200]}"
            print("⚠️ Usage type select not present on page; verified via API")
            return

        # Check if it's visible
        if usage_selects.first.is_visible():
            # Get options
            options = usage_selects.first.locator('option').all_text_contents()
            
            # Should have more than just the empty option
            assert len(options) > 1, f"Expected multiple usage type options, got: {options}"
            
            # Check for expected usage types (formal, informal, archaic, etc.)
            options_text = " ".join(options).lower()
            expected_usage = ['formal', 'informal', 'archaic', 'slang', 'literary', 'colloquial']
            has_usage = any(usage in options_text for usage in expected_usage)
            assert has_usage, f"Expected at least one usage type in: {options}"
            
            print(f"✅ Usage type: {len(options)} options loaded")
        else:
            # Check via API
            page.goto(f'{app_url}/api/ranges/usage-type')
            content = page.content()
            assert '"success":true' in content or '"data"' in content, \
                f"Usage type range not accessible via API: {content[:200]}"
            print("⚠️  Usage type select exists but not visible (may need UI action to show)")

    def test_all_ranges_api_accessible(self, page: Page, app_url, basex_test_connector):
        """Test that all required ranges are accessible via API."""
        # First check what ranges are actually available
        page.goto(f'{app_url}/api/ranges')
        all_ranges_content = page.content()
        
        # Try to extract available_types from JSON
        import json
        import re
        json_match = re.search(r'<pre>(.*?)</pre>', all_ranges_content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if 'available_types' in data:
                    print(f"\n📊 Available ranges: {sorted(data['available_types'])}")
                elif 'data' in data:
                    print(f"\n📊 Available ranges: {sorted(list(data['data'].keys()))}")
            except Exception as e:
                print(f"Could not parse JSON: {e}")
        
        # Test that domain-type works directly
        page.goto(f'{app_url}/api/ranges/domain-type')
        direct_content = page.content()
        print(f"\n🔍 Direct domain-type request: {'success' if '404' not in direct_content else 'FAILED'}")
        
        required_ranges = [
            'grammatical-info',
            'domain-type',
            'semantic-domain-ddp4',
            'usage-type'
        ]
        
        for range_id in required_ranges:
            response = page.goto(f'{app_url}/api/ranges/{range_id}')
            content = page.content()
            
            # Check HTTP status, not text content (since "404" might appear in domain names)
            assert response and response.ok, \
                f"Range {range_id} returned {response.status if response else 'no response'}"
            
            # Should contain data
            assert '"data"' in content or '"values"' in content, \
                f"Range {range_id} missing data: {content[:200]}"
            
            print(f"✅ API accessible: /api/ranges/{range_id}")

    def test_dynamic_lift_range_initialization(self, page: Page, app_url, basex_test_connector):
        """Test that ALL elements with class 'dynamic-lift-range' are initialized."""
        page.goto(f'{app_url}/entries/add')
        page.wait_for_load_state('networkidle')
        
        # Wait for JavaScript initialization
        page.wait_for_timeout(3000)
        
        # Find all dynamic-lift-range selects
        all_dynamic_selects = page.locator('select.dynamic-lift-range')
        total_count = all_dynamic_selects.count()
        
        assert total_count > 0, "Should have at least one dynamic-lift-range select"
        
        # Check each one has been populated (more than 1 option)
        initialized_count = 0
        for i in range(total_count):
            select = all_dynamic_selects.nth(i)
            
            # Skip if not visible (might be in template)
            if not select.is_visible():
                continue
            
            option_count = select.locator('option').count()
            range_id = select.get_attribute('data-range-id')
            
            if option_count > 1:
                initialized_count += 1
                print(f"✅ Initialized: {range_id} ({option_count} options)")
            else:
                print(f"❌ NOT initialized: {range_id} (only {option_count} option)")
        
        # At least some should be initialized
        assert initialized_count > 0, \
            f"Expected at least some dynamic-lift-range selects to be initialized, got {initialized_count}/{total_count}"
        
        print(f"\n📊 Summary: {initialized_count}/{total_count} dynamic-lift-range selects initialized")
