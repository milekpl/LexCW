"""
Enhanced comprehensive language database with variants and custom language support.

This module provides:
1. Language variants (English UK/US, Spanish Spain/Mexico, etc.)
2. Historical and classical languages (Latin, Ancient Greek, Sanskrit)
3. Constructed languages (Esperanto, Klingon, etc.)
4. Custom language input for specialized lexicographic work
5. Validation and normalization of language inputs
"""

from __future__ import annotations
from typing import Any, Optional
import re


def get_language_variants() -> list[dict[str, str]]:
    """
    Get language variants that address common lexicographic needs.
    
    Returns:
        List of language variant dictionaries with detailed metadata
    """
    return [
        # English variants
        {'code': 'en', 'name': 'English', 'family': 'Indo-European', 'region': 'Global', 'type': 'base'},
        {'code': 'en-GB', 'name': 'English (United Kingdom)', 'family': 'Indo-European', 'region': 'Europe', 'type': 'variant', 'base': 'en', 'notes': 'British spelling, vocabulary'},
        {'code': 'en-US', 'name': 'English (United States)', 'family': 'Indo-European', 'region': 'North America', 'type': 'variant', 'base': 'en', 'notes': 'American spelling, vocabulary'},
        {'code': 'en-AU', 'name': 'English (Australia)', 'family': 'Indo-European', 'region': 'Oceania', 'type': 'variant', 'base': 'en', 'notes': 'Australian spelling, vocabulary'},
        {'code': 'en-CA', 'name': 'English (Canada)', 'family': 'Indo-European', 'region': 'North America', 'type': 'variant', 'base': 'en', 'notes': 'Canadian spelling, vocabulary'},
        {'code': 'en-IN', 'name': 'English (India)', 'family': 'Indo-European', 'region': 'South Asia', 'type': 'variant', 'base': 'en', 'notes': 'Indian English variety'},
        
        # Spanish variants
        {'code': 'es', 'name': 'Spanish', 'family': 'Indo-European', 'region': 'Global', 'type': 'base'},
        {'code': 'es-ES', 'name': 'Spanish (Spain)', 'family': 'Indo-European', 'region': 'Europe', 'type': 'variant', 'base': 'es', 'notes': 'Peninsular Spanish'},
        {'code': 'es-MX', 'name': 'Spanish (Mexico)', 'family': 'Indo-European', 'region': 'North America', 'type': 'variant', 'base': 'es', 'notes': 'Mexican Spanish'},
        {'code': 'es-AR', 'name': 'Spanish (Argentina)', 'family': 'Indo-European', 'region': 'South America', 'type': 'variant', 'base': 'es', 'notes': 'Argentinian Spanish'},
        {'code': 'es-CO', 'name': 'Spanish (Colombia)', 'family': 'Indo-European', 'region': 'South America', 'type': 'variant', 'base': 'es', 'notes': 'Colombian Spanish'},
        
        # French variants
        {'code': 'fr', 'name': 'French', 'family': 'Indo-European', 'region': 'Global', 'type': 'base'},
        {'code': 'fr-FR', 'name': 'French (France)', 'family': 'Indo-European', 'region': 'Europe', 'type': 'variant', 'base': 'fr', 'notes': 'Metropolitan French'},
        {'code': 'fr-CA', 'name': 'French (Canada)', 'family': 'Indo-European', 'region': 'North America', 'type': 'variant', 'base': 'fr', 'notes': 'Canadian French'},
        {'code': 'fr-CH', 'name': 'French (Switzerland)', 'family': 'Indo-European', 'region': 'Europe', 'type': 'variant', 'base': 'fr', 'notes': 'Swiss French'},
        
        # Portuguese variants
        {'code': 'pt', 'name': 'Portuguese', 'family': 'Indo-European', 'region': 'Global', 'type': 'base'},
        {'code': 'pt-BR', 'name': 'Portuguese (Brazil)', 'family': 'Indo-European', 'region': 'South America', 'type': 'variant', 'base': 'pt', 'notes': 'Brazilian Portuguese'},
        {'code': 'pt-PT', 'name': 'Portuguese (Portugal)', 'family': 'Indo-European', 'region': 'Europe', 'type': 'variant', 'base': 'pt', 'notes': 'European Portuguese'},
        
        # German variants
        {'code': 'de', 'name': 'German', 'family': 'Indo-European', 'region': 'Europe', 'type': 'base'},
        {'code': 'de-DE', 'name': 'German (Germany)', 'family': 'Indo-European', 'region': 'Europe', 'type': 'variant', 'base': 'de', 'notes': 'Standard German'},
        {'code': 'de-AT', 'name': 'German (Austria)', 'family': 'Indo-European', 'region': 'Europe', 'type': 'variant', 'base': 'de', 'notes': 'Austrian German'},
        {'code': 'de-CH', 'name': 'German (Switzerland)', 'family': 'Indo-European', 'region': 'Europe', 'type': 'variant', 'base': 'de', 'notes': 'Swiss German'},
        
        # Arabic variants
        {'code': 'ar', 'name': 'Arabic', 'family': 'Afro-Asiatic', 'region': 'Middle East, Africa', 'type': 'base'},
        {'code': 'ar-SA', 'name': 'Arabic (Saudi Arabia)', 'family': 'Afro-Asiatic', 'region': 'Middle East', 'type': 'variant', 'base': 'ar', 'notes': 'Saudi Arabic'},
        {'code': 'ar-EG', 'name': 'Arabic (Egypt)', 'family': 'Afro-Asiatic', 'region': 'North Africa', 'type': 'variant', 'base': 'ar', 'notes': 'Egyptian Arabic'},
        {'code': 'ar-MA', 'name': 'Arabic (Morocco)', 'family': 'Afro-Asiatic', 'region': 'North Africa', 'type': 'variant', 'base': 'ar', 'notes': 'Moroccan Arabic'},
        
        # Chinese variants
        {'code': 'zh', 'name': 'Chinese', 'family': 'Sino-Tibetan', 'region': 'East Asia', 'type': 'base'},
        {'code': 'zh-CN', 'name': 'Chinese (Simplified)', 'family': 'Sino-Tibetan', 'region': 'East Asia', 'type': 'variant', 'base': 'zh', 'notes': 'Simplified characters'},
        {'code': 'zh-TW', 'name': 'Chinese (Traditional)', 'family': 'Sino-Tibetan', 'region': 'East Asia', 'type': 'variant', 'base': 'zh', 'notes': 'Traditional characters'},
        {'code': 'zh-HK', 'name': 'Chinese (Hong Kong)', 'family': 'Sino-Tibetan', 'region': 'East Asia', 'type': 'variant', 'base': 'zh', 'notes': 'Hong Kong Cantonese'},
    ]


