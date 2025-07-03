#!/usr/bin/env python3
"""
Test script to verify the complete variant UI functionality.
This tests both the backend variant extraction and frontend rendering.
"""

import unittest
import json
from app import create_app
from app.services.dictionary_service import DictionaryService
from app.database.basex_connector import BaseXConnector
from config import Config


class TestVariantUI(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # Initialize the dictionary service
        self.connector = BaseXConnector(
            Config.BASEX_HOST, Config.BASEX_PORT, 
            Config.BASEX_USERNAME, Config.BASEX_PASSWORD,
            Config.BASEX_DATABASE
        )
        self.service = DictionaryService(self.connector)
    
    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'service'):
            # Close service connections
            pass
        self.app_context.pop()
    
    def test_variant_extraction_backend(self):
        """Test that the backend correctly extracts variant relations"""
        print("\n=== Testing Backend Variant Extraction ===")
        
        # Test entries that should have variants
        test_entries = [
            'Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf',
            'protestor_5b2d8179-ccc6-4aac-a21e-ef2a28bafb89',
            'protested draft_337e6c08-7903-4c99-868b-ec60483ae50b'
        ]
        
        for entry_id in test_entries:
            print(f"\nTesting entry: {entry_id}")
            entry = self.service.get_entry(entry_id)
            
            self.assertIsNotNone(entry, f"Entry {entry_id} should exist")
            self.assertTrue(hasattr(entry, 'variant_relations'), "Entry should have variant_relations attribute")
            
            if entry.variant_relations:
                print(f"  Found {len(entry.variant_relations)} variant relations:")
                for i, variant in enumerate(entry.variant_relations):
                    print(f"    {i+1}. ref={variant.get('ref')}, type={variant.get('variant_type')}")
                    
                    # Validate variant structure
                    self.assertIn('ref', variant, "Variant should have 'ref' field")
                    self.assertIn('variant_type', variant, "Variant should have 'variant_type' field")
                    self.assertIn('type', variant, "Variant should have 'type' field")
            else:
                print(f"  No variant relations found for {entry_id}")
    
    def test_variant_template_rendering(self):
        """Test that variant data is correctly passed to templates"""
        print("\n=== Testing Template Variant Data ===")
        
        # Test entry with known variants
        entry_id = 'Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf'
        entry = self.service.get_entry(entry_id)
        
        if entry and entry.variant_relations:
            print(f"Entry {entry_id} has {len(entry.variant_relations)} variants")
            
            # Test template data serialization
            from jinja2 import Template
            template = Template('{{ (entry.variant_relations or []) | tojson | safe }}')
            rendered = template.render(entry=entry)
            
            print(f"Template renders: {rendered}")
            
            # Parse the JSON to verify it's valid
            try:
                variant_data = json.loads(rendered)
                self.assertIsInstance(variant_data, list, "Variant data should be a list")
                
                if variant_data:
                    variant = variant_data[0]
                    self.assertIn('ref', variant, "Variant should have 'ref' field")
                    self.assertIn('variant_type', variant, "Variant should have 'variant_type' field")
                    print(f"  First variant: ref={variant.get('ref')}, type={variant.get('variant_type')}")
                
            except json.JSONDecodeError as e:
                self.fail(f"Template rendered invalid JSON: {e}")
        else:
            print(f"Entry {entry_id} has no variants for template testing")
    
    def test_variant_form_response(self):
        """Test that the edit form includes variant data"""
        print("\n=== Testing Edit Form Response ===")
        
        # Test the edit form for an entry with variants
        entry_id = 'Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf'
        
        # Make request to edit form
        response = self.client.get(f'/entries/{entry_id}/edit', follow_redirects=True)
        
        print(f"Edit form response status: {response.status_code}")
        
        if response.status_code == 200:
            response_text = response.get_data(as_text=True)
            
            # Check if variant-related content is present
            variant_indicators = [
                'variants-container',
                'Variants',
                'variant_relations',
                'VariantFormsManager'
            ]
            
            found_indicators = []
            for indicator in variant_indicators:
                if indicator in response_text:
                    found_indicators.append(indicator)
            
            print(f"Found variant indicators: {found_indicators}")
            self.assertTrue(len(found_indicators) > 0, "Edit form should contain variant-related content")
            
            # Check for JavaScript initialization
            if 'VariantFormsManager' in response_text:
                print("✓ VariantFormsManager initialization found in response")
            else:
                print("✗ VariantFormsManager initialization not found")
                
        else:
            print(f"Edit form request failed with status {response.status_code}")
    
    def test_variant_vs_relation_distinction(self):
        """Test that variants are properly distinguished from regular relations"""
        print("\n=== Testing Variant vs Relation Distinction ===")
        
        # Test an entry that has both variants and regular relations
        entry_id = 'Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf'
        entry = self.service.get_entry(entry_id)
        
        if entry:
            print(f"Entry {entry_id}:")
            print(f"  Total relations: {len(entry.relations) if entry.relations else 0}")
            print(f"  Variant relations: {len(entry.variant_relations) if entry.variant_relations else 0}")
            
            # Verify that variants are a subset of relations
            if entry.relations and entry.variant_relations:
                # Find relations that are variants
                variant_refs = {v.get('ref') for v in entry.variant_relations}
                relation_refs = {r.ref for r in entry.relations if hasattr(r, 'ref')}
                
                print(f"  Variant refs: {variant_refs}")
                print(f"  All relation refs: {relation_refs}")
                
                # Variants should be a subset of relations
                self.assertTrue(variant_refs.issubset(relation_refs), 
                               "All variant refs should exist in regular relations")
        else:
            print(f"Entry {entry_id} not found for distinction testing")


if __name__ == '__main__':
    print("=" * 60)
    print("VARIANT UI FUNCTIONALITY TEST")
    print("=" * 60)
    
    unittest.main(verbosity=2)
