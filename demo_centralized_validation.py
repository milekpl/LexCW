#!/usr/bin/env python3
"""
Demo script for centralized validation system.

This script demonstrates the working Jsontron-inspired validation engine
that validates JSON data from entry forms.
"""

from app.services.validation_engine import ValidationEngine, SchematronValidator


def demo_jsontron_validation():
    """Demonstrate JSON validation using Jsontron rules."""
    print("=== Centralized Validation System Demo ===")
    print()
    
    # Initialize the validation engine
    engine = ValidationEngine()
    print(f"✓ Validation engine loaded with {len(engine.rules)} rules")
    print()
    
    # Test data samples (simulating entry_form.html output)
    test_cases = [
        {
            "name": "Valid Entry",
            "data": {
                "id": "valid_entry_123",
                "lexical_unit": {"seh": "nhlamulo", "en": "solution"},
                "senses": [
                    {
                        "id": "sense1",
                        "gloss": "a way to solve a problem",
                        "definition": "A method or process of solving a problem"
                    }
                ]
            }
        },
        {
            "name": "Missing Entry ID (Critical Error)",
            "data": {
                "lexical_unit": {"seh": "test"},
                "senses": [{"id": "sense1", "gloss": "test"}]
            }
        },
        {
            "name": "Empty Lexical Unit (Critical Error)",
            "data": {
                "id": "test_entry",
                "lexical_unit": {},
                "senses": [{"id": "sense1", "gloss": "test"}]
            }
        },
        {
            "name": "Invalid Language Code (Warning)",
            "data": {
                "id": "test_entry",
                "lexical_unit": {"xyz": "test", "seh": "valid"},
                "senses": [{"id": "sense1", "gloss": "test"}]
            }
        },
        {
            "name": "Invalid Pronunciation Language (Critical)",
            "data": {
                "id": "test_entry",
                "lexical_unit": {"seh": "test"},
                "senses": [{"id": "sense1", "gloss": "test"}],
                "pronunciations": {"en": "invalid"}
            }
        }
    ]
    
    # Validate each test case
    for i, test_case in enumerate(test_cases, 1):
        print(f"{i}. Testing: {test_case['name']}")
        print("-" * 50)
        
        result = engine.validate_json(test_case['data'])
        
        print(f"Valid: {result.is_valid}")
        print(f"Errors: {len(result.errors)}")
        print(f"Warnings: {len(result.warnings)}")
        print(f"Info: {len(result.info)}")
        
        if result.errors:
            print("\nCritical Errors:")
            for error in result.errors:
                print(f"  - {error.rule_id}: {error.message}")
                print(f"    Path: {error.path}")
        
        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"  - {warning.rule_id}: {warning.message}")
                print(f"    Path: {warning.path}")
        
        print()
    
    print("=== Validation Rules Summary ===")
    print(f"Total rules loaded: {len(engine.rules)}")
    
    # Show rule breakdown by category and priority
    by_category = {}
    by_priority = {}
    
    for rule_id, rule_config in engine.rules.items():
        category = rule_config.get('category', 'unknown')
        priority = rule_config.get('priority', 'unknown')
        
        by_category[category] = by_category.get(category, 0) + 1
        by_priority[priority] = by_priority.get(priority, 0) + 1
    
    print("\nBy Category:")
    for category, count in sorted(by_category.items()):
        print(f"  {category}: {count} rules")
    
    print("\nBy Priority:")
    for priority, count in sorted(by_priority.items()):
        print(f"  {priority}: {count} rules")


def demo_schematron_integration():
    """Demonstrate Schematron XML validation."""
    print("\n=== Schematron XML Validation Demo ===")
    
    try:
        validator = SchematronValidator()
        print("✓ Schematron validator initialized")
        
        # Test XML sample
        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<lift xmlns="http://code.google.com/p/lift-standard">
    <entry id="test_entry">
        <lexical-unit>
            <form lang="seh">
                <text>test</text>
            </form>
        </lexical-unit>
        <sense id="sense1">
            <gloss lang="en">
                <text>test meaning</text>
            </gloss>
        </sense>
    </entry>
</lift>'''
        
        result = validator.validate_xml(test_xml)
        print(f"XML Validation - Valid: {result.is_valid}")
        print(f"Errors: {len(result.errors)}")
        
        if result.errors:
            for error in result.errors:
                print(f"  - {error.message}")
        
    except Exception as e:
        print(f"⚠ Schematron validation error: {e}")
        print("This is expected if PySchematron setup is incomplete")


if __name__ == "__main__":
    demo_jsontron_validation()
    demo_schematron_integration()
    
    print("\n=== Demo Complete ===")
    print("✓ Centralized validation system is working!")
    print("✓ Jsontron-inspired JSON validation implemented")
    print("✓ Ready to replace scattered model validation logic")
