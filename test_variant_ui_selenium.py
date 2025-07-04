#!/usr/bin/env python3
"""
Robust UI testing harness using Selenium WebDriver
Tests actual rendered content including JavaScript-generated elements
"""

from __future__ import annotations
import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import quote

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UITestHarness:
    """
    Comprehensive UI testing harness using Selenium WebDriver
    Tests actual rendered content including JavaScript execution
    """
    
    def __init__(self, base_url: str = "http://localhost:5000", headless: bool = True):
        self.base_url = base_url
        self.driver: Optional[webdriver.Chrome] = None
        self.headless = headless
        
    def setup_driver(self) -> None:
        """Initialize Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)  # 10 second implicit wait
            logger.info("✅ Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize WebDriver: {e}")
            raise
            
    def teardown_driver(self) -> None:
        """Clean up WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("✅ WebDriver cleaned up")
            
    def wait_for_element(self, by: By, value: str, timeout: int = 10) -> Any:
        """Wait for element to be present and return it"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"❌ Element not found: {by}={value} within {timeout}s")
            return None
            
    def check_for_error_messages(self) -> List[str]:
        """Check for any error messages on the page"""
        error_messages = []
        
        # Specific error message selectors (avoid false positives from required field markers)
        error_selectors = [
            ".alert-danger:not([style*='display: none'])",
            ".alert-error:not([style*='display: none'])",
            ".error-message",
            ".flash-messages .error",
            ".validation-error"
        ]
        
        for selector in error_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.text.strip():
                        # Skip if it's just a required field marker (*)
                        text = element.text.strip()
                        if text == "*" or text == "":
                            continue
                        error_messages.append(f"Error ({selector}): {text}")
            except:
                continue
                
        # Check for serious application errors in page text
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            serious_errors = [
                "internal server error",
                "500 error",
                "404 not found", 
                "application error",
                "traceback",
                "exception occurred"
            ]
            
            for error_pattern in serious_errors:
                if error_pattern in body_text:
                    error_messages.append(f"Serious error found: {error_pattern}")
        except:
            pass
            
        return error_messages
        
    def test_variant_ui_for_entry(self, entry_id: str, expected_variants: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Test variant UI for a specific entry
        
        Args:
            entry_id: Entry ID to test
            expected_variants: List of expected variants with 'type' and 'target' keys
            
        Returns:
            Test results dictionary
        """
        if not self.driver:
            self.setup_driver()
            
        results = {
            "entry_id": entry_id,
            "success": False,
            "errors": [],
            "found_variants": [],
            "missing_variants": [],
            "unexpected_content": []
        }
        
        try:
            # Navigate to entry edit page
            encoded_id = quote(entry_id)
            url = f"{self.base_url}/entries/{encoded_id}/edit"
            logger.info(f"Testing entry: {entry_id}")
            logger.info(f"URL: {url}")
            
            self.driver.get(url)
            
            # Wait for page to load
            time.sleep(2)
            
            # Check for any error messages first
            error_messages = self.check_for_error_messages()
            if error_messages:
                results["errors"].extend(error_messages)
                logger.error(f"❌ Found error messages: {error_messages}")
                return results
                
            # Wait for variants container
            variants_container = self.wait_for_element(By.ID, "variants-container")
            if not variants_container:
                results["errors"].append("Variants container not found")
                return results
                
            # Wait a bit more for JavaScript to execute
            time.sleep(1)
            
            # Check for variant items
            variant_items = self.driver.find_elements(By.CLASS_NAME, "variant-item")
            
            if not expected_variants:
                # Should show empty state, not variant items
                if variant_items:
                    results["errors"].append(f"Expected no variants but found {len(variant_items)} variant items")
                else:
                    results["success"] = True
                    logger.info("✅ Correctly shows no variants")
            else:
                # Should show variant items
                if not variant_items:
                    results["errors"].append("Expected variants but none found")
                    logger.error("❌ Expected variants but none found")
                    return results
                    
                # Validate each expected variant
                for expected in expected_variants:
                    found = False
                    for item in variant_items:
                        try:
                            # Check variant type in header
                            header = item.find_element(By.CSS_SELECTOR, ".card-header h6")
                            if expected["type"] in header.text:
                                # Check target reference in input field
                                ref_input = item.find_element(By.CSS_SELECTOR, "input[name*='[ref]']")
                                if expected["target"] in ref_input.get_attribute("value"):
                                    found = True
                                    results["found_variants"].append({
                                        "type": expected["type"],
                                        "target": ref_input.get_attribute("value"),
                                        "header_text": header.text
                                    })
                                    logger.info(f"✅ Found expected variant: {expected['type']}")
                                    break
                        except NoSuchElementException:
                            continue
                            
                    if not found:
                        results["missing_variants"].append(expected)
                        logger.error(f"❌ Missing expected variant: {expected}")
                        
                # Check if we found all expected variants
                if len(results["found_variants"]) == len(expected_variants) and not results["missing_variants"]:
                    results["success"] = True
                    logger.info(f"✅ All {len(expected_variants)} expected variants found correctly")
                    
        except Exception as e:
            results["errors"].append(f"Exception during testing: {str(e)}")
            logger.error(f"❌ Exception during testing: {e}")
            
        return results
        
    def run_comprehensive_variant_tests(self) -> Dict[str, Any]:
        """Run comprehensive tests for variant UI functionality"""
        
        test_cases = [
            {
                "entry_id": "Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf",
                "description": "Entry that IS a variant (should show target)",
                "expected_variants": [
                    {
                        "type": "Unspecified Variant",
                        "target": "Protestant ethic_64c53110-099c-446b-8e7f-e06517d47c92"
                    }
                ]
            },
            {
                "entry_id": "Protestant ethic_64c53110-099c-446b-8e7f-e06517d47c92", 
                "description": "Entry that HAS variants (should show variants pointing to it)",
                "expected_variants": [
                    {
                        "type": "Unspecified Variant",
                        "target": "Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf"
                    }
                ]
            },
            {
                "entry_id": "protestor_5b2d8179-ccc6-4aac-a21e-ef2a28bafb89",
                "description": "Entry that IS a spelling variant",
                "expected_variants": [
                    {
                        "type": "Spelling Variant", 
                        "target": "protester_9aae374e-bfc1-4729-908e-4f2ed423cc75"
                    }
                ]
            },
            {
                "entry_id": "protester_9aae374e-bfc1-4729-908e-4f2ed423cc75",
                "description": "Entry that HAS spelling variants",
                "expected_variants": [
                    {
                        "type": "Spelling Variant",
                        "target": "protestor_5b2d8179-ccc6-4aac-a21e-ef2a28bafb89"
                    }
                ]
            }
        ]
        
        overall_results = {
            "total_tests": len(test_cases),
            "passed": 0,
            "failed": 0,
            "test_results": [],
            "summary": ""
        }
        
        try:
            self.setup_driver()
            
            for test_case in test_cases:
                logger.info(f"\n--- Testing: {test_case['description']} ---")
                
                result = self.test_variant_ui_for_entry(
                    test_case["entry_id"],
                    test_case["expected_variants"]
                )
                
                result["description"] = test_case["description"]
                overall_results["test_results"].append(result)
                
                if result["success"]:
                    overall_results["passed"] += 1
                    logger.info(f"✅ PASSED: {test_case['description']}")
                else:
                    overall_results["failed"] += 1
                    logger.error(f"❌ FAILED: {test_case['description']}")
                    for error in result["errors"]:
                        logger.error(f"   Error: {error}")
                        
        finally:
            self.teardown_driver()
            
        # Generate summary
        if overall_results["failed"] == 0:
            overall_results["summary"] = f"🎉 ALL {overall_results['total_tests']} TESTS PASSED!"
        else:
            overall_results["summary"] = f"❌ {overall_results['failed']}/{overall_results['total_tests']} TESTS FAILED"
            
        return overall_results


def main():
    """Run the comprehensive variant UI tests"""
    print("=== COMPREHENSIVE VARIANT UI TESTING WITH SELENIUM ===")
    
    harness = UITestHarness()
    results = harness.run_comprehensive_variant_tests()
    
    print(f"\n{results['summary']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    
    if results['failed'] > 0:
        print("\n=== FAILED TESTS DETAILS ===")
        for result in results['test_results']:
            if not result['success']:
                print(f"\n❌ FAILED: {result['description']}")
                print(f"   Entry: {result['entry_id']}")
                for error in result['errors']:
                    print(f"   Error: {error}")
                if result['missing_variants']:
                    print(f"   Missing variants: {result['missing_variants']}")
    
    return results['failed'] == 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
