"""
CSS Mapping Service for display profile management.

This is a placeholder implementation for test compatibility.
The full implementation should be completed as part of the CSS specification plan.
"""

from __future__ import annotations

import json
import uuid
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.models.display_profile import DisplayProfile


class CSSMappingService:
    """Service for managing display profiles and rendering entries with CSS styling."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize the CSS mapping service.

        Args:
            storage_path: Path to store display profiles (for testing)
        """
        self.storage_path = storage_path
        self._profiles: Dict[str, DisplayProfile] = {}
        self._logger = logging.getLogger(__name__)
        if storage_path and storage_path.exists():
            self._load_profiles()

    def create_profile(self, profile_data: Dict[str, Any]) -> DisplayProfile:
        """Create a new display profile.
        
        Args:
            profile_data: Dictionary containing profile configuration
            
        Returns:
            The created DisplayProfile instance
        """
        profile_id = str(uuid.uuid4())
        profile_data_copy = profile_data.copy()
        profile_data_copy["profile_id"] = profile_id
        
        profile = DisplayProfile(**profile_data_copy)
        self._profiles[profile_id] = profile
        self._save_profiles()
        return profile

    def get_profile(self, profile_id: str) -> Optional[DisplayProfile]:
        """Get a display profile by ID.
        
        Args:
            profile_id: The profile ID to retrieve
            
        Returns:
            The DisplayProfile instance or None if not found
        """
        return self._profiles.get(profile_id)

    def list_profiles(self) -> List[DisplayProfile]:
        """List all display profiles.
        
        Returns:
            List of all DisplayProfile instances
        """
        return list(self._profiles.values())

    def update_profile(self, profile_id: str, update_data: Dict[str, Any]) -> Optional[DisplayProfile]:
        """Update an existing display profile.
        
        Args:
            profile_id: The profile ID to update
            update_data: Dictionary containing updates
            
        Returns:
            The updated DisplayProfile instance or None if not found
        """
        if profile_id not in self._profiles:
            return None
            
        profile = self._profiles[profile_id]
        for key, value in update_data.items():
            setattr(profile, key, value)
            
        self._save_profiles()
        return profile

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a display profile.
        
        Args:
            profile_id: The profile ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        if profile_id in self._profiles:
            del self._profiles[profile_id]
            self._save_profiles()
            return True
        return False

    def render_entry(self, entry_xml: str, profile: DisplayProfile) -> str:
        """Render an entry XML with the given display profile.

        Args:
            entry_xml: The LIFT entry XML to render
            profile: The display profile to use

        Returns:
            HTML representation of the entry with embedded custom CSS
        """
        try:
            from app.utils.lift_to_html_transformer import (
                LIFTToHTMLTransformer,
                ElementConfig
            )

            # Convert profile elements to ElementConfig objects
            element_configs = []
            for elem in profile.elements:
                # elem is a ProfileElement SQLAlchemy object, not a dict
                # Get display_mode from config JSON if available, default to inline
                display_mode = "inline"
                if elem.config and isinstance(elem.config, dict):
                    display_mode = elem.config.get('display_mode', 'inline')
                
                config = ElementConfig(
                    lift_element=elem.lift_element,
                    display_order=elem.display_order if elem.display_order is not None else 999,
                    css_class=elem.css_class if elem.css_class else elem.lift_element,
                    prefix=elem.prefix if elem.prefix else "",
                    suffix=elem.suffix if elem.suffix else "",
                    visibility=elem.visibility if elem.visibility else "always",
                    display_mode=display_mode
                )
                element_configs.append(config)

            # Use transformer to generate HTML
            transformer = LIFTToHTMLTransformer()
            
            # Replace grammatical-info IDs with abbreviations from ranges
            entry_xml_with_abbr = self._replace_grammatical_info_with_abbr(entry_xml)
            
            # Extract entry-level PoS if all senses have the same grammatical-info
            # Use the XML with abbreviations so entry-level PoS uses abbr too
            entry_level_pos = self._extract_entry_level_pos(entry_xml_with_abbr)
            
            html_content = transformer.transform(entry_xml_with_abbr, element_configs, entry_level_pos=entry_level_pos)

            # Wrap in profile-specific container with sanitized class name
            profile_class = self._sanitize_class_name(profile.name)
            
            # Build CSS block
            css_parts = []
            
            # Add sense numbering CSS if enabled (but only if not already in custom CSS)
            if profile.number_senses and (not profile.custom_css or 'sense::before' not in profile.custom_css):
                # If we have entry-level PoS, adjust sense numbering to account for it
                if entry_level_pos:
                    css_parts.append("""
                        .lift-entry-rendered { counter-reset: sense-counter; }
                        .entry-pos { 
                            font-weight: bold; 
                            font-style: italic;
                            margin-right: 0.5em;
                        }
                        .sense::before { 
                            counter-increment: sense-counter; 
                            content: counter(sense-counter) ". "; 
                            font-weight: bold; 
                        }
                    """)
                else:
                    css_parts.append("""
                        .lift-entry-rendered { counter-reset: sense-counter; }
                        .sense::before { 
                            counter-increment: sense-counter; 
                            content: counter(sense-counter) ". "; 
                            font-weight: bold; 
                        }
                    """)
            
            # Add subentry indentation CSS if enabled (but only if not already in custom CSS)
            if profile.show_subentries and (not profile.custom_css or 'subentry' not in profile.custom_css):
                css_parts.append("""
                    .subentry { 
                        margin-left: 2em; 
                        padding-left: 1em; 
                        border-left: 2px solid #ddd; 
                    }
                """)
            
            # Add custom CSS if provided
            if profile.custom_css:
                css_parts.append(profile.custom_css)
            
            css_block = ""
            if css_parts:
                css_block = f'<style>{"".join(css_parts)}</style>\n'
            
            return f'{css_block}<div class="lift-entry-rendered profile-{profile_class}">{html_content}</div>'

        except Exception as e:
            self._logger.error(f"Failed to render entry: {str(e)}", exc_info=True)
            return f'<div class="entry-render-error">Error rendering entry: {str(e)}</div>'

    def _extract_entry_level_pos(self, entry_xml: str) -> Optional[str]:
        """Extract entry-level part-of-speech if all senses have the same PoS.
        
        Args:
            entry_xml: The LIFT entry XML
            
        Returns:
            Part of speech string if all senses match, None otherwise
        """
        import xml.etree.ElementTree as ET
        import re
        
        try:
            # Clean up namespace declarations
            clean_xml = re.sub(r'\sxmlns(:[^=]+)?="[^"]+"', '', entry_xml)
            clean_xml = re.sub(r'<([a-z]+):', r'<\1', clean_xml)
            clean_xml = re.sub(r'</([a-z]+):', r'</\1', clean_xml)
            
            root = ET.fromstring(clean_xml)
            
            # Find all grammatical-info elements in senses
            pos_values = set()
            for sense in root.findall('.//sense'):
                gram_info = sense.find('./grammatical-info')
                if gram_info is not None and 'value' in gram_info.attrib:
                    pos_value = gram_info.attrib['value'].strip()
                    if pos_value:
                        pos_values.add(pos_value)
            
            # Only return PoS if all senses have the same one
            if len(pos_values) == 1:
                return next(iter(pos_values))
            
            return None
            
        except Exception as e:
            self._logger.debug(f"Could not extract entry-level PoS: {e}")
            return None
            
    def _replace_grammatical_info_with_abbr(self, entry_xml: str, lang: str = 'en') -> str:
        """Replace range element values with abbreviations from ranges.
        
        This replaces values in elements like grammatical-info, relation type attributes,
        variant type attributes, etc. with their abbreviations from the ranges configuration.
        
        Args:
            entry_xml: The LIFT entry XML
            lang: Language code for abbreviation (default: 'en')
            
        Returns:
            Modified XML with abbreviations replacing IDs
        """
        import xml.etree.ElementTree as ET
        import re
        
        try:
            # Get ranges from dictionary service
            from flask import current_app
            from app.services.dictionary_service import DictionaryService
            
            dict_service = current_app.injector.get(DictionaryService)
            ranges = dict_service.get_ranges()
            
            if not ranges:
                return entry_xml
            
            # Build lookup maps for all ranges: range_id -> {value_id -> abbreviation}
            range_abbr_maps = {}
            
            def add_to_map(values_list, target_map):
                """Recursively add values and their children to the lookup map."""
                for val in values_list:
                    val_id = val.get('id')
                    abbrev = val.get('abbrev')
                    if val_id and abbrev:
                        # Abbrev can be a string or dict with language keys
                        if isinstance(abbrev, dict):
                            abbr_text = abbrev.get(lang, abbrev.get('en', val_id))
                        else:
                            abbr_text = abbrev
                        target_map[val_id] = abbr_text
                    
                    # Recursively process children
                    children = val.get('children', [])
                    if children:
                        add_to_map(children, target_map)
            
            # Build maps for all ranges
            for range_id, range_data in ranges.items():
                if range_data and range_data.get('values'):
                    abbr_map = {}
                    add_to_map(range_data.get('values', []), abbr_map)
                    if abbr_map:
                        range_abbr_maps[range_id] = abbr_map
            
            if not range_abbr_maps:
                return entry_xml
            
            # Clean up namespace declarations
            clean_xml = re.sub(r'\sxmlns(:[^=]+)?="[^"]+"', '', entry_xml)
            clean_xml = re.sub(r'<([a-z]+):', r'<\1', clean_xml)
            clean_xml = re.sub(r'</([a-z]+):', r'</\1', clean_xml)
            
            root = ET.fromstring(clean_xml)
            
            # Replace values in range-based elements
            # grammatical-info: value attribute
            if 'grammatical-info' in range_abbr_maps:
                for elem in root.findall('.//grammatical-info'):
                    current_value = elem.attrib.get('value', '')
                    if current_value in range_abbr_maps['grammatical-info']:
                        elem.attrib['value'] = range_abbr_maps['grammatical-info'][current_value]
            
            # relation: type attribute (maps to lexical-relation or relation-type range)
            relation_map = (range_abbr_maps.get('lexical-relation') or 
                          range_abbr_maps.get('relation-type') or 
                          range_abbr_maps.get('relation-types'))
            if relation_map:
                for elem in root.findall('.//relation'):
                    current_type = elem.attrib.get('type', '')
                    if current_type in relation_map:
                        elem.attrib['type'] = relation_map[current_type]
            
            # variant: type attribute (maps to variant-type or variant-types range)
            variant_map = (range_abbr_maps.get('variant-type') or 
                         range_abbr_maps.get('variant-types'))
            if variant_map:
                for elem in root.findall('.//variant'):
                    current_type = elem.attrib.get('type', '')
                    if current_type in variant_map:
                        elem.attrib['type'] = variant_map[current_type]
            
            # etymology: type attribute
            if 'etymology' in range_abbr_maps:
                for elem in root.findall('.//etymology'):
                    current_type = elem.attrib.get('type', '')
                    if current_type in range_abbr_maps['etymology']:
                        elem.attrib['type'] = range_abbr_maps['etymology'][current_type]
            
            # reversal: type attribute (if reversal-type range exists)
            if 'reversal-type' in range_abbr_maps:
                for elem in root.findall('.//reversal'):
                    current_type = elem.attrib.get('type', '')
                    if current_type in range_abbr_maps['reversal-type']:
                        elem.attrib['type'] = range_abbr_maps['reversal-type'][current_type]
            
            # note: type attribute (maps to note-type range)
            note_map = range_abbr_maps.get('note-type') or range_abbr_maps.get('note-types')
            if note_map:
                for elem in root.findall('.//note'):
                    current_type = elem.attrib.get('type', '')
                    if current_type in note_map:
                        elem.attrib['type'] = note_map[current_type]
            
            # Convert back to string
            return ET.tostring(root, encoding='unicode')
            
        except Exception as e:
            self._logger.debug(f"Could not replace range values with abbreviations: {e}")
            return entry_xml

    def _sanitize_class_name(self, name: str) -> str:
        """Sanitize a string for use as a CSS class name.

        Args:
            name: String to sanitize

        Returns:
            Safe CSS class name
        """
        import re
        # Replace spaces and special chars with hyphens
        safe_name = re.sub(r'[^\w-]', '-', name.lower())
        # Remove consecutive hyphens
        safe_name = re.sub(r'-+', '-', safe_name)
        # Remove leading/trailing hyphens
        return safe_name.strip('-')

    def _load_profiles(self) -> None:
        """Load profiles from storage file."""
        if not self.storage_path or not self.storage_path.exists():
            return
            
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for profile_data in data:
                    profile = DisplayProfile(**profile_data)
                    if profile.profile_id:
                        self._profiles[profile.profile_id] = profile
        except (json.JSONDecodeError, KeyError):
            # If the file is corrupted, start with empty profiles
            pass

    def _save_profiles(self) -> None:
        """Save profiles to storage file."""
        if not self.storage_path:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.storage_path, "w", encoding="utf-8") as f:
            data = [profile.dict() for profile in self._profiles.values()]
            json.dump(data, f, indent=2)