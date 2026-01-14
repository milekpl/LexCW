from __future__ import annotations
from typing import Dict, List, Tuple
from flask import current_app
from markupsafe import Markup # Changed from flask import Markup
import yaml
import os

def get_project_languages() -> List[Tuple[str, str]]:
    """
    Return a list of admissible language tuples (code, name) for the current project.
    The source language will have a special display name with a "Vernacular" tooltip.
    This list is suitable for dropdowns where such distinction is important (e.g., entry form notes).
    Only returns languages configured in project settings.
    """
    if not current_app:
        # Fallback for contexts where app is not available
        return [('en', 'English')]

    config_manager = current_app.config_manager
    
    # Use the correct methods that return dictionaries
    source_lang_config = config_manager.get_source_language()
    target_langs_config = config_manager.get_target_languages()

    source_code = source_lang_config.get('code')
    source_name = source_lang_config.get('name', 'Source Language')

    # Create the special display name for the source language (vernacular)
    source_lang_display_name = Markup(
        f'{source_name} '
        f'<i class="fas fa-info-circle text-muted ms-1" '
        f'data-bs-toggle="tooltip" data-bs-placement="top" '
        f'title="Vernacular (primary project language)"></i>'
    )

    # Create the list of language choices
    choices = [(source_code, source_lang_display_name)]
    
    # Add target languages
    for target_lang in target_langs_config:
        target_code = target_lang.get('code')
        target_name = target_lang.get('name', 'Target Language')
        if target_code and target_code != source_code:  # Skip duplicates
            choices.append((target_code, target_name))

    return choices

# Preserve other functions from the original file
def load_available_languages() -> List[Tuple[str, str]]:
    """Load available languages from the languages.yaml file."""
    languages_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        '..', 'static', 'data', 'languages.yaml'
    )
    
    try:
        with open(languages_file_path, 'r', encoding='utf-8') as f:
            languages_data = yaml.safe_load(f)
            return [(code, data['name']) for code, data in languages_data.items()]
    except Exception as e:
        # Fallback to a minimal set in case of errors
        return [('en', 'English'), ('es', 'Spanish'), ('fr', 'French')]

def get_language_choices_for_forms() -> List[Tuple[str, str]]:
    """
    Returns a simple list of (code, name) tuples for general form select fields,
    without the vernacular tooltip.
    """
    # This can be expanded or made configurable
    return load_available_languages() # Use the new loader