def get_historical_languages() -> list[dict[str, str]]:
    """
    Get historical and classical languages commonly used in lexicographic work.
    
    Returns:
        List of historical language dictionaries
    """
    return [
        # Classical European
        {'code': 'la', 'name': 'Latin', 'family': 'Indo-European', 'region': 'Historical', 'type': 'historical', 'notes': 'Classical and Medieval Latin'},
        {'code': 'grc', 'name': 'Ancient Greek', 'family': 'Indo-European', 'region': 'Historical', 'type': 'historical', 'notes': 'Classical Greek'},
        {'code': 'got', 'name': 'Gothic', 'family': 'Indo-European', 'region': 'Historical', 'type': 'historical', 'notes': 'Extinct Germanic language'},
        {'code': 'ang', 'name': 'Old English', 'family': 'Indo-European', 'region': 'Historical', 'type': 'historical', 'notes': 'Anglo-Saxon'},
        {'code': 'fro', 'name': 'Old French', 'family': 'Indo-European', 'region': 'Historical', 'type': 'historical', 'notes': 'Medieval French'},
        {'code': 'gmh', 'name': 'Middle High German', 'family': 'Indo-European', 'region': 'Historical', 'type': 'historical', 'notes': 'Medieval German'},
        
        # Classical Non-European
        {'code': 'sa', 'name': 'Sanskrit', 'family': 'Indo-European', 'region': 'Historical', 'type': 'historical', 'notes': 'Classical Sanskrit'},
        {'code': 'pi', 'name': 'Pali', 'family': 'Indo-European', 'region': 'Historical', 'type': 'historical', 'notes': 'Buddhist canonical language'},
        {'code': 'syc', 'name': 'Classical Syriac', 'family': 'Afro-Asiatic', 'region': 'Historical', 'type': 'historical', 'notes': 'Aramaic dialect'},
        {'code': 'cop', 'name': 'Coptic', 'family': 'Afro-Asiatic', 'region': 'Historical', 'type': 'historical', 'notes': 'Late Egyptian'},
        {'code': 'sux', 'name': 'Sumerian', 'family': 'Language isolate', 'region': 'Historical', 'type': 'historical', 'notes': 'Ancient Mesopotamian'},
        {'code': 'akk', 'name': 'Akkadian', 'family': 'Afro-Asiatic', 'region': 'Historical', 'type': 'historical', 'notes': 'Ancient Mesopotamian'},
    ]


