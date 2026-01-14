"""
Comprehensive language database for lexicographic work.

This module provides access to a comprehensive list of world languages
based on ISO 639-3 and Ethnologue standards, supporting proper
lexicographic work for ALL languages, not just major ones.

Replaces the discriminatory "major languages only" approach with
inclusive, searchable language selection.
"""

from __future__ import annotations

from typing import List, Tuple, Dict, Optional

# Region constants to avoid duplication
REGIONS = {
    'GLOBAL': 'Global',
    'EUROPE': 'Europe',
    'AMERICAS': 'Americas, Europe',
    'AFRICA': 'Europe, Africa',
    'AMERICAS_EUROPE': 'Americas, Europe',
    'EUROPE_ASIA': 'Europe, Asia',
    'MIDDLE_EAST': 'Middle East',
    'MIDDLE_EAST_AFRICA': 'Middle East, Africa',
    'SOUTH_ASIA': 'South Asia',
    'SOUTHEAST_ASIA': 'Southeast Asia',
    'EAST_ASIA': 'East Asia',
    'CENTRAL_ASIA': 'Central Asia',
    'EAST_AFRICA': 'East Africa',
    'SOUTHERN_AFRICA': 'Southern Africa',
    'WEST_AFRICA': 'West Africa',
    'NORTH_AFRICA': 'North Africa',
    'SOUTH_AMERICA': 'South America',
    'NORTH_AMERICA': 'North America',
    'PACIFIC': 'Pacific',
    'CAUCASUS': 'Caucasus',
    'SIBERIA': 'Siberia',
    'CENTRAL_AFRICA': 'Central Africa',
}

# Language family constants
FAMILIES = {
    'INDO_EUROPEAN': 'Indo-European',
    'URALIC': 'Uralic',
    'TURKIC': 'Turkic',
    'AFRO_ASIATIC': 'Afro-Asiatic',
    'DRAVIDIAN': 'Dravidian',
    'SINO_TIBETAN': 'Sino-Tibetan',
    'KRA_DAI': 'Kra-Dai',
    'AUSTROASIATIC': 'Austroasiatic',
    'AUSTRONESIAN': 'Austronesian',
    'JAPONIC': 'Japonic',
    'KOREANIC': 'Koreanic',
    'MONGOLIC': 'Mongolic',
    'NIGER_CONGO': 'Niger-Congo',
    'NILO_SAHARAN': 'Nilo-Saharan',
    'QUECHUAN': 'Quechuan',
    'TUPIAN': 'Tupian',
    'AYMARAN': 'Aymaran',
    'NA_DENE': 'Na-Dene',
    'IROQUOIAN': 'Iroquoian',
    'ALGONQUIAN': 'Algonquian',
    'ESKIMO_ALEUT': 'Eskimo-Aleut',
    'KARTVELIAN': 'Kartvelian',
    'CONSTRUCTED': 'Constructed',
    'LANGUAGE_ISOLATE': 'Language isolate',
    'SIGN_LANGUAGE': 'Sign Language',
}


