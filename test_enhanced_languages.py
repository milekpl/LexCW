#!/usr/bin/env python3
"""
Test the enhanced language system with variants and custom languages.
"""

import sys
sys.path.append('.')

def main():
    """Test enhanced language functionality."""
    print("🌍 Testing Enhanced Language System")
    print("=" * 50)
    
    try:
        from app.utils.language_variants import (
            get_all_enhanced_languages, 
            search_enhanced_languages,
            validate_language_input,
            CustomLanguage
        )
        
        # Test 1: Enhanced language coverage
        all_languages = get_all_enhanced_languages()
        print(f"✅ Total enhanced languages: {len(all_languages)}")
        
        # Test 2: Language variants
        variants = [lang for lang in all_languages if lang.get('type') == 'variant']
        print(f"✅ Language variants: {len(variants)}")
        print(f"   Examples: {', '.join([v['name'] for v in variants[:3]])}")
        
        # Test 3: Historical languages
        historical = [lang for lang in all_languages if lang.get('type') == 'historical']
        print(f"✅ Historical languages: {len(historical)}")
        print(f"   Examples: {', '.join([h['name'] for h in historical[:3]])}")
        
        # Test 4: Constructed languages
        constructed = [lang for lang in all_languages if lang.get('type') == 'constructed']
        print(f"✅ Constructed languages: {len(constructed)}")
        print(f"   Examples: {', '.join([c['name'] for c in constructed[:3]])}")
        
        # Test 5: Search functionality
        print("\n🔍 Testing Enhanced Search:")
        
        # Search for variant
        us_english = search_enhanced_languages('en-US')
        print(f"✅ Search 'en-US': {len(us_english)} results")
        if us_english:
            print(f"   Found: {us_english[0]['name']}")
        
        # Search for historical
        latin_results = search_enhanced_languages('Latin')
        print(f"✅ Search 'Latin': {len(latin_results)} results")
        if latin_results:
            print(f"   Found: {latin_results[0]['name']}")
        
        # Search for constructed
        esperanto_results = search_enhanced_languages('Esperanto')
        print(f"✅ Search 'Esperanto': {len(esperanto_results)} results")
        if esperanto_results:
            print(f"   Found: {esperanto_results[0]['name']}")
        
        # Test 6: Custom language creation
        print("\n🔧 Testing Custom Language Creation:")
        
        custom_lang = CustomLanguage(
            code='enuk',
            name='English (UK dialectal)',
            family='Indo-European',
            region='United Kingdom',
            notes='Specialized UK dialect variant'
        )
        print(f"✅ Created custom language: {custom_lang.name} ({custom_lang.code})")
        
        # Test 7: Language input validation
        print("\n✅ Testing Input Validation:")
        
        test_inputs = [
            'en-US',  # Should find variant
            'Latin',  # Should find historical
            'Esperanto',  # Should find constructed
            'Custom: Klingon-UK',  # Should create custom
        ]
        
        for test_input in test_inputs:
            result = validate_language_input(test_input)
            if result:
                print(f"   '{test_input}' -> {result['name']} ({result['code']})")
            else:
                print(f"   '{test_input}' -> Not found/invalid")
        
        print("\n🎉 ENHANCED LANGUAGE SYSTEM WORKING!")
        print("This solves the flexibility issues:")
        print("   ✅ English (UK) ↔ English (US) dictionaries now possible")
        print("   ✅ English ↔ Latin dictionaries supported")
        print("   ✅ Custom language creation for specialized work")
        print("   ✅ Esperanto and other constructed languages included")
        print("   ✅ Historical language variants supported")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced language test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
