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

    # Create the list of language choices - start with source language
    ordered_choices = [(source_code, source_lang_display_name)]
    
    # Add all target languages
    for target_lang in target_langs_config:
        target_code = target_lang.get('code')
        target_name = target_lang.get('name', 'Target Language')
        if target_code and target_code != source_code:  # Skip duplicates
            ordered_choices.append((target_code, target_name))

    return ordered_choices


def get_language_choices_for_forms() -> List[Tuple[str, str]]:
    """
    Returns a simple list of (code, name) tuples for general form select fields,
    without the vernacular tooltip.
    """
    # This can be expanded or made configurable
    return load_available_languages() # Use the new loader


_language_cache = None

def load_available_languages() -> List[Tuple[str, str]]:
    """
    Loads a list of (code, name) language tuples from app/data/languages.yaml.
    Caches the result for subsequent calls.
    Returns a default list if the file is not found or is invalid.
    """
    global _language_cache
    if _language_cache is not None:
        return _language_cache

    default_fallback_languages = [('en', 'English (Default)'), ('es', 'Spanish (Default)')]

    try:
        # Correctly determine the path to app/data/languages.yaml
        # __file__ is the path to the current file (language_utils.py)
        # os.path.dirname(__file__) is app/utils/
        # os.path.dirname(os.path.dirname(__file__)) is app/
        current_dir = os.path.dirname(os.path.abspath(__file__)) # app/utils
        app_dir = os.path.dirname(current_dir) # app/
        yaml_path = os.path.join(app_dir, 'data', 'languages.yaml')

        if not os.path.exists(yaml_path):
            current_app.logger.warning(f"languages.yaml not found at {yaml_path}. Using default languages.")
            _language_cache = default_fallback_languages
            return _language_cache

        with open(yaml_path, 'r', encoding='utf-8') as f:
            languages_data = yaml.safe_load(f)

        if not languages_data or not isinstance(languages_data, list):
            current_app.logger.warning(f"languages.yaml at {yaml_path} is empty or not a list. Using default languages.")
            _language_cache = default_fallback_languages
            return _language_cache

        loaded_languages = []
        for lang_entry in languages_data:
            if isinstance(lang_entry, dict) and 'code' in lang_entry and 'name' in lang_entry:
                loaded_languages.append((str(lang_entry['code']), str(lang_entry['name'])))
            else:
                current_app.logger.warning(f"Skipping invalid language entry in {yaml_path}: {lang_entry}")

        if not loaded_languages: # If all entries were invalid
            current_app.logger.warning(f"No valid language entries found in {yaml_path}. Using default languages.")
            _language_cache = default_fallback_languages
        else:
            _language_cache = loaded_languages

        return _language_cache
    except FileNotFoundError:
        current_app.logger.error(f"Critical: languages.yaml definitely not found at {yaml_path} (FileNotFoundError). Using default languages.")
        _language_cache = default_fallback_languages
        return _language_cache
    except yaml.YAMLError as e:
        current_app.logger.error(f"Error parsing languages.yaml at {yaml_path}: {e}. Using default languages.")
        _language_cache = default_fallback_languages
        return _language_cache
    except Exception as e:
        # Catch any other unexpected errors during loading
        current_app.logger.error(f"Unexpected error loading languages.yaml: {e}. Using default languages.")
        _language_cache = default_fallback_languages
        return _language_cache
