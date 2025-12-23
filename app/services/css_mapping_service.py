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
        """Build lookup maps for all ranges (abbreviations).
        
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
            
            def add_to_map(values_list, target_map, use_abbrev: bool = True):
                for val in values_list:
                    val_id = val.get('id')
                    if use_abbrev:
                        abbrev = val.get('abbrev')
                        if val_id and abbrev:
                            if isinstance(abbrev, dict):
                                abbr_text = abbrev.get(lang, abbrev.get('en', val_id))
                            else:
                                abbr_text = abbrev
                            target_map[val_id] = abbr_text
                    else:
                        label = val.get('label') or val.get('id')
                        if isinstance(label, dict):
                            label_text = label.get(lang, label.get('en', val_id))
                        else:
                            label_text = label
                        if val_id and label_text:
                            target_map[val_id] = label_text
                    
                    children = val.get('children', [])
                    if children:
                        add_to_map(children, target_map, use_abbrev)
            
            for range_id, range_data in ranges.items():
                if range_data and range_data.get('values'):
                    abbr_map = {}
                    add_to_map(range_data.get('values', []), abbr_map, use_abbrev=True)
                    range_abbr_maps[range_id] = abbr_map
                        
            return range_abbr_maps
        except Exception as e:
            self._logger.debug(f"Could not build range lookup: {e}")
            return {}

    def _apply_relation_display_aspect(self, elem: ET.Element, aspect: str, range_map: Dict[str, str]) -> None:
        """Apply display aspect to a relation element.
        
        - If aspect == 'label' or 'full', range_map should be id->label mapping.
        - If aspect == 'abbr', range_map should be id->abbrev mapping.
        If a label mapping is requested but missing, fall back to a humanized label
        by capitalizing the type ID (e.g., 'antonym' -> 'Antonym').
        """
        current_type = elem.attrib.get('type', '')
        if not current_type:
            return

        if current_type in range_map:
            elem.attrib['type'] = range_map[current_type]
            return

        # If we requested a label/full and there's no mapping, create a fallback
        if aspect in ('label', 'full'):
            # Humanize type: replace dashes with spaces and title-case each word
            human_label = ' '.join([w.capitalize() for w in current_type.replace('-', ' ').split()])
            elem.attrib['type'] = human_label
            return

        # Otherwise leave it unchanged (abbr or unknown aspect)
        return
    def _apply_grammatical_display_aspect(self, elem: ET.Element, aspect: str, range_map: Dict[str, str]) -> None:
        """Apply display aspect to a grammatical-info element."""
        current_value = elem.attrib.get('value', '')
        if current_value in range_map:
            elem.attrib['value'] = range_map[current_value]

    def _build_range_label_lookup(self, lang: str = 'en') -> Dict[str, Dict[str, str]]:
        """Build lookup maps for ranges using labels instead of abbreviations.

        Returns mapping: range_id -> { value_id -> label }
        """
        try:
            from flask import current_app
            from app.services.dictionary_service import DictionaryService

            dict_service = current_app.injector.get(DictionaryService)
            ranges = dict_service.get_ranges()

            if not ranges:
                return {}

            range_label_maps: Dict[str, Dict[str, str]] = {}

            def add_to_map(values_list, target_map):
                for val in values_list:
                    val_id = val.get('id')
                    label = val.get('label') or val.get('id')
                    if isinstance(label, dict):
                        label_text = label.get(lang, label.get('en', val_id))
                    else:
                        label_text = label
                    if val_id and label_text:
                        target_map[val_id] = label_text

                    children = val.get('children', [])
                    if children:
                        add_to_map(children, target_map)

            for range_id, range_data in ranges.items():
                if range_data and range_data.get('values'):
                    lbl_map: Dict[str, str] = {}
                    add_to_map(range_data.get('values', []), lbl_map)
                    if lbl_map:
                        range_label_maps[range_id] = lbl_map

            return range_label_maps
        except Exception as e:
            self._logger.debug(f"Could not build range label lookup: {e}")
            return {}
    def apply_display_aspects(self, entry_xml: str, profile: DisplayProfile) -> (str, set):
        """Apply display aspects from the profile to the entry XML.

        This inspects the profile elements' display aspects (e.g., 'label', 'abbr')
        and applies appropriate mappings to matching XML nodes. It returns the
        modified XML and a set of element tag names that were handled explicitly
        (so callers can avoid overwriting those with generic abbreviation replacement).
        """
        import xml.etree.ElementTree as ET
        import re

        handled_elements = set()

        # Build mapping tables
        abbr_maps = self._build_range_lookup()
        label_maps = self._build_range_label_lookup()

        # Parse XML (light namespace cleanup)
        clean_xml = re.sub(r'\sxmlns(:[^=]+)?="[^"]+"', '', entry_xml)
        clean_xml = re.sub(r'<([a-z]+):', r'<\1', clean_xml)
        clean_xml = re.sub(r'</([a-z]+):', r'</\1', clean_xml)

        try:
            root = ET.fromstring(clean_xml)
        except Exception:
            # If parsing fails, return original
            return entry_xml, handled_elements

        # Inspect profile elements to determine how to render specific lift elements
        for pe in profile.elements:
            aspect = None
            try:
                aspect = pe.get_display_aspect()
            except Exception:
                aspect = None

            lift_elem = pe.lift_element
            if not lift_elem:
                continue

            # Relation-specific handling
            if lift_elem == 'relation':
                # Choose label map for 'label' or 'full' aspects; abbrev map for 'abbr'
                use_label = aspect in ('label', 'full')
                # Prefer standardized range ids
                rel_map = None
                if use_label:
                    # Prefer standardized lexical-relation mapping only
                    rel_map = label_maps.get('lexical-relation')
                else:
                    rel_map = abbr_maps.get('lexical-relation')

                # Apply relation display aspect for all relation elements. If no mapping exists
                # we'll still call the helper which can fall back to a humanized label when
                # a 'label'/'full' aspect is requested.
                for elem in root.findall('.//relation'):
                    self._apply_relation_display_aspect(elem, aspect or 'abbr', rel_map or {})
                handled_elements.add('relation')

            # Grammatical info handling
            if lift_elem == 'grammatical-info':
                # If the profile asks for 'label' or 'full', use label map; otherwise use abbr
                use_label = aspect in ('label', 'full')
                gram_map = label_maps.get('grammatical-info') if use_label else abbr_maps.get('grammatical-info')
                if gram_map:
                    for elem in root.findall('.//grammatical-info'):
                        self._apply_grammatical_display_aspect(elem, aspect or 'abbr', gram_map)
                    handled_elements.add('grammatical-info')

            # Variant handling
            if lift_elem == 'variant':
                use_label = aspect in ('label', 'full')
                var_map = label_maps.get('variant-type') if use_label else abbr_maps.get('variant-type')
                if var_map:
                    for elem in root.findall('.//variant'):
                        current_type = elem.attrib.get('type', '')
                        if current_type in var_map:
                            elem.attrib['type'] = var_map[current_type]
                    handled_elements.add('variant')

            # Traits are a bit generic; apply if profile requested
            if lift_elem == 'trait':
                # For simplicity, apply abbreviation replacement if no aspect
                use_label = aspect in ('label', 'full')
                for elem in root.findall('.//trait'):
                    trait_name = elem.attrib.get('name', '')
                    value = elem.attrib.get('value', '')
                    if not trait_name or not value:
                        continue
                    # Resolve correct map for this trait name
                    if use_label:
                        val_map = label_maps.get(trait_name) or label_maps.get(f"{trait_name}s") or label_maps.get(trait_name.rstrip('s'))
                    else:
                        val_map = abbr_maps.get(trait_name) or abbr_maps.get(f"{trait_name}s") or abbr_maps.get(trait_name.rstrip('s'))
                    if val_map and value in val_map:
                        elem.attrib['value'] = val_map[value]
                        handled_elements.add('trait')

        # Convert tree back to string and return with handled set
        return ET.tostring(root, encoding='unicode'), handled_elements

    def render_entry(self, entry_xml: str, profile: DisplayProfile, dict_service=None) -> str:
        """Render an entry XML with the given display profile.
        
        Enhanced with debugging for live preview issues.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[CSS Service] Rendering entry, XML length: {len(entry_xml)}")
        logger.info(f"[CSS Service] Profile: {profile.name if profile else 'None'}")
        logger.info(f"[CSS Service] Dict service available: {dict_service is not None}")
        
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
            
            # First apply display aspects indicated by the profile. This returns modified
            # XML plus a set of element tag names handled explicitly by the profile (so we
            # can avoid overwriting them with the generic abbreviation pass).
            entry_xml_with_profile_aspects, handled = self.apply_display_aspects(entry_xml, profile)

            # Now do a general abbreviation replacement for remaining elements we didn't handle
            entry_xml_with_abbr = self._replace_grammatical_info_with_abbr(entry_xml_with_profile_aspects, skip_elements=handled)
            
            # Resolve relation references to show headwords instead of IDs
            entry_xml_with_relations = self._resolve_relation_references(entry_xml_with_abbr, dict_service)
            
            # Extract entry-level PoS if all senses have the same grammatical-info
            # Use the XML with abbreviations so entry-level PoS uses abbr too
            entry_level_pos = self._extract_entry_level_pos(entry_xml_with_relations)
            
            html_content = transformer.transform(entry_xml_with_relations, element_configs, entry_level_pos=entry_level_pos)
            
            logger.info(f"[CSS Service] Transformer output length: {len(html_content) if html_content else 0}")

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
                    css_parts.append(
                        ".lift-entry-rendered { counter-reset: sense-counter; }\n"
                        ".entry-pos { \n"
                        "    font-weight: bold; \n"
                        "    font-style: italic;\n"
                        "    margin-right: 0.5em;\n"
                        "}\n"
                        ".sense::before { \n"
                        "    counter-increment: sense-counter; \n"
                        "    content: counter(sense-counter) \". \"; \n"
                        "    font-weight: bold; \n"
                        "}\n"
                    )
                else:
                    css_parts.append(
                        ".lift-entry-rendered { counter-reset: sense-counter; }\n"
                        ".sense::before { \n"
                        "    counter-increment: sense-counter; \n"
                        "    content: counter(sense-counter) \". \"; \n"
                        "    font-weight: bold; \n"
                        "}\n"
                    )
            
            # Add subentry indentation CSS if enabled (but only if not already in custom CSS)
            if profile.show_subentries and (not profile.custom_css or 'subentry' not in profile.custom_css):
                css_parts.append(
                    ".subentry { \n"
                    "    margin-left: 2em; \n"
                    "    padding-left: 1em; \n"
                    "    border-left: 2px solid #ddd; \n"
                    "}\n"
                )
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
            
    def _replace_grammatical_info_with_abbr(self, entry_xml: str, lang: str = 'en', skip_elements: Optional[set] = None) -> str:
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
            if skip_elements is None:
                skip_elements = set()

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
            if 'grammatical-info' in range_abbr_maps and 'grammatical-info' not in skip_elements:
                for elem in root.findall('.//grammatical-info'):
                    current_value = elem.attrib.get('value', '')
                    if current_value in range_abbr_maps['grammatical-info']:
                        elem.attrib['value'] = range_abbr_maps['grammatical-info'][current_value]
            
            # relation: type attribute (maps to lexical-relation range)
            relation_map = range_abbr_maps.get('lexical-relation')
            if 'relation' not in skip_elements and relation_map:
                for elem in root.findall('.//relation'):
                    current_type = elem.attrib.get('type', '')
                    if current_type in relation_map:
                        elem.attrib['type'] = relation_map[current_type]
            
            # variant: type attribute (maps to variant-type or variant-type range)
            variant_map = range_abbr_maps.get('variant-type') 
            if 'variant' not in skip_elements and variant_map:
                for elem in root.findall('.//variant'):
                    current_type = elem.attrib.get('type', '')
                    if current_type in variant_map:
                        elem.attrib['type'] = variant_map[current_type]
            
            # etymology: type attribute
            if 'etymology' in range_abbr_maps and 'etymology' not in skip_elements:
                for elem in root.findall('.//etymology'):
                    current_type = elem.attrib.get('type', '')
                    if current_type in range_abbr_maps['etymology']:
                        elem.attrib['type'] = range_abbr_maps['etymology'][current_type]
            
            # reversal: type attribute (if reversal-type range exists)
            if 'reversal-type' in range_abbr_maps and 'reversal' not in skip_elements:
                for elem in root.findall('.//reversal'):
                    current_type = elem.attrib.get('type', '')
                    if current_type in range_abbr_maps['reversal-type']:
                        elem.attrib['type'] = range_abbr_maps['reversal-type'][current_type]
            
            # note: type attribute (maps to note-type range)
            note_map = range_abbr_maps.get('note-type') or range_abbr_maps.get('note-type')
            if note_map and 'note' not in skip_elements:
                for elem in root.findall('.//note'):
                    current_type = elem.attrib.get('type', '')
                    if current_type in note_map:
                        elem.attrib['type'] = note_map[current_type]

            # trait: value attribute (maps to range with same name as trait "name")
            # This handles semantic-domain, academic-domain, usage-type etc. if they are traits
            if 'trait' not in skip_elements:
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