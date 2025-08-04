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
    """
    all_available_languages_dict = dict(load_available_languages()) # For easy name lookup

    if not current_app:
        # Fallback for contexts where app is not available
        # Return the raw list from YAML loader, or a hardcoded minimal if that fails too.
        return all_available_languages_dict.items() if all_available_languages_dict else [('en', 'English'), ('es', 'Spanish')]

    config_manager = current_app.config_manager
    
    # Use the correct methods that return dictionaries, not the list method
    source_lang_config = config_manager.get_source_language()
    target_lang_config = config_manager.get_target_language()

    source_code = source_lang_config.get('code')
    # Use the name from config settings, not from the general languages.yaml, for current vernacular
    source_name_from_config = source_lang_config.get('name', all_available_languages_dict.get(source_code, 'Source Language'))

    # Create the special display name for the source language (vernacular)
    source_lang_display_name = Markup(
        f'{source_name_from_config} '
        f'<i class="fas fa-info-circle text-muted ms-1" '
        f'data-bs-toggle="tooltip" data-bs-placement="top" '
        f'title="Vernacular (primary project language)"></i>'
    )

    # Prepare the final list of choices
    # Start with all available languages, then customize the source language display

    # Use a dictionary to ensure unique codes and allow easy update of the source language display
    # Initialize with all available languages (plain names)
    final_choices_dict = {code: name for code, name in all_available_languages_dict.items()}

    # If the configured source language is in our available list, update its display name
    if source_code and source_code in final_choices_dict:
        final_choices_dict[source_code] = source_lang_display_name
    elif source_code: # If source_code from settings is not in languages.yaml, add it with tooltip
        final_choices_dict[source_code] = source_lang_display_name

    # Ensure target language from settings is also present, using its configured name
    # (though it should already be in all_available_languages_dict if it's from languages.yaml)
    target_code = target_lang_config.get('code')
    if target_code and target_code not in final_choices_dict: # If target_code from settings is not in languages.yaml
        target_name_from_config = target_lang_config.get('name', 'Target Language')
        final_choices_dict[target_code] = target_name_from_config
    elif target_code and target_code in final_choices_dict and target_code != source_code:
        # If it is in the list, ensure we use the name from settings if it's different
        # and it's not the source language (which already has its special display name)
        target_name_from_config = target_lang_config.get('name', all_available_languages_dict.get(target_code))
        if target_name_from_config != final_choices_dict[target_code]:
             final_choices_dict[target_code] = target_name_from_config


    # Convert dictionary to list of tuples for SelectField choices
    # We might want a specific order, e.g., source, then target, then alphabetical.
    # For now, dictionary order (Python 3.7+) or sorted by code might be acceptable.

    # Let's create an ordered list: source, target, then the rest alphabetically by name
    ordered_choices = []

    # Add source language first
    if source_code and source_code in final_choices_dict:
        ordered_choices.append((source_code, final_choices_dict[source_code]))

    # Add target language second (if different from source)
    if target_code and target_code != source_code and target_code in final_choices_dict:
        ordered_choices.append((target_code, final_choices_dict[target_code]))

    # Add remaining languages, sorted by name
    # Exclude source and target if already added to avoid duplicates with potentially different display names
    remaining_langs = sorted(
        [(code, name) for code, name in final_choices_dict.items() if code not in [source_code, target_code]],
        key=lambda item: str(item[1]) # Sort by name (str() in case of Markup)
    )
    ordered_choices.extend(remaining_langs)

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
