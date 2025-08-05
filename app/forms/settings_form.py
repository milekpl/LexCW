"""
Settings form for configuring project languages and preferences.

This form provides comprehensive language selection capabilities
including searchable dropdowns and dynamic target language selection.
"""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, validators
from wtforms.validators import DataRequired, Length, Optional
from typing import Dict, Any, List, Union
import json

from app.utils.comprehensive_languages import (
    get_language_choices_for_select,
    get_language_by_code,
    get_comprehensive_languages
)
from app.forms.searchable_language_field import SearchableLanguageMultiSelectField


class SettingsForm(FlaskForm):
    """
    Form for configuring project settings with comprehensive language support.
    
    Features:
    - Searchable source language dropdown with 150+ languages
    - Dynamic target language selection with search functionality
    - Support for all major world languages and language families
    - Accessibility-friendly with sign languages included
    """

    # Project identification
    project_name = StringField(
        'Project Name',
        validators=[DataRequired(), Length(min=1, max=200)],
        description='Name of your lexicographic project'
    )

    # Source language selection - comprehensive dropdown
    source_language_code = SelectField(
        'Source Language',
        validators=[DataRequired()],
        description='Primary language being documented',
        coerce=str
    )

    source_language_name = StringField(
        'Source Language Name',
        validators=[Optional(), Length(max=100)],
        description='Custom name for source language (optional)'
    )

    # Target languages - dynamic searchable multi-select
    available_target_languages = SearchableLanguageMultiSelectField(
        'Target Languages',
        description='Languages used for definitions, translations, and cross-references'
    )

    # Submit button
    submit = SubmitField('Update Settings')

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize form with comprehensive language choices."""
        super().__init__(*args, **kwargs)
        
        # Populate source language dropdown with all available languages
        # Use try-catch to handle cases where Flask context is not available (like in unit tests)
        try:
            language_choices = get_language_choices_for_select()
            # Add empty option at the beginning
            self.source_language_code.choices = [('', 'Select a language...')] + language_choices
        except RuntimeError:
            # Fall back to basic choices if no Flask context (unit tests)
            basic_choices = [
                ('en', 'English'),
                ('es', 'Spanish'),
                ('fr', 'French'),
                ('de', 'German'),
                ('zh', 'Chinese'),
                ('ar', 'Arabic'),
                ('pt', 'Portuguese'),
                ('ru', 'Russian'),
                ('ja', 'Japanese'),
                ('ko', 'Korean')
            ]
            self.source_language_code.choices = [('', 'Select a language...')] + basic_choices

    def populate_from_config(self, config: Union[Dict[str, Any], Any]) -> None:
        """
        Populate form fields from configuration data.
        
        Args:
            config: Configuration object or dictionary with project settings
        """
        if hasattr(config, 'get_project_name'):
            # Config manager object
            self.project_name.data = config.get_project_name() or ''
            
            source_lang = config.get_source_language()
            if source_lang and isinstance(source_lang, dict):
                self.source_language_code.data = source_lang.get('code', '')
                self.source_language_name.data = source_lang.get('name', '')
            
            target_langs = config.get_target_languages()
            if target_langs and isinstance(target_langs, list):
                # Extract language codes from target languages
                target_codes = []
                for lang in target_langs:
                    if isinstance(lang, dict) and 'code' in lang:
                        target_codes.append(lang['code'])
                    elif isinstance(lang, str):
                        target_codes.append(lang)
                self.available_target_languages.populate_from_codes(target_codes)
        
        elif isinstance(config, dict):
            # Dictionary configuration
            self.project_name.data = config.get('project_name', '')
            
            source_lang = config.get('source_language', {})
            if isinstance(source_lang, dict):
                self.source_language_code.data = source_lang.get('code', '')
                self.source_language_name.data = source_lang.get('name', '')
            
            target_langs = config.get('target_languages', [])
            if isinstance(target_langs, list):
                target_codes = []
                for lang in target_langs:
                    if isinstance(lang, dict) and 'code' in lang:
                        target_codes.append(lang['code'])
                    elif isinstance(lang, str):
                        target_codes.append(lang)
                self.available_target_languages.populate_from_codes(target_codes)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert form data to configuration dictionary.
        
        Returns:
            Dictionary with project configuration including full language objects
        """
        # Build source language object
        source_language = {}
        if self.source_language_code.data:
            # Get full language info from comprehensive database
            lang_info = get_language_by_code(self.source_language_code.data)
            if lang_info:
                source_language = {
                    'code': lang_info['code'],
                    'name': self.source_language_name.data or lang_info['name'],
                    'family': lang_info['family'],
                    'region': lang_info['region']
                }
            else:
                # Fallback for unknown codes
                source_language = {
                    'code': self.source_language_code.data,
                    'name': self.source_language_name.data or self.source_language_code.data,
                    'family': 'Unknown',
                    'region': 'Unknown'
                }

        # Build target languages list
        target_languages = []
        selected_codes = self.available_target_languages.get_selected_codes()
        for code in selected_codes:
            lang_info = get_language_by_code(code)
            if lang_info:
                target_languages.append({
                    'code': lang_info['code'],
                    'name': lang_info['name'],
                    'family': lang_info['family'],
                    'region': lang_info['region']
                })

        return {
            'project_name': self.project_name.data or '',
            'source_language': source_language,
            'target_languages': target_languages
        }
        
    def get_language_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about selected languages for display.
        
        Returns:
            Dictionary with language family and region statistics
        """
        all_selected = []
        
        # Add source language
        if self.source_language_code.data:
            source_lang = get_language_by_code(self.source_language_code.data)
            if source_lang:
                all_selected.append(source_lang)
        
        # Add target languages
        target_langs = self.available_target_languages.get_selected_languages()
        all_selected.extend(target_langs)
        
        if not all_selected:
            return {
                'total_languages': 0,
                'families': {},
                'regions': {},
                'coverage': 'No languages selected'
            }
        
        # Count families and regions
        families = {}
        regions = {}
        
        for lang in all_selected:
            family = lang.get('family', 'Unknown')
            region = lang.get('region', 'Unknown')
            
            families[family] = families.get(family, 0) + 1
            regions[region] = regions.get(region, 0) + 1
        
        # Generate coverage description
        family_count = len(families)
        region_count = len(regions)
        
        if family_count == 1 and region_count == 1:
            coverage = f"Focused on {list(families.keys())[0]} languages from {list(regions.keys())[0]}"
        elif family_count <= 3:
            coverage = f"Covers {family_count} language families across {region_count} regions"
        else:
            coverage = f"Diverse multilingual project with {family_count} language families"
        
        return {
            'total_languages': len(all_selected),
            'families': families,
            'regions': regions,
            'coverage': coverage
        }
