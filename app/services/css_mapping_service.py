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
from xml.etree import ElementTree as ET

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
    def _build_range_lookup(self, lang: str = 'en') -> Dict[str, Dict[str, str]]:
        """Build lookup maps for all ranges.
        
        Args:
            lang: Language code for abbreviations
            
        Returns:
            Dictionary mapping range ID to a map of {value_id: abbreviation}
        """
        try:
            from flask import current_app
            from app.services.dictionary_service import DictionaryService
            
            dict_service = current_app.injector.get(DictionaryService)
            ranges = dict_service.get_ranges()
            
            if not ranges:
                return {}
            
            range_abbr_maps = {}
            
            def add_to_map(values_list, target_map):
                for val in values_list:
                    val_id = val.get('id')
                    abbrev = val.get('abbrev')
                    if val_id and abbrev:
                        if isinstance(abbrev, dict):
                            abbr_text = abbrev.get(lang, abbrev.get('en', val_id))
                        else:
                            abbr_text = abbrev
                        target_map[val_id] = abbr_text
                    
                    children = val.get('children', [])
                    if children:
                        add_to_map(children, target_map)
            
            for range_id, range_data in ranges.items():
                if range_data and range_data.get('values'):
                    abbr_map = {}
                    add_to_map(range_data.get('values', []), abbr_map)
                    if abbr_map:
                        range_abbr_maps[range_id] = abbr_map
                        
            return range_abbr_maps
        except Exception as e:
            self._logger.debug(f"Could not build range lookup: {e}")
            return {}

    def _apply_relation_display_aspect(self, elem: ET.Element, aspect: str, range_map: Dict[str, str]) -> None:
        """Apply display aspect to a relation element."""
        # This is a placeholder for more complex aspect logic
        # Currently we just do the replacement if it matches map
        current_type = elem.attrib.get('type', '')
        if current_type in range_map:
            # If aspect is 'label' we might want full label, but map has abbr?
            # For now, consistent behavior with existing implementation
            elem.attrib['type'] = range_map[current_type]

    def _apply_grammatical_display_aspect(self, elem: ET.Element, aspect: str, range_map: Dict[str, str]) -> None:
        """Apply display aspect to a grammatical-info element."""
        # Placeholder
        current_value = elem.attrib.get('value', '')
        if current_value in range_map:
            elem.attrib['value'] = range_map[current_value]

    def apply_display_aspects(self, entry_xml: str, profile: DisplayProfile) -> str:
        """Apply display aspects to the entry XML.
        
        This method modifies the XML to reflect display configurations like
        'full', 'abbr', or 'label' for various elements.
        
        Args:
            entry_xml: The LIFT entry XML
            profile: DisplayProfile containing configuration
            
        Returns:
            Modified XML
        """
        # For now, we largely rely on _replace_grammatical_info_with_abbr which handles generic range replacement
        # But we can add specific logic here if needed. 
        # Since _replace_grammatical_info_with_abbr is called in render_entry, this might be redundant 
        # unless we move logic here. For safety/compatibility with existing tests, we keep _replace...
        # and just ensure this method exists and does something useful or pass-through.
        
        # If we really want to support 'aspect' we would inspect profile.elements here
        # and match them to XML nodes.
        return self._replace_grammatical_info_with_abbr(entry_xml)

    def render_entry(self, entry_xml: str, profile: DisplayProfile, dict_service=None) -> str:
        """Render an entry XML with the given display profile.

        Args:
            entry_xml: The LIFT entry XML to render
            profile: The display profile to use
            dict_service: Optional DictionaryService instance for relation resolution.
                         If not provided, will try to get from current_app.

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
                    display_mode=display_mode,
                    filter=elem.config.get('filter') if elem.config and isinstance(elem.config, dict) else None,
                    separator=elem.config.get('separator', ', ') if elem.config and isinstance(elem.config, dict) else ', '
                )
                element_configs.append(config)

            # Use transformer to generate HTML
            transformer = LIFTToHTMLTransformer()
            
            # Replace grammatical-info IDs with abbreviations from ranges
            entry_xml_with_abbr = self._replace_grammatical_info_with_abbr(entry_xml)
            
            # Resolve relation references to show headwords instead of IDs
            entry_xml_with_relations = self._resolve_relation_references(entry_xml_with_abbr, dict_service)
            
            # Extract entry-level PoS if all senses have the same grammatical-info
            # Use the XML with abbreviations so entry-level PoS uses abbr too
            entry_level_pos = self._extract_entry_level_pos(entry_xml_with_relations)
            
            html_content = transformer.transform(entry_xml_with_relations, element_configs, entry_level_pos=entry_level_pos)

            # Wrap in profile-specific container with sanitized class name
            profile_class = self._sanitize_class_name(profile.name)
            
            # Build CSS block
            css_parts = []
            
            # Count number of senses in the entry
            sense_count = 0
            try:
                root = ET.fromstring(entry_xml)
                sense_count = len(root.findall('.//sense'))
            except Exception as e:
                self._logger.warning(f"Failed to count senses in entry: {e}")
                sense_count = 0
            
            # Add sense numbering CSS if enabled
            # Simplified logic: number senses if number_senses is True AND there are multiple senses
            should_number_senses = False
            if profile.number_senses and sense_count > 1:
                should_number_senses = True
                self._logger.info(f"Profile '{profile.name}': Numbering ON (sense_count={sense_count})")
            
            if should_number_senses and (not profile.custom_css or 'sense::before' not in profile.custom_css):
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
                          range_abbr_maps.get('lexical-relation'))
            if relation_map:
                for elem in root.findall('.//relation'):
                    current_type = elem.attrib.get('type', '')
                    if current_type in relation_map:
                        elem.attrib['type'] = relation_map[current_type]
            
            # variant: type attribute (maps to variant-type or variant-type range)
            variant_map = range_abbr_maps.get('variant-type') 
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
            note_map = range_abbr_maps.get('note-type') or range_abbr_maps.get('note-type')
            if note_map:
                for elem in root.findall('.//note'):
                    current_type = elem.attrib.get('type', '')
                    if current_type in note_map:
                        elem.attrib['type'] = note_map[current_type]

            # trait: value attribute (maps to range with same name as trait "name")
            # This handles semantic-domain, academic-domain, usage-type etc. if they are traits
            for elem in root.findall('.//trait'):
                trait_name = elem.attrib.get('name', '')
                current_value = elem.attrib.get('value', '')
                
                # Check if we have a range map for this trait name
                if trait_name and current_value:
                    # Try exact match or plural/singular variations
                    range_map = (range_abbr_maps.get(trait_name) or 
                               range_abbr_maps.get(f"{trait_name}s") or
                               range_abbr_maps.get(trait_name.rstrip('s')))
                               
                    if range_map and current_value in range_map:
                        elem.attrib['value'] = range_map[current_value]
            
            # field: type attribute (maps to range with same name as field "type")
            for elem in root.findall('.//field'):
                field_type = elem.attrib.get('type', '')
                
                # Check if we have a range map for this field type
                if field_type:
                    # Try exact match or plural/singular variations
                    range_map = (range_abbr_maps.get(field_type) or 
                               range_abbr_maps.get(f"{field_type}s") or
                               range_abbr_maps.get(field_type.rstrip('s')))
                               
                    # fields usually have content in form/text, but might use traits or other mechanism
                    # If field has a 'value' trait-like attribute (uncommon but possible) OR
                    # we just want to resolve the TYPE logic? 
                    # Actually, fields hold content. Resolution is usually for the content if it's an ID.
                    # But standard fields in LIFT hold text. 
                    # If the USER meant "usage-type" as a range, it is typically a TRAIT.
                    # If it is a field, it might be just text.
                    # We'll assume traits cover the domains/usage-type requirements.
                    pass
            
            # Convert back to string
            return ET.tostring(root, encoding='unicode')
            
        except Exception as e:
            self._logger.debug(f"Could not replace range values with abbreviations: {e}")
            return entry_xml

    def _resolve_relation_references(self, entry_xml: str, dict_service=None) -> str:
        """Resolve relation references to show headwords instead of IDs.
        
        This replaces the 'ref' attribute in relation elements with a special
        'data-headword' attribute that contains the actual headword of the referenced entry.
        
        Args:
            entry_xml: The LIFT entry XML
            dict_service: Optional DictionaryService instance. If not provided, will try to get from current_app.
            
        Returns:
            Modified XML with relation references resolved to headwords
        """
        import xml.etree.ElementTree as ET
        import re
        
        try:
            # Get dictionary service to look up referenced entries
            if dict_service is None:
                from flask import current_app
                from app.services.dictionary_service import DictionaryService
                dict_service = current_app.injector.get(DictionaryService)
            
            # Clean up namespace declarations
            clean_xml = re.sub(r'\sxmlns(:[^=]+)?="[^"]+"', '', entry_xml)
            clean_xml = re.sub(r'<([a-z]+):', r'<\1', clean_xml)
            clean_xml = re.sub(r'</([a-z]+):', r'</\1', clean_xml)
            
            root = ET.fromstring(clean_xml)
            
            # Find all relation elements
            for relation in root.findall('.//relation'):
                ref_id = relation.attrib.get('ref', '')
                if ref_id:
                    try:
                        db_name = dict_service.db_connector.database
                        has_ns = dict_service._detect_namespace_usage()
                        
                        # First try to find it as an entry ID
                        query = dict_service._query_builder.build_entry_by_id_query(
                            ref_id, db_name, has_ns
                        )
                        self._logger.debug(f"Resolving relation ref {ref_id} as entry in database {db_name}")
                        ref_entry_xml = dict_service.db_connector.execute_query(query)
                        
                        headword = None
                        sense_number = None
                        
                        if ref_entry_xml:
                            # Found as entry - extract lexical unit
                            ref_clean_xml = re.sub(r'\sxmlns(:[^=]+)?="[^"]+"', '', ref_entry_xml)
                            ref_clean_xml = re.sub(r'<([a-z]+):', r'<\1', ref_clean_xml)
                            ref_clean_xml = re.sub(r'</([a-z]+):', r'</\1', ref_clean_xml)
                            ref_root = ET.fromstring(ref_clean_xml)
                            
                            lexical_unit = ref_root.find('.//lexical-unit')
                            if lexical_unit is not None:
                                for form in lexical_unit.findall('.//form'):
                                    text_elem = form.find('./text')
                                    if text_elem is not None and text_elem.text:
                                        headword = text_elem.text.strip()
                                        break
                        else:
                            # Not found as entry - try as sense ID
                            self._logger.debug(f"Not found as entry, trying as sense ID: {ref_id}")
                            
                            # Query for sense by ID - search all entries
                            if has_ns:
                                sense_query = f"""
                                declare namespace lift = "http://fieldworks.sil.org/schemas/lift/0.13";
                                for $sense in collection('{db_name}')//lift:sense[@id="{ref_id}"]
                                let $entry := $sense/ancestor::lift:entry
                                return $entry
                                """
                            else:
                                sense_query = f"""
                                for $sense in collection('{db_name}')//sense[@id="{ref_id}"]
                                let $entry := $sense/ancestor::entry
                                return $entry
                                """
                            
                            ref_entry_xml = dict_service.db_connector.execute_query(sense_query)
                            
                            if ref_entry_xml:
                                # Found the entry containing the sense
                                ref_clean_xml = re.sub(r'\sxmlns(:[^=]+)?="[^"]+"', '', ref_entry_xml)
                                ref_clean_xml = re.sub(r'<([a-z]+):', r'<\1', ref_clean_xml)
                                ref_clean_xml = re.sub(r'</([a-z]+):', r'</\1', ref_clean_xml)
                                ref_root = ET.fromstring(ref_clean_xml)
                                
                                # Get headword from lexical unit
                                lexical_unit = ref_root.find('.//lexical-unit')
                                if lexical_unit is not None:
                                    for form in lexical_unit.findall('.//form'):
                                        text_elem = form.find('./text')
                                        if text_elem is not None and text_elem.text:
                                            headword = text_elem.text.strip()
                                            break
                                
                                # Find the sense number (1-based index)
                                all_senses = ref_root.findall('.//sense')
                                for idx, sense in enumerate(all_senses, 1):
                                    if sense.attrib.get('id') == ref_id:
                                        sense_number = idx
                                        break
                        
                        # Store the resolved reference
                        if headword:
                            if sense_number:
                                relation.attrib['data-headword'] = f"{headword} ({sense_number})"
                            else:
                                relation.attrib['data-headword'] = headword
                            self._logger.debug(f"Resolved {ref_id} to: {relation.attrib['data-headword']}")
                                            
                    except Exception as e:
                        # If we can't find the entry, just leave the ref as-is
                        self._logger.debug(f"Could not resolve relation reference {ref_id}: {e}")
                        pass
            
            # Convert back to string
            return ET.tostring(root, encoding='unicode')
            
        except Exception as e:
            self._logger.debug(f"Could not resolve relation references: {e}")
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