def get_constructed_languages() -> list[dict[str, str]]:
    """
    Get constructed languages that may be relevant for lexicographic work.
    
    Returns:
        List of constructed language dictionaries
    """
    return [
        # International Auxiliary Languages
        {'code': 'eo', 'name': 'Esperanto', 'family': 'Constructed', 'region': 'Global', 'type': 'constructed', 'notes': 'International auxiliary language'},
        {'code': 'ia', 'name': 'Interlingua', 'family': 'Constructed', 'region': 'Global', 'type': 'constructed', 'notes': 'Naturalistic auxiliary language'},
        {'code': 'ie', 'name': 'Interlingue', 'family': 'Constructed', 'region': 'Global', 'type': 'constructed', 'notes': 'Occidental language'},
        {'code': 'vo', 'name': 'Volapük', 'family': 'Constructed', 'region': 'Global', 'type': 'constructed', 'notes': 'Early auxiliary language'},
        {'code': 'ido', 'name': 'Ido', 'family': 'Constructed', 'region': 'Global', 'type': 'constructed', 'notes': 'Reformed Esperanto'},
        
        # Fictional Languages
        {'code': 'tlh', 'name': 'Klingon', 'family': 'Constructed', 'region': 'Fictional', 'type': 'constructed', 'notes': 'Star Trek universe'},
        {'code': 'sjn', 'name': 'Sindarin', 'family': 'Constructed', 'region': 'Fictional', 'type': 'constructed', 'notes': 'Tolkien Elvish'},
        {'code': 'qya', 'name': 'Quenya', 'family': 'Constructed', 'region': 'Fictional', 'type': 'constructed', 'notes': 'Tolkien High Elvish'},
        {'code': 'dot', 'name': 'Dothraki', 'family': 'Constructed', 'region': 'Fictional', 'type': 'constructed', 'notes': 'Game of Thrones'},
        {'code': 'hbo', 'name': 'High Valyrian', 'family': 'Constructed', 'region': 'Fictional', 'type': 'constructed', 'notes': 'Game of Thrones'},
        
        # Artistic Languages
        {'code': 'loj', 'name': 'Lojban', 'family': 'Constructed', 'region': 'Global', 'type': 'constructed', 'notes': 'Logical language'},
        {'code': 'tpi', 'name': 'Na\'vi', 'family': 'Constructed', 'region': 'Fictional', 'type': 'constructed', 'notes': 'Avatar movie'},
    ]


