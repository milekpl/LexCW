"""
Language choices data module.

This module provides predefined language options for the settings form.
This solves the "UX nightmare" by giving users proper language choices
instead of forcing them to type language codes manually.
"""

from __future__ import annotations

from typing import List, Tuple


def get_common_languages() -> List[Tuple[str, str]]:
    """
    Get list of common languages for lexicographic work.
    
    Returns list of (code, name) tuples for use in form choices.
    These are major world languages commonly used in dictionary projects.
    """
    return [
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('pt', 'Portuguese'),
        ('it', 'Italian'),
        ('ru', 'Russian'),
        ('ar', 'Arabic'),
        ('zh', 'Chinese'),
        ('ja', 'Japanese'),
        ('ko', 'Korean'),
        ('hi', 'Hindi'),
        ('sw', 'Swahili'),
        ('pl', 'Polish'),
        ('nl', 'Dutch'),
        ('sv', 'Swedish'),
        ('da', 'Danish'),
        ('no', 'Norwegian'),
        ('fi', 'Finnish'),
        ('tr', 'Turkish'),
        ('th', 'Thai'),
        ('vi', 'Vietnamese'),
        ('he', 'Hebrew'),
        ('cs', 'Czech'),
        ('hu', 'Hungarian'),
        ('ro', 'Romanian'),
        ('bg', 'Bulgarian'),
        ('hr', 'Croatian'),
        ('sk', 'Slovak'),
        ('sl', 'Slovenian'),
    ]


def get_source_language_choices() -> List[Tuple[str, str]]:
    """
    Get language choices specifically for source/vernacular languages.
    
    Returns same list as common languages - any language can be a source language.
    """
    return get_common_languages()


def get_target_language_choices() -> List[Tuple[str, str]]:
    """
    Get language choices for target languages (definitions/translations).
    
    Returns same list as common languages - any language can be used for definitions.
    """
    return get_common_languages()