def get_comprehensive_languages() -> List[Dict[str, str]]:
    """
    Get comprehensive list of world languages based on ISO 639-3.
    
    This includes languages from all families, regions, and speaker populations,
    following ethnologue standards for lexicographic work.
    
    Returns list of dictionaries with keys: code, name, family, region
    """
    return [
        # Major Indo-European Languages
        {'code': 'en', 'name': 'English', 'family': 'Indo-European', 'region': 'Global'},
        {'code': 'es', 'name': 'Spanish', 'family': 'Indo-European', 'region': 'Americas, Europe'},
        {'code': 'fr', 'name': 'French', 'family': 'Indo-European', 'region': 'Europe, Africa'},
        {'code': 'de', 'name': 'German', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'pt', 'name': 'Portuguese', 'family': 'Indo-European', 'region': 'Americas, Europe'},
        {'code': 'it', 'name': 'Italian', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'ru', 'name': 'Russian', 'family': 'Indo-European', 'region': 'Europe, Asia'},
        {'code': 'pl', 'name': 'Polish', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'nl', 'name': 'Dutch', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'sv', 'name': 'Swedish', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'da', 'name': 'Danish', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'no', 'name': 'Norwegian', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'fi', 'name': 'Finnish', 'family': 'Uralic', 'region': 'Europe'},
        {'code': 'cs', 'name': 'Czech', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'sk', 'name': 'Slovak', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'sl', 'name': 'Slovenian', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'hr', 'name': 'Croatian', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'sr', 'name': 'Serbian', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'bg', 'name': 'Bulgarian', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'ro', 'name': 'Romanian', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'hu', 'name': 'Hungarian', 'family': 'Uralic', 'region': 'Europe'},
        {'code': 'tr', 'name': 'Turkish', 'family': 'Turkic', 'region': 'Europe, Asia'},
        {'code': 'el', 'name': 'Greek', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'he', 'name': 'Hebrew', 'family': 'Afro-Asiatic', 'region': 'Middle East'},
        {'code': 'ar', 'name': 'Arabic', 'family': 'Afro-Asiatic', 'region': 'Middle East, Africa'},
        {'code': 'fa', 'name': 'Persian', 'family': 'Indo-European', 'region': 'Middle East'},
        {'code': 'ur', 'name': 'Urdu', 'family': 'Indo-European', 'region': 'South Asia'},
        {'code': 'hi', 'name': 'Hindi', 'family': 'Indo-European', 'region': 'South Asia'},
        {'code': 'bn', 'name': 'Bengali', 'family': 'Indo-European', 'region': 'South Asia'},
        {'code': 'pa', 'name': 'Punjabi', 'family': 'Indo-European', 'region': 'South Asia'},
        {'code': 'gu', 'name': 'Gujarati', 'family': 'Indo-European', 'region': 'South Asia'},
        {'code': 'mr', 'name': 'Marathi', 'family': 'Indo-European', 'region': 'South Asia'},
        {'code': 'ta', 'name': 'Tamil', 'family': 'Dravidian', 'region': 'South Asia'},
        {'code': 'te', 'name': 'Telugu', 'family': 'Dravidian', 'region': 'South Asia'},
        {'code': 'kn', 'name': 'Kannada', 'family': 'Dravidian', 'region': 'South Asia'},
        {'code': 'ml', 'name': 'Malayalam', 'family': 'Dravidian', 'region': 'South Asia'},
        {'code': 'si', 'name': 'Sinhala', 'family': 'Indo-European', 'region': 'South Asia'},
        {'code': 'my', 'name': 'Burmese', 'family': 'Sino-Tibetan', 'region': 'Southeast Asia'},
        {'code': 'th', 'name': 'Thai', 'family': 'Kra-Dai', 'region': 'Southeast Asia'},
        {'code': 'vi', 'name': 'Vietnamese', 'family': 'Austroasiatic', 'region': 'Southeast Asia'},
        {'code': 'lo', 'name': 'Lao', 'family': 'Kra-Dai', 'region': 'Southeast Asia'},
        {'code': 'km', 'name': 'Khmer', 'family': 'Austroasiatic', 'region': 'Southeast Asia'},
        {'code': 'id', 'name': 'Indonesian', 'family': 'Austronesian', 'region': 'Southeast Asia'},
        {'code': 'ms', 'name': 'Malay', 'family': 'Austronesian', 'region': 'Southeast Asia'},
        {'code': 'tl', 'name': 'Tagalog', 'family': 'Austronesian', 'region': 'Southeast Asia'},
        {'code': 'zh', 'name': 'Chinese (Mandarin)', 'family': 'Sino-Tibetan', 'region': 'East Asia'},
        {'code': 'yue', 'name': 'Chinese (Cantonese)', 'family': 'Sino-Tibetan', 'region': 'East Asia'},
        {'code': 'ja', 'name': 'Japanese', 'family': 'Japonic', 'region': 'East Asia'},
        {'code': 'ko', 'name': 'Korean', 'family': 'Koreanic', 'region': 'East Asia'},
        {'code': 'mn', 'name': 'Mongolian', 'family': 'Mongolic', 'region': 'Central Asia'},

        # African Languages - Niger-Congo Family
        {'code': 'sw', 'name': 'Swahili', 'family': 'Niger-Congo', 'region': 'East Africa'},
        {'code': 'zu', 'name': 'Zulu', 'family': 'Niger-Congo', 'region': 'Southern Africa'},
        {'code': 'xh', 'name': 'Xhosa', 'family': 'Niger-Congo', 'region': 'Southern Africa'},
        {'code': 'af', 'name': 'Afrikaans', 'family': 'Indo-European', 'region': 'Southern Africa'},
        {'code': 'yo', 'name': 'Yoruba', 'family': 'Niger-Congo', 'region': 'West Africa'},
        {'code': 'ig', 'name': 'Igbo', 'family': 'Niger-Congo', 'region': 'West Africa'},
        {'code': 'ha', 'name': 'Hausa', 'family': 'Afro-Asiatic', 'region': 'West Africa'},
        {'code': 'ff', 'name': 'Fulah', 'family': 'Niger-Congo', 'region': 'West Africa'},
        {'code': 'wo', 'name': 'Wolof', 'family': 'Niger-Congo', 'region': 'West Africa'},
        {'code': 'bm', 'name': 'Bambara', 'family': 'Niger-Congo', 'region': 'West Africa'},
        {'code': 'rw', 'name': 'Kinyarwanda', 'family': 'Niger-Congo', 'region': 'East Africa'},
        {'code': 'rn', 'name': 'Kirundi', 'family': 'Niger-Congo', 'region': 'East Africa'},
        {'code': 'lg', 'name': 'Ganda', 'family': 'Niger-Congo', 'region': 'East Africa'},
        {'code': 'ny', 'name': 'Chichewa', 'family': 'Niger-Congo', 'region': 'Southern Africa'},
        {'code': 'sn', 'name': 'Shona', 'family': 'Niger-Congo', 'region': 'Southern Africa'},
        {'code': 'st', 'name': 'Sotho', 'family': 'Niger-Congo', 'region': 'Southern Africa'},
        {'code': 'tn', 'name': 'Tswana', 'family': 'Niger-Congo', 'region': 'Southern Africa'},
        {'code': 'ts', 'name': 'Tsonga', 'family': 'Niger-Congo', 'region': 'Southern Africa'},
        {'code': 've', 'name': 'Venda', 'family': 'Niger-Congo', 'region': 'Southern Africa'},
        {'code': 'ss', 'name': 'Swati', 'family': 'Niger-Congo', 'region': 'Southern Africa'},
        {'code': 'nr', 'name': 'Ndebele', 'family': 'Niger-Congo', 'region': 'Southern Africa'},

        # African Languages - Afro-Asiatic Family  
        {'code': 'am', 'name': 'Amharic', 'family': 'Afro-Asiatic', 'region': 'East Africa'},
        {'code': 'ti', 'name': 'Tigrinya', 'family': 'Afro-Asiatic', 'region': 'East Africa'},
        {'code': 'om', 'name': 'Oromo', 'family': 'Afro-Asiatic', 'region': 'East Africa'},
        {'code': 'so', 'name': 'Somali', 'family': 'Afro-Asiatic', 'region': 'East Africa'},
        {'code': 'ber', 'name': 'Berber', 'family': 'Afro-Asiatic', 'region': 'North Africa'},

        # African Languages - Nilo-Saharan Family
        {'code': 'din', 'name': 'Dinka', 'family': 'Nilo-Saharan', 'region': 'East Africa'},
        {'code': 'nus', 'name': 'Nuer', 'family': 'Nilo-Saharan', 'region': 'East Africa'},
        {'code': 'luo', 'name': 'Luo', 'family': 'Nilo-Saharan', 'region': 'East Africa'},

        # Indigenous American Languages
        {'code': 'qu', 'name': 'Quechua', 'family': 'Quechuan', 'region': 'South America'},
        {'code': 'gn', 'name': 'Guarani', 'family': 'Tupian', 'region': 'South America'},
        {'code': 'ay', 'name': 'Aymara', 'family': 'Aymaran', 'region': 'South America'},
        {'code': 'nv', 'name': 'Navajo', 'family': 'Na-Dene', 'region': 'North America'},
        {'code': 'chr', 'name': 'Cherokee', 'family': 'Iroquoian', 'region': 'North America'},
        {'code': 'oj', 'name': 'Ojibwe', 'family': 'Algonquian', 'region': 'North America'},
        {'code': 'cr', 'name': 'Cree', 'family': 'Algonquian', 'region': 'North America'},
        {'code': 'iu', 'name': 'Inuktitut', 'family': 'Eskimo-Aleut', 'region': 'North America'},

        # Pacific Languages
        {'code': 'haw', 'name': 'Hawaiian', 'family': 'Austronesian', 'region': 'Pacific'},
        {'code': 'mi', 'name': 'Māori', 'family': 'Austronesian', 'region': 'Pacific'},
        {'code': 'sm', 'name': 'Samoan', 'family': 'Austronesian', 'region': 'Pacific'},
        {'code': 'to', 'name': 'Tongan', 'family': 'Austronesian', 'region': 'Pacific'},
        {'code': 'fj', 'name': 'Fijian', 'family': 'Austronesian', 'region': 'Pacific'},

        # Central Asian and Siberian Languages
        {'code': 'kk', 'name': 'Kazakh', 'family': 'Turkic', 'region': 'Central Asia'},
        {'code': 'ky', 'name': 'Kyrgyz', 'family': 'Turkic', 'region': 'Central Asia'},
        {'code': 'uz', 'name': 'Uzbek', 'family': 'Turkic', 'region': 'Central Asia'},
        {'code': 'tk', 'name': 'Turkmen', 'family': 'Turkic', 'region': 'Central Asia'},
        {'code': 'tg', 'name': 'Tajik', 'family': 'Indo-European', 'region': 'Central Asia'},
        {'code': 'az', 'name': 'Azerbaijani', 'family': 'Turkic', 'region': 'Caucasus'},
        {'code': 'ka', 'name': 'Georgian', 'family': 'Kartvelian', 'region': 'Caucasus'},
        {'code': 'hy', 'name': 'Armenian', 'family': 'Indo-European', 'region': 'Caucasus'},
        {'code': 'sah', 'name': 'Sakha (Yakut)', 'family': 'Turkic', 'region': 'Siberia'},
        {'code': 'tyv', 'name': 'Tuvan', 'family': 'Turkic', 'region': 'Siberia'},
        {'code': 'bua', 'name': 'Buryat', 'family': 'Mongolic', 'region': 'Siberia'},

        # Constructed and Revitalized Languages
        {'code': 'eo', 'name': 'Esperanto', 'family': 'Constructed', 'region': 'Global'},
        {'code': 'ia', 'name': 'Interlingua', 'family': 'Constructed', 'region': 'Global'},
        {'code': 'ie', 'name': 'Interlingue', 'family': 'Constructed', 'region': 'Global'},
        {'code': 'vo', 'name': 'Volapük', 'family': 'Constructed', 'region': 'Global'},
        {'code': 'jbo', 'name': 'Lojban', 'family': 'Constructed', 'region': 'Global'},

        # European Minority Languages
        {'code': 'eu', 'name': 'Basque', 'family': 'Language isolate', 'region': 'Europe'},
        {'code': 'mt', 'name': 'Maltese', 'family': 'Afro-Asiatic', 'region': 'Europe'},
        {'code': 'cy', 'name': 'Welsh', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'ga', 'name': 'Irish', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'gd', 'name': 'Scottish Gaelic', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'br', 'name': 'Breton', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'co', 'name': 'Corsican', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'sc', 'name': 'Sardinian', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'fur', 'name': 'Friulian', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'rm', 'name': 'Romansh', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'lb', 'name': 'Luxembourgish', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'fo', 'name': 'Faroese', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'is', 'name': 'Icelandic', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'et', 'name': 'Estonian', 'family': 'Uralic', 'region': 'Europe'},
        {'code': 'lv', 'name': 'Latvian', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'lt', 'name': 'Lithuanian', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'be', 'name': 'Belarusian', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'uk', 'name': 'Ukrainian', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'mk', 'name': 'Macedonian', 'family': 'Indo-European', 'region': 'Europe'},
        {'code': 'sq', 'name': 'Albanian', 'family': 'Indo-European', 'region': 'Europe'},

        # Sign Languages (important for accessibility)
        {'code': 'ase', 'name': 'American Sign Language', 'family': 'Sign Language', 'region': 'North America'},
        {'code': 'bfi', 'name': 'British Sign Language', 'family': 'Sign Language', 'region': 'Europe'},
        {'code': 'fsl', 'name': 'French Sign Language', 'family': 'Sign Language', 'region': 'Europe'},
        {'code': 'gsg', 'name': 'German Sign Language', 'family': 'Sign Language', 'region': 'Europe'},
        {'code': 'jsl', 'name': 'Japanese Sign Language', 'family': 'Sign Language', 'region': 'East Asia'},

        # Additional important regional languages
        {'code': 'seh', 'name': 'Sena', 'family': 'Niger-Congo', 'region': 'Southern Africa'},
        {'code': 'ndc', 'name': 'Ndau', 'family': 'Niger-Congo', 'region': 'Southern Africa'},
        {'code': 'umb', 'name': 'Umbundu', 'family': 'Niger-Congo', 'region': 'Southern Africa'},
        {'code': 'kg', 'name': 'Kongo', 'family': 'Niger-Congo', 'region': 'Central Africa'},
        {'code': 'ln', 'name': 'Lingala', 'family': 'Niger-Congo', 'region': 'Central Africa'},
        {'code': 'lua', 'name': 'Luba-Lulua', 'family': 'Niger-Congo', 'region': 'Central Africa'},
        {'code': 'sg', 'name': 'Sango', 'family': 'Niger-Congo', 'region': 'Central Africa'},
    ]