class CustomLanguage:
    """
    Represents a custom language that users can define for specialized work.
    """
    
    def __init__(self, code: str, name: str, family: Optional[str] = None, 
                 region: Optional[str] = None, notes: Optional[str] = None):
        self.code = self._validate_code(code)
        self.name = self._validate_name(name)
        self.family = family or 'Custom'
        self.region = region or 'User-defined'
        self.notes = notes
        self.type = 'custom'
    
    def _validate_code(self, code: str) -> str:
        """Validate and normalize language code."""
        code = code.strip().lower()
        if not re.match(r'^[a-z]{2,3}(-[A-Z]{2})?(-[a-z]+)?$', code):
            # Allow more flexible custom codes
            if not re.match(r'^[a-z0-9_-]{2,10}$', code):
                raise ValueError(f"Invalid language code format: {code}")
        return code
    
    def _validate_name(self, name: str) -> str:
        """Validate and normalize language name."""
        name = name.strip()
        if not name or len(name) < 2:
            raise ValueError("Language name must be at least 2 characters")
        if len(name) > 100:
            raise ValueError("Language name too long (max 100 characters)")
        return name
    
    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary format compatible with other language functions."""
        result = {
            'code': self.code,
            'name': self.name,
            'family': self.family,
            'region': self.region,
            'type': self.type
        }
        if self.notes:
            result['notes'] = self.notes
        return result


def validate_language_input(input_str: str) -> dict[str, str] | None:
    """
    Validate and parse language input from user.
    
    Supports formats:
    - "en" -> finds English
    - "en-US" -> finds English (United States)
    - "Latin" -> finds Latin
    - "MyLang (custom)" -> creates custom language
    
    Args:
        input_str: User input string
        
    Returns:
        Language dictionary if valid, None if invalid
    """
    input_str = input_str.strip()
    if not input_str:
        return None
    
    # First, try to find in existing languages (avoid circular import)
    try:
        from app.utils.comprehensive_languages import search_languages
        results = search_languages(input_str)
        if results:
            return results[0]  # Return first match
    except ImportError:
        pass
    
    # Check variants and historical/constructed languages
    all_special_languages = (get_language_variants() + 
                           get_historical_languages() + 
                           get_constructed_languages())
    
    for lang in all_special_languages:
        if (lang['code'].lower() == input_str.lower() or 
            lang['name'].lower() == input_str.lower()):
            return lang
    
    # If not found and contains "(custom)" or similar markers, create custom
    custom_markers = ['(custom)', '(user-defined)', '(specialized)']
    is_custom = any(marker in input_str.lower() for marker in custom_markers)
    
    if is_custom or len(input_str.split()) <= 3:  # Likely a custom language
        try:
            # Extract name and generate code
            name = re.sub(r'\([^)]*\)', '', input_str).strip()
            code = generate_custom_code(name)
            
            custom = CustomLanguage(code=code, name=name, notes="User-defined language")
            return custom.to_dict()
        except ValueError:
            return None
    
    return None


def generate_custom_code(name: str) -> str:
    """
    Generate a custom language code from a name.
    
    Args:
        name: Language name
        
    Returns:
        Generated language code
    """
    # Take first 2-3 letters of first word
    words = name.split()
    if not words:
        return "cust"
    
    first_word = re.sub(r'[^a-zA-Z]', '', words[0])
    if len(first_word) >= 3:
        return first_word[:3].lower()
    elif len(first_word) == 2:
        return first_word.lower()
    else:
        # Fallback
        return "cust"


def get_all_enhanced_languages() -> list[dict[str, str]]:
    """
    Get all languages including variants, historical, and constructed languages.
    
    Returns:
        Complete list of all supported languages
    """
    # Import here to avoid circular imports
    try:
        from app.utils.comprehensive_languages import get_comprehensive_languages
        base_languages = get_comprehensive_languages()
    except ImportError:
        # Fallback if comprehensive_languages is not available
        base_languages = []
    
    variants = get_language_variants()
    historical = get_historical_languages()
    constructed = get_constructed_languages()
    
    # Combine all, removing duplicates based on code
    all_languages = {}
    
    for lang_list in [base_languages, variants, historical, constructed]:
        for lang in lang_list:
            all_languages[lang['code']] = lang
    
    return list(all_languages.values())


def search_enhanced_languages(query: str) -> list[dict[str, str]]:
    """
    Search all enhanced languages including variants and custom language support.
    
    Args:
        query: Search term
        
    Returns:
        List of matching languages
    """
    if not query:
        return []
    
    query = query.lower().strip()
    all_languages = get_all_enhanced_languages()
    
    results = []
    
    for lang in all_languages:
        # Search in code, name, family, region, and notes
        searchable_fields = [
            lang.get('code', ''),
            lang.get('name', ''),
            lang.get('family', ''),
            lang.get('region', ''),
            lang.get('notes', '')
        ]
        
        searchable_text = ' '.join(searchable_fields).lower()
        
        if query in searchable_text:
            results.append(lang)
    
    # Sort by relevance (exact matches first, then name matches, then others)
    def sort_key(lang):
        name = lang.get('name', '').lower()
        code = lang.get('code', '').lower()
        
        if code == query:
            return (0, name)  # Exact code match
        elif name == query:
            return (1, name)  # Exact name match
        elif name.startswith(query):
            return (2, name)  # Name starts with query
        elif query in name:
            return (3, name)  # Query in name
        else:
            return (4, name)  # Other matches
    
    results.sort(key=sort_key)
    return results
