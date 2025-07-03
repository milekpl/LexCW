#!/usr/bin/env python3
"""
Test script to directly test template rendering with mock variant data
"""

from jinja2 import Template

# Mock entry object with variant_relations
class MockEntry:
    def __init__(self):
        self.id = "Protestant work ethic_38cda8f9-199f-44b3-9bf0-bc2e08ba33bf"
        self.variant_relations = [
            {
                'ref': 'Protestant ethic_64c53110-099c-446b-8e7f-e06517d47c92',
                'variant_type': 'Unspecified Variant',
                'type': '_component-lexeme'
            }
        ]

# Test template fragment
template_code = """
// Initialize variant forms manager
if (window.VariantFormsManager && document.getElementById('variants-container')) {
    // Pass variant_relations data to JavaScript with safe fallback
    try {
        const variantRelations = {{ (entry.variant_relations or []) | tojson | safe }};
        console.log('[TEMPLATE DEBUG] Variant relations from template:', variantRelations);
        console.log('[TEMPLATE DEBUG] Variant relations length:', variantRelations.length);
        window.variantRelations = variantRelations;
    } catch (error) {
        console.warn('[TEMPLATE DEBUG] Failed to load variant relations:', error);
        window.variantRelations = [];
    }
    
    console.log('[TEMPLATE DEBUG] Initializing VariantFormsManager...');
    window.variantFormsManager = new VariantFormsManager('variants-container');
}
"""

# Test rendering
template = Template(template_code)
entry = MockEntry()

result = template.render(entry=entry)
print("Template rendered JavaScript:")
print("=" * 50)
print(result)
print("=" * 50)

# Test if the JSON serialization works
import json
serialized = json.dumps(entry.variant_relations)
print(f"JSON serialization of variant_relations: {serialized}")