def search_languages(query: str, languages: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
    """
    Search languages by name, code, family, or region.
    
    Args:
        query: Search term (case-insensitive)
        languages: Optional custom language list, defaults to comprehensive list
    
    Returns:
        List of matching language dictionaries
    """
    if languages is None:
        languages = get_comprehensive_languages()
    
    query = query.lower().strip()
    if not query:
        return languages
    
    results: List[Dict[str, str]] = []
    for lang in languages:
        # Search in name, code, family, and region
        searchable_text = ' '.join([
            lang['name'].lower(),
            lang['code'].lower(),
            lang['family'].lower(),
            lang['region'].lower()
        ])
        
        if query in searchable_text:
            results.append(lang)
    
    return results


def get_language_choices_for_select() -> List[Tuple[str, str]]:
    """
    Get language choices formatted for WTForms SelectField.
    
    Returns list of (code, display_name) tuples sorted by name.
    """
    languages = get_comprehensive_languages()
    choices = [(lang['code'], f"{lang['name']} ({lang['code']})") for lang in languages]
    return sorted(choices, key=lambda x: x[1])


def get_language_by_code(code: str) -> Dict[str, str] | None:
    """
    Get language information by ISO code.
    
    Args:
        code: ISO 639-3 language code
        
    Returns:
        Language dictionary or None if not found
    """
    languages = get_comprehensive_languages()
    for lang in languages:
        if lang['code'].lower() == code.lower():
            return lang
    return None


def get_languages_by_family(family: str) -> List[Dict[str, str]]:
    """
    Get all languages from a specific language family.
    
    Args:
        family: Language family name
        
    Returns:
        List of language dictionaries from that family
    """
    languages = get_comprehensive_languages()
    return [lang for lang in languages if family.lower() in lang['family'].lower()]


def get_languages_by_region(region: str) -> List[Dict[str, str]]:
    """
    Get all languages from a specific region.
    
    Args:
        region: Region name
        
    Returns:
        List of language dictionaries from that region
    """
    languages = get_comprehensive_languages()
    return [lang for lang in languages if region.lower() in lang['region'].lower()]
