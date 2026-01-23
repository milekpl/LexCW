"""
Field Language Detection Service.

Detects the appropriate language code for entry fields
to enable automatic dictionary selection.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.models.project_settings import ProjectSettings


class FieldLanguageDetector:
    """
    Detects language codes for entry fields.

    Uses field path patterns and project settings to determine
    which dictionary should be used for validation.
    """

    # IPA language code (fixed for IPA fields)
    IPA_LANG_CODE = 'seh-fonipa'

    # Field path mappings to language source
    # 'source' can be:
    #   - 'project_source': Use project's source language
    #   - 'field_keys': Extract from dictionary keys
    #   - 'inherit': Inherit from parent context
    #   - 'fixed': Fixed language code value
    FIELD_MAPPINGS = {
        'lexical_unit': 'project_source',
        'lexical-unit': 'project_source',
        'lexicalUnit': 'project_source',
        'pronunciations': 'fixed:seh-fonipa',
        'pronunciation': 'fixed:seh-fonipa',
        'ipa': 'fixed:seh-fonipa',
        'definitions': 'field_keys',
        'definition': 'field_keys',
        'defs': 'field_keys',
        'glosses': 'field_keys',
        'gloss': 'field_keys',
        'examples': 'inherit',
        'example': 'inherit',
        'notes': 'field_keys',
        'note': 'field_keys',
        'etymologies': 'field_keys',
        'etymology': 'field_keys',
        'variants': 'inherit',
        'variant': 'inherit',
        'relations': 'inherit',
        'relation': 'inherit',
    }

    # Common language code patterns - accepts both underscores and hyphens
    LANG_CODE_PATTERN = re.compile(r'^[a-zA-Z]{2,3}([-_][a-zA-Z0-9]+)*$')

    # Reserved/special language codes
    SPECIAL_CODES = {
        'seh-fonipa': 'IPA (X-SAMPA)',
        'x-ipa': 'IPA (X-SAMPA)',
        'ipa': 'IPA',
    }

    def __init__(self):
        """Initialize detector."""
        pass

    def detect(
        self,
        field_path: str,
        field_value: Any,
        project_settings: Optional[ProjectSettings] = None,
        parent_lang_code: Optional[str] = None
    ) -> str:
        """
        Detect the language code for a field.

        Args:
            field_path: Dot-notation path to the field (e.g., 'senses.0.definition')
            field_value: The field value
            project_settings: Project settings for language lookup
            parent_lang_code: Language code from parent context (for inheritance)

        Returns:
            Language code string (e.g., 'en_US', 'seh-fonipa')
        """
        # Get the base field name (last component of path)
        base_field = self._get_base_field(field_path)

        # Get language source for this field
        source = self._get_language_source(base_field)

        return self._resolve_language(
            source=source,
            field_value=field_value,
            project_settings=project_settings,
            parent_lang_code=parent_lang_code
        )

    def detect_from_dict(
        self,
        entry_data: Dict[str, Any],
        project_settings: Optional[ProjectSettings] = None
    ) -> Dict[str, str]:
        """
        Detect language codes for all relevant fields in entry.

        Args:
            entry_data: Full entry data dictionary
            project_settings: Project settings

        Returns:
            Dict mapping field paths to language codes
        """
        results = {}

        # Process lexical unit
        if 'lexical_unit' in entry_data:
            lang_code = self.detect(
                'lexical_unit',
                entry_data['lexical_unit'],
                project_settings
            )
            results['lexical_unit'] = lang_code

        # Process pronunciations
        if 'pronunciations' in entry_data:
            lang_code = self.detect(
                'pronunciations',
                entry_data['pronunciations'],
                project_settings
            )
            results['pronunciations'] = lang_code

        # Process senses (need to do recursively)
        senses = entry_data.get('senses', [])
        for i, sense in enumerate(senses):
            if isinstance(sense, dict):
                parent_lang = results.get(f'senses.{i-1}.definition') if i > 0 else None

                # Definition
                if 'definition' in sense:
                    lang_code = self.detect(
                        f'senses.{i}.definition',
                        sense['definition'],
                        project_settings,
                        parent_lang
                    )
                    results[f'senses.{i}.definition'] = lang_code

                # Gloss
                if 'gloss' in sense:
                    lang_code = self.detect(
                        f'senses.{i}.gloss',
                        sense['gloss'],
                        project_settings,
                        parent_lang
                    )
                    results[f'senses.{i}.gloss'] = lang_code

                # Examples
                for j, example in enumerate(sense.get('examples', [])):
                    if isinstance(example, dict):
                        lang_code = self.detect(
                            f'senses.{i}.examples.{j}',
                            example.get('form', {}),
                            project_settings,
                            lang_code  # Use definition's lang code
                        )
                        results[f'senses.{i}.examples.{j}'] = lang_code

        # Process notes
        if 'notes' in entry_data:
            lang_code = self.detect(
                'notes',
                entry_data['notes'],
                project_settings
            )
            results['notes'] = lang_code

        return results

    def _get_base_field(self, field_path: str) -> str:
        """Extract the base field name from a path."""
        # Handle dot notation: 'senses.0.definition' -> 'definition'
        # Handle bracket notation: 'senses[0].definition' -> 'definition'
        parts = re.split(r'[.\[\]]', field_path)
        # Filter out empty parts and numeric indices
        parts = [p for p in parts if p and not p.isdigit()]
        return parts[-1] if parts else field_path

    def _get_language_source(self, field_name: str) -> str:
        """Get the language source for a field name."""
        # Normalize field name
        normalized = field_name.lower().replace('-', '_')

        # Direct lookup
        if normalized in self.FIELD_MAPPINGS:
            return self.FIELD_MAPPINGS[normalized]

        # Check for key patterns
        if 'lexical' in normalized or 'headword' in normalized:
            return 'project_source'
        if 'pronunci' in normalized or 'ipa' in normalized:
            return 'fixed:seh-fonipa'
        if 'definition' in normalized or 'defs' in normalized:
            return 'field_keys'
        if 'gloss' in normalized:
            return 'field_keys'

        # Default to field keys
        return 'field_keys'

    def _resolve_language(
        self,
        source: str,
        field_value: Any,
        project_settings: Optional[ProjectSettings] = None,
        parent_lang_code: Optional[str] = None
    ) -> str:
        """Resolve language code from source type."""
        if source.startswith('fixed:'):
            # Fixed language code
            return source.split(':')[1]

        elif source == 'project_source':
            # Use project's source language
            if project_settings:
                source_lang = project_settings.source_language
                if isinstance(source_lang, dict):
                    return source_lang.get('code', 'en')
                elif isinstance(source_lang, str):
                    return source_lang
            return 'en'  # Default

        elif source == 'field_keys':
            # Extract from dictionary keys
            lang_code = self._extract_from_keys(field_value)
            if lang_code:
                return lang_code
            # Fallback to parent or project source
            return parent_lang_code or self._resolve_language(
                'project_source', field_value, project_settings
            )

        elif source == 'inherit':
            # Inherit from parent
            if parent_lang_code:
                return parent_lang_code
            # Fallback
            return self._resolve_language(
                'project_source', field_value, project_settings
            )

        # Default fallback
        return 'en'

    def _extract_from_keys(self, value: Any) -> Optional[str]:
        """Extract language code from dictionary keys."""
        if not isinstance(value, dict):
            return None

        for key in value.keys():
            if self._is_valid_lang_code(key):
                return key

        return None

    def _is_valid_lang_code(self, code: str) -> bool:
        """Check if string is a valid language code."""
        if not code:
            return False

        # Check pattern - allows only one region part (e.g., en_US or en-US, not en-US-US)
        if not self.LANG_CODE_PATTERN.match(code):
            return False

        # Check for multiple region parts (e.g., en-US-US is invalid)
        parts = re.split(r'[-_]', code)
        if len(parts) > 2:
            return False

        # Check length (basic validation)
        if len(code) < 2:
            return False

        return True

    def get_languages_from_entry(self, entry_data: Dict[str, Any]) -> Set[str]:
        """
        Extract all unique language codes from an entry.

        Args:
            entry_data: Entry data dictionary

        Returns:
            Set of language codes found in the entry
        """
        languages = set()

        # Add source language if available
        if 'lexical_unit' in entry_data:
            lu = entry_data['lexical_unit']
            if isinstance(lu, dict):
                for key in lu.keys():
                    if self._is_valid_lang_code(key):
                        languages.add(key)

        # Add languages from nested structures
        def extract_from_nested(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if self._is_valid_lang_code(key):
                        languages.add(key)
                    extract_from_nested(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_from_nested(item)

        extract_from_nested(entry_data)

        return languages

    def normalize_lang_code(self, code: str) -> str:
        """
        Normalize a language code to standard format.

        Args:
            code: Input language code

        Returns:
            Normalized language code
        """
        if not code:
            return 'en'

        # Handle special codes first (before case normalization)
        code_lower = code.lower()
        if code_lower in ('ipa', 'x-ipa', 'x_ipa'):
            return 'seh-fonipa'

        # Convert to lowercase
        code = code_lower

        # Handle common variations
        # 'en-us' -> 'en-US'
        if '-' in code:
            parts = code.split('-')
            code = f"{parts[0]}-{parts[1].upper()}" if len(parts) > 1 else parts[0]

        # 'en_us' -> 'en_US'
        elif '_' in code:
            parts = code.split('_')
            code = f"{parts[0]}_{parts[1].upper()}" if len(parts) > 1 else parts[0]

        return code

    def is_ipa_field(self, field_path: str) -> bool:
        """Check if a field should use IPA dictionary."""
        base_field = self._get_base_field(field_path).lower()
        return 'pronunci' in base_field or base_field in ('ipa', 'x-ipa')


# Singleton instance
field_language_detector = FieldLanguageDetector()


def get_language_detector() -> FieldLanguageDetector:
    """Get the global language detector instance."""
    return field_language_detector
