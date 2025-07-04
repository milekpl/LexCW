#!/usr/bin/env python3
"""
Comprehensive UI testing harness using Selenium WebDriver
Tests actual rendered content and provides detailed failure diagnostics
"""

from __future__ import annotations
import time
import logging
import sys
import json
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from urllib.parse import quote

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ComprehensiveUITester:
    """
    Comprehensive UI testing harness that validates actual rendered content
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
            self.driver.implicitly_wait(10)
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
            
    def detect_critical_errors(self) -> List[str]:
        """Detect critical application errors that would prevent normal operation"""
        errors = []
        
        try:
            # Check page title for error indicators
            title = self.driver.title.lower()
            if any(err in title for err in ["error", "500", "404", "exception"]):
                errors.append(f"Error in page title: {self.driver.title}")
                
            # Check for Flask/Python error messages
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            critical_patterns = [
                "Traceback (most recent call last)",
                "Internal Server Error",
                "500 Internal Server Error",
                "TypeError:",
                "AttributeError:",
                "KeyError:",
                "ValueError:",
                "NameError:",
                "The server encountered an internal error"
            ]
            
            for pattern in critical_patterns:
                if pattern in body_text:
                    errors.append(f"Critical error detected: {pattern}")
                    
            # Check for alert messages (Bootstrap alerts)
            alert_selectors = [
                ".alert-danger:not([style*='display: none'])",
                ".alert-error:not([style*='display: none'])"
            ]
            
            for selector in alert_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    if element.is_displayed() and element.text.strip():
                        text = element.text.strip()
                        # Skip trivial markers
                        if text not in ["*", ""]:
                            errors.append(f"Alert error: {text}")
                            
        except Exception as e:
            errors.append(f"Error during error detection: {str(e)}")
            
        return errors
        
    def extract_variant_data_from_page(self) -> Dict[str, Any]:
        """Extract variant-related data from the current page"""
        variant_data = {
            "variant_items": [],
            "javascript_data": None,
            "errors": []
        }
        
        try:
            # Extract JavaScript variant data
            script_elements = self.driver.find_elements(By.TAG_NAME, "script")
            for script in script_elements:
                script_content = script.get_attribute("innerHTML")
                if script_content and "variantRelations" in script_content:
                    # Extract the JSON data
                    import re
                    match = re.search(r'window\.variantRelations\s*=\s*(\[.*?\]);', script_content, re.DOTALL)
                    if match:
                        try:
                            variant_data["javascript_data"] = json.loads(match.group(1))
                        except json.JSONDecodeError as e:
                            variant_data["errors"].append(f"Failed to parse variant JSON: {e}")
                            
            # Extract rendered variant items
            variant_items = self.driver.find_elements(By.CLASS_NAME, "variant-item")
            for item in variant_items:
                try:
                    item_data = {}
                    
                    # Get direction
                    direction = item.get_attribute("data-direction") or "unknown"
                    item_data["direction"] = direction
                    
                    # Get header text (variant type and direction info)
                    header = item.find_element(By.CSS_SELECTOR, ".card-header h6")
                    item_data["header_text"] = header.text.strip()
                    
                    # Get reference field - check for both input and clickable links
                    try:
                        ref_input = item.find_element(By.CSS_SELECTOR, "input[name*='[ref]']")
                        item_data["ref_value"] = ref_input.get_attribute("value")
                    except NoSuchElementException:
                        item_data["ref_value"] = "NO_INPUT_FIELD"
                    
                    # Check for clickable headword link (can be in different locations)
                    try:
                        # Try incoming variant format first (.alert-light a)
                        ref_link = item.find_element(By.CSS_SELECTOR, ".alert-light a")
                        item_data["ref_display"] = ref_link.text.strip()
                        item_data["ref_link_href"] = ref_link.get_attribute("href")
                        
                        # Extract entry ID from the href
                        href = ref_link.get_attribute("href")
                        if href and "/entries/" in href and "/edit" in href:
                            entry_id = href.split("/entries/")[1].split("/edit")[0]
                            from urllib.parse import unquote
                            item_data["ref_id"] = unquote(entry_id)
                        else:
                            item_data["ref_id"] = "UNKNOWN"
                            
                    except NoSuchElementException:
                        # Try outgoing variant format (different selector structure)
                        try:
                            # Look for any link within the variant item
                            ref_links = item.find_elements(By.TAG_NAME, "a")
                            for link in ref_links:
                                href = link.get_attribute("href")
                                if href and "/entries/" in href and "/edit" in href:
                                    item_data["ref_display"] = link.text.strip()
                                    item_data["ref_link_href"] = href
                                    
                                    entry_id = href.split("/entries/")[1].split("/edit")[0]
                                    from urllib.parse import unquote
                                    item_data["ref_id"] = unquote(entry_id)
                                    break
                            else:
                                item_data["ref_display"] = "NO_LINK_FOUND"
                        except Exception:
                            item_data["ref_display"] = "NO_LINK_FOUND"
                            
                    variant_data["variant_items"].append(item_data)
                    
                except Exception as e:
                    variant_data["errors"].append(f"Error extracting variant item: {e}")
                    
        except Exception as e:
            variant_data["errors"].append(f"Error extracting variant data: {e}")
            
        return variant_data
        
    def test_entry_variant_ui(self, entry_id: str, expected_behavior: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive test for variant UI on a specific entry
        
        Args:
            entry_id: The entry to test
            expected_behavior: Expected behavior with keys:
                - should_have_variants: bool
                - expected_variant_count: int
                - expected_directions: List[str] (incoming/outgoing)
                - expected_refs: List[str] (entry IDs that should be referenced)
        """
        if not self.driver:
            self.setup_driver()
            
        test_result = {
            "entry_id": entry_id,
            "url": "",
            "success": False,
            "critical_errors": [],
            "variant_data": {},
            "validation_results": {},
            "raw_page_info": {}
        }
        
        try:
            # Navigate to entry edit page
            encoded_id = quote(entry_id)
            url = f"{self.base_url}/entries/{encoded_id}/edit"
            test_result["url"] = url
            
            logger.info(f"🧪 Testing entry: {entry_id}")
            logger.info(f"📍 URL: {url}")
            
            self.driver.get(url)
            time.sleep(3)  # Allow time for JavaScript execution
            
            # Detect critical errors first
            critical_errors = self.detect_critical_errors()
            test_result["critical_errors"] = critical_errors
            
            if critical_errors:
                logger.error(f"❌ Critical errors detected: {critical_errors}")
                return test_result
                
            # Extract variant data
            variant_data = self.extract_variant_data_from_page()
            test_result["variant_data"] = variant_data
            
            # Store raw page information for debugging
            test_result["raw_page_info"] = {
                "title": self.driver.title,
                "url": self.driver.current_url,
                "has_variants_container": bool(self.driver.find_elements(By.ID, "variants-container"))
            }
            
            # Validate against expected behavior
            validation = self.validate_variant_behavior(variant_data, expected_behavior)
            test_result["validation_results"] = validation
            test_result["success"] = validation["overall_success"]
            
            if test_result["success"]:
                logger.info(f"✅ Entry {entry_id} passed all variant UI tests")
            else:
                logger.error(f"❌ Entry {entry_id} failed variant UI tests")
                for error in validation["failures"]:
                    logger.error(f"   • {error}")
                    
        except Exception as e:
            test_result["critical_errors"].append(f"Exception during testing: {str(e)}")
            logger.error(f"❌ Exception testing entry {entry_id}: {e}")
            
        return test_result
        
    def validate_variant_behavior(self, variant_data: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
        """Validate variant data against expected behavior"""
        validation = {
            "overall_success": True,
            "failures": [],
            "successes": []
        }
        
        # Check if variants should exist
        has_variants = bool(variant_data["variant_items"])
        should_have_variants = expected.get("should_have_variants", False)
        
        if should_have_variants and not has_variants:
            validation["failures"].append("Expected variants but none found")
            validation["overall_success"] = False
        elif not should_have_variants and has_variants:
            validation["failures"].append(f"Expected no variants but found {len(variant_data['variant_items'])}")
            validation["overall_success"] = False
        elif should_have_variants and has_variants:
            validation["successes"].append("Variants found as expected")
            
        # Check variant count
        if "expected_variant_count" in expected:
            actual_count = len(variant_data["variant_items"])
            expected_count = expected["expected_variant_count"]
            if actual_count != expected_count:
                validation["failures"].append(f"Expected {expected_count} variants but found {actual_count}")
                validation["overall_success"] = False
            else:
                validation["successes"].append(f"Correct variant count: {actual_count}")
                
        # Check directions
        if "expected_directions" in expected:
            actual_directions = [item["direction"] for item in variant_data["variant_items"]]
            for expected_dir in expected["expected_directions"]:
                if expected_dir not in actual_directions:
                    validation["failures"].append(f"Missing expected direction: {expected_dir}")
                    validation["overall_success"] = False
                else:
                    validation["successes"].append(f"Found expected direction: {expected_dir}")
                    
        # Check referenced entries
        if "expected_refs" in expected:
            actual_refs = []
            for item in variant_data["variant_items"]:
                # Collect all possible reference values
                if "ref_value" in item and item["ref_value"] != "NO_INPUT_FIELD":
                    actual_refs.append(item["ref_value"])
                if "ref_id" in item:
                    actual_refs.append(item["ref_id"])
                if "ref_display" in item:
                    actual_refs.append(item["ref_display"])
                    
            for expected_ref in expected["expected_refs"]:
                # Check if the expected ref matches any of the actual refs (partial match for IDs)
                found = False
                for actual_ref in actual_refs:
                    # Match either by exact string match or by checking if one contains the other
                    # This handles cases where expected_ref is full ID but actual_ref is just headword
                    if (expected_ref == actual_ref or 
                        expected_ref in actual_ref or 
                        actual_ref in expected_ref or
                        # Check if the base headword matches (before the underscore)
                        expected_ref.split('_')[0] == actual_ref or
                        actual_ref == expected_ref.split('_')[0]):
                        found = True
                        break
                        
                if not found:
                    validation["failures"].append(f"Missing expected reference: {expected_ref} (found: {actual_refs})")
                    validation["overall_success"] = False
                else:
                    validation["successes"].append(f"Found expected reference: {expected_ref}")
        
        # Check for clickable links if expected
        if expected.get("should_have_clickable_links", False):
            links_found = 0
            for item in variant_data["variant_items"]:
                if "ref_link_href" in item and item["ref_link_href"]:
                    links_found += 1
                    
            if links_found == 0:
                validation["failures"].append("Expected clickable links but none found")
                validation["overall_success"] = False
            else:
                validation["successes"].append(f"Found {links_found} clickable link(s) as expected")
                    
        return validation
        
    def run_variant_relation_tests(self) -> Dict[str, Any]:
        """Run comprehensive tests for variant relation functionality"""
        
        test_cases = [
            {
                "entry_id": "Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf",
                "description": "Entry that IS a variant (should show outgoing relation with clickable link)",
                "expected_behavior": {
                    "should_have_variants": True,
                    "expected_variant_count": 1,
                    "expected_directions": ["outgoing"],
                    "expected_refs": ["Protestant ethic_64c53110-099c-446b-8e7f-e06517d47c92"],
                    "should_have_clickable_links": True
                }
            },
            {
                "entry_id": "Protestant ethic_64c53110-099c-446b-8e7f-e06517d47c92", 
                "description": "Entry that HAS variants (should show incoming relation with clickable link)",
                "expected_behavior": {
                    "should_have_variants": True,
                    "expected_variant_count": 1,
                    "expected_directions": ["incoming"],
                    "expected_refs": ["Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf"],
                    "should_have_clickable_links": True
                }
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
            for test_case in test_cases:
                logger.info(f"\n🧪 Running test: {test_case['description']}")
                
                result = self.test_entry_variant_ui(
                    test_case["entry_id"], 
                    test_case["expected_behavior"]
                )
                
                result["description"] = test_case["description"]
                overall_results["test_results"].append(result)
                
                if result["success"]:
                    overall_results["passed"] += 1
                    logger.info(f"✅ PASSED: {test_case['description']}")
                else:
                    overall_results["failed"] += 1
                    logger.error(f"❌ FAILED: {test_case['description']}")
                    
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
    print("=== COMPREHENSIVE VARIANT UI TESTING ===")
    
    tester = ComprehensiveUITester()
    results = tester.run_variant_relation_tests()
    
    print(f"\n{results['summary']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    
    if results['failed'] > 0:
        print("\n=== FAILED TESTS DETAILS ===")
        for result in results['test_results']:
            if not result['success']:
                print(f"\n❌ FAILED: {result['description']}")
                print(f"   Entry: {result['entry_id']}")
                print(f"   URL: {result['url']}")
                
                if result['critical_errors']:
                    print("   Critical Errors:")
                    for error in result['critical_errors']:
                        print(f"     • {error}")
                        
                if result['validation_results'].get('failures'):
                    print("   Validation Failures:")
                    for failure in result['validation_results']['failures']:
                        print(f"     • {failure}")
                        
                if result['variant_data'].get('errors'):
                    print("   Data Extraction Errors:")
                    for error in result['variant_data']['errors']:
                        print(f"     • {error}")
                        
                print(f"   Variant Items Found: {len(result['variant_data'].get('variant_items', []))}")
                for i, item in enumerate(result['variant_data'].get('variant_items', [])):
                    print(f"     Item {i+1}: {item}")
    
    return results['failed'] == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
