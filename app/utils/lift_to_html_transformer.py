from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re
import logging

@dataclass
class ElementConfig:
    """Configuration for how a LIFT element should be rendered."""
    lift_element: str
    display_order: int
    css_class: str
    prefix: str = ""
    suffix: str = ""
    visibility: str = "always"  # "always", "if-content", "never"
    display_mode: str = "inline"  # "inline" or "block"
    filter: Optional[str] = None
    separator: str = ", "  # Separator for multiple occurrences of same element
    children: List[ElementConfig] = None
    abbr_format: Optional[str] = None # "label", "abbr", "full" for traits/fields

    def __post_init__(self):
        if self.children is None:
            self.children = []

class HTMLBuilder:
    """Builds HTML from LIFT XML elements according to display profile."""

    def __init__(self, profile_elements: List[ElementConfig], entry_level_pos: Optional[str] = None):
        self.profile_elements = sorted(profile_elements, key=lambda x: x.display_order)
        # Support multiple configs per tag for filtered elements (traits, fields, relations)
        self.element_config_map: Dict[str, List[ElementConfig]] = {}
        for config in self.profile_elements:
            if config.lift_element not in self.element_config_map:
                self.element_config_map[config.lift_element] = []
            self.element_config_map[config.lift_element].append(config)
            
        self.html_parts = []
        self.current_indent = 0
        self.entry_level_pos = entry_level_pos
        self.pos_displayed = False
        self.logger = logging.getLogger(__name__)

    def _get_local_tag(self, tag: str) -> str:
        """Get the local name of a tag (without namespace)."""
        if "}" in tag:
            return tag.split("}", 1)[1]
        return tag

    def build_html(self, root: ET.Element) -> str:
        """Build HTML from the LIFT XML root element using hierarchical processing."""
        html_parts = []
        processed = set()  # Track processed elements to avoid duplicates

        # Process top-level entry structure hierarchically
        html_parts.append(self._process_hierarchical(root, processed))

        result = ' '.join(html_parts).strip()
        if not result:
            return "<div class='entry-empty'>No content to display</div>"
        
        return result

    def _process_hierarchical(self, element: ET.Element, processed: set) -> str:
        """Process an element and its children hierarchically."""
        elem_id = id(element)
        if elem_id in processed:
            return ""
        
        local_tag = self._get_local_tag(element.tag)
        configs = self.element_config_map.get(local_tag, [])

        # Find the best matching config for this specific element instance
        config = None
        # Try specific filters first
        for c in configs:
            if c.filter and self._check_filter(element, c.filter):
                config = c
                break
        # Fallback to first non-filtered config if no filtered match
        if not config:
            for c in configs:
                if not c.filter:
                    config = c
                    break
        
        # If configs exist for this tag but none match, it means it's filtered out
        if configs and not config:
            return ""

        # Mark as processed
        processed.add(elem_id)

        # Handle visibility
        if config:
            if config.visibility == "never":
                return ""
            if config.filter and not self._check_filter(element, config.filter):
                return ""

        # Determine structural vs content
        structural_only_elements = {'sense', 'subsense', 'entry', 'lift'}
        is_structural = local_tag in structural_only_elements
        
        # Extract text content if appropriate
        text_content = ""
        if not is_structural:
            if local_tag == 'grammatical-info' and self.entry_level_pos:
                # Special case: skip if matches entry-level PoS
                gram_value = element.attrib.get('value', '').strip()
                if gram_value == self.entry_level_pos:
                    return ""
                # Use non-recursive extraction here to avoid duplication with form children
                text_content = self._extract_text_from_forms(element, recursive=False, aspect=config.abbr_format if config else None)
            else:
                # Use non-recursive extraction here to avoid duplication with form children
                text_content = self._extract_text_from_forms(element, recursive=False, aspect=config.abbr_format if config else None)
        
        # Process children (respecting profile order)
        child_html = self._process_children(element, processed, parent_tag=local_tag)
        
        # Combine text and children
        combined_content = text_content
        if child_html:
            if text_content:
                combined_content += ' ' + child_html
            else:
                combined_content = child_html
        
        if config:
            # Check if-content visibility
            if config.visibility == "if-content" and not combined_content.strip():
                return ""
            
            # Wrap in configured tag/class
            tag = 'div' if config.display_mode == 'block' else 'span'
            html = f'<{tag} class="{config.css_class}">'
            if config.prefix:
                html += f'<span class="prefix">{config.prefix}</span>'
            html += combined_content
            if config.suffix:
                html += f'<span class="suffix">{config.suffix}</span>'
            html += f'</{tag}>'
            return html
            
        else:
            # No config (e.g. entry, form), just return content
            return combined_content

    def _process_children(self, element: ET.Element, processed: set, parent_tag: str) -> str:
        """Process children of an element, respecting profile order then XML order."""
        child_parts = []
        children_list = list(element)
        if not children_list:
            return ""

        # Map children by their local tag for quick lookup
        children_by_tag = {}
        for child in children_list:
            tag = self._get_local_tag(child.tag)
            if tag not in children_by_tag:
                children_by_tag[tag] = []
            children_by_tag[tag].append(child)

        # 1. Iterate Profile Elements (Ordered)
        for config in self.profile_elements:
            tag = config.lift_element
            if tag in children_by_tag:
                # Found matching children for this profile element
                matching_children = children_by_tag[tag]
                
                # Check for grouping
                should_group = tag in ('trait', 'field', 'relation')
                
                if should_group:
                    # Collect all candidates for this config
                    group_candidates = []
                    for child in matching_children:
                        if id(child) in processed:
                            continue
                        # Check filter for this specific config
                        if config.filter and not self._check_filter(child, config.filter):
                            continue
                        group_candidates.append(child)
                    
                    if group_candidates:
                        # Extract text/html for grouped elements
                        group_texts = []
                        for child in group_candidates:
                            processed.add(id(child))
                            # For grouped items, we want the recursive text because we won't visit children
                            text = self._extract_text_from_forms(child, recursive=True, aspect=config.abbr_format if hasattr(config, 'abbr_format') else None)
                            if text:
                                group_texts.append(text)
                        
                        if group_texts:
                            joined_text = config.separator.join(group_texts)
                            tag_name = 'div' if config.display_mode == 'block' else 'span'
                            
                            # Trait data attribute logic
                            attr_html = ""
                            if tag == 'trait' and group_candidates:
                                first_name = group_candidates[0].attrib.get('name', '')
                                if first_name:
                                    attr_html = f' data-trait-name="{first_name}"'
                            
                            html = f'<{tag_name} class="{config.css_class}"{attr_html}>'
                            if config.prefix:
                                html += f'<span class="prefix">{config.prefix}</span>'
                            html += joined_text
                            if config.suffix:
                                html += f'<span class="suffix">{config.suffix}</span>'
                            html += f'</{tag_name}>'
                            child_parts.append(html)
                            
                else:
                    # Not grouped - process individually
                    # Inject entry-level PoS before processing senses when applicable
                    if tag == 'sense' and parent_tag == 'entry' and self.entry_level_pos and not self.pos_displayed:
                        self.pos_displayed = True
                        child_parts.append(f'<span class="entry-pos">{self.entry_level_pos}</span>')

                    for child in matching_children:
                        if id(child) in processed:
                            continue
                        
                        # filter check
                        if config.filter and not self._check_filter(child, config.filter):
                            continue
                            
                        # Process recursively
                        # Important: Do NOT mark as processed here; _process_hierarchical does it.
                        child_html = self._process_hierarchical(child, processed)
                        if child_html:
                            child_parts.append(child_html)

        # 2. Entry-level PoS injection (if applicable)
        # 3. Iterate Remaining XML Children (Unconfigured / Unprocessed)
        for child in children_list:
            if id(child) in processed:
                continue
            
            # Special check for Entry PoS if we hit a sense and haven't shown it
            tag = self._get_local_tag(child.tag)
            if parent_tag == 'entry' and tag == 'sense' and self.entry_level_pos and not self.pos_displayed:
                self.pos_displayed = True
                child_parts.append(f'<span class="entry-pos">{self.entry_level_pos}</span>')
            
            res = self._process_hierarchical(child, processed)
            if res:
                child_parts.append(res)
                
        return ' '.join(child_parts)
    
    def _extract_text_from_forms(self, element: ET.Element, recursive: bool = True, aspect: Optional[str] = None) -> str:
        """Extract text from LIFT form/text structure or element attributes.
        
        Args:
            element: LIFT element
            recursive: If True, look at form/text children. If False, only check own attributes/text.
            aspect: Current display aspect (label, abbr, full)
        """
        text_parts = []
        
        # Use local tag awareness for children
        if recursive:
            for child in element:
                child_local = self._get_local_tag(child.tag)
                if child_local == 'form':
                    # Found a form
                    text_found = False
                    for subchild in child:
                        if self._get_local_tag(subchild.tag) == 'text':
                            if subchild.text:
                                text_parts.append(subchild.text.strip())
                                text_found = True
                    if not text_found and child.text:
                        if child.text.strip():
                            text_parts.append(child.text.strip())
        
        if text_parts:
            return ' '.join(text_parts)
        
        local_tag = self._get_local_tag(element.tag)
        
        # Handle trait elements specially - show only the resolved value
        if local_tag == 'trait':
            value = element.attrib.get('value', '')
            if value:
                return value
        
        # Handle relation elements specially - show type and headword (or ref if headword not available)
        if local_tag == 'relation':
            rel_type = element.attrib.get('type', '')
            # Prefer data-headword if available (resolved by CSS service)
            headword = element.attrib.get('data-headword', '')
            ref = element.attrib.get('ref', '')

            if rel_type and headword:
                # Return type and headword - prefix/suffix will be added by config
                return f"{rel_type} {headword}"
            elif rel_type and ref:
                # Fallback to ref if headword not resolved
                return f"{rel_type} {ref}"
            elif headword:
                return headword
            elif ref:
                return ref
            elif rel_type:
                # If only type is available, return just the type
                return rel_type

        # Handle illustration elements - render image tag with optional caption
        if local_tag == 'illustration':
            href = element.attrib.get('href', '').strip()
            if not href:
                return ''

            # Prefer absolute URLs; otherwise assume static file under /static/
            if '://' in href:
                src = href
            else:
                src = '/' + '/'.join(['static', href.lstrip('/')])

            # Try to extract a label/caption (prefer first available)
            caption = ''
            for child in element:
                if self._get_local_tag(child.tag) == 'label':
                    for form in child:
                        if self._get_local_tag(form.tag) == 'form':
                            for text_elem in form:
                                if self._get_local_tag(text_elem.tag) == 'text':
                                    if text_elem.text and text_elem.text.strip():
                                        caption = text_elem.text.strip()
                                        break
                            if caption: break
                    if caption: break

            # Build image HTML; include caption if available
            img_html = f'<img src="{src}" class="lift-illustration img-thumbnail" style="max-width:300px;max-height:200px;" alt="{caption or "Illustration"}"/>'
            if caption:
                return f'<figure class="illustration-figure">{img_html}<figcaption class="illustration-caption">{caption}</figcaption></figure>'
            return img_html
        
        # Handle field elements - show type in brackets if no content
        if local_tag == 'field' and 'type' in element.attrib:
            # Field content was already checked in form/text above
            # Only show type if no content found
            return f"[{element.attrib['type']}]"
        
        # For elements without form/text, check if content is in attributes
        # Only check 'value' attribute (for grammatical-info, etc.)
        if 'value' in element.attrib:
            return element.attrib['value']
        
        # Fallback: direct text content
        if element.text and element.text.strip():
            return element.text.strip()
        
        return ""

    def _check_filter(self, element: ET.Element, filter_str: str) -> bool:
        """Check if element matches the filter configuration."""
        if not filter_str:
            return True
            
        local_tag = self._get_local_tag(element.tag)
        if local_tag == 'relation':
            rel_type = element.attrib.get('type', '')
            filters = [f.strip() for f in filter_str.split(',')]
            
            # Check for exclusions (starting with !)
            exclusions = [f[1:] for f in filters if f.startswith('!')]
            if exclusions and rel_type in exclusions:
                return False
                
            # Check for inclusions (not starting with !)
            inclusions = [f for f in filters if not f.startswith('!')]
            if inclusions and rel_type not in inclusions:
                return False
                
            return True
            
        elif local_tag == 'trait':
            trait_name = element.attrib.get('name', '')
            return trait_name == filter_str
            
        elif local_tag == 'field':
            field_type = element.attrib.get('type', '')
            return field_type == filter_str
            
        return True

class LIFTToHTMLTransformer:
    """Transforms LIFT XML to HTML using display profile configurations."""

    def __init__(self):
        self.namespace_map = {
            'lift': 'urn:sil:lift:0.13',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }

    def transform(self, lift_xml: str, element_configs: List[ElementConfig], entry_level_pos: Optional[str] = None) -> str:
        """Transform LIFT XML to HTML using the provided element configurations."""
        try:
            # Parse the XML
            root = self._parse_lift_xml(lift_xml)

            # Create HTML builder with the profile configurations
            html_builder = HTMLBuilder(element_configs, entry_level_pos=entry_level_pos)

            # Build and return the HTML
            return html_builder.build_html(root)

        except Exception as e:
            logging.getLogger(__name__).error(f"Transformation failed: {e}", exc_info=True)
            return f"<div class='entry-error'>Error rendering entry: {str(e)}</div>"

    def _parse_lift_xml(self, lift_xml: str) -> ET.Element:
        """Parse LIFT XML, handling namespaces."""
        # Remove namespace declarations to simplify parsing
        clean_xml = self._remove_namespaces(lift_xml)

        try:
            return ET.fromstring(clean_xml)
        except ET.ParseError as e:
            # Try parsing with namespaces if cleanup fails
            try:
                return ET.fromstring(lift_xml)
            except ET.ParseError:
                raise ValueError(f"Failed to parse LIFT XML: {str(e)}")

    def _remove_namespaces(self, xml_string: str) -> str:
        """Remove namespace declarations from XML to simplify parsing."""
        from app.utils.namespace_manager import LIFTNamespaceManager
        return LIFTNamespaceManager.normalize_lift_xml(xml_string, target_namespace=None)

    def generate_lift_xml_from_form_data(self, form_data: Dict[str, Any]) -> str:
        """Generate LIFT XML from form data structure."""
        try:
            from xml.etree import ElementTree as ET
            import uuid
            from datetime import datetime
            
            # Create entry element
            entry_id = form_data.get('id', str(uuid.uuid4()))
            entry = ET.Element('entry')
            entry.set('id', entry_id)
            entry.set('dateCreated', datetime.now().isoformat())
            entry.set('dateModified', datetime.now().isoformat())
            
            # Add lexical unit - this is critical for the headword
            lexical_unit = form_data.get('lexical_unit', {})
            lexical_unit_lang = form_data.get('lexical_unit_lang', {})
            
            # Handle both old and new formats
            if lexical_unit:
                lexical_unit_elem = ET.SubElement(entry, 'lexical-unit')
                for lang, text in lexical_unit.items():
                    form_elem = ET.SubElement(lexical_unit_elem, 'form')
                    form_elem.set('lang', lang)
                    text_elem = ET.SubElement(form_elem, 'text')
                    text_elem.text = str(text)
            elif lexical_unit_lang:
                lexical_unit_elem = ET.SubElement(entry, 'lexical-unit')
                for lang, text in lexical_unit_lang.items():
                    form_elem = ET.SubElement(lexical_unit_elem, 'form')
                    form_elem.set('lang', lang)
                    text_elem = ET.SubElement(form_elem, 'text')
                    text_elem.text = str(text)
            else:
                lexical_unit_elem = ET.SubElement(entry, 'lexical-unit')
                form_elem = ET.SubElement(lexical_unit_elem, 'form')
                form_elem.set('lang', 'en')
                text_elem = ET.SubElement(form_elem, 'text')
                text_elem.text = 'unknown'
            
            # Add entry-level grammatical info
            grammatical_info = form_data.get('grammatical_info')
            if grammatical_info:
                if isinstance(grammatical_info, dict):
                    if len(grammatical_info) == 1:
                        grammatical_info = list(grammatical_info.values())[0]
                gram_elem = ET.SubElement(entry, 'grammatical-info')
                gram_elem.set('value', str(grammatical_info))
            
            # Add entry-level traits
            traits = form_data.get('traits', {})
            if traits:
                for trait_name, trait_value in traits.items():
                    if trait_value:
                        trait_elem = ET.SubElement(entry, 'trait')
                        trait_elem.set('name', trait_name)
                        trait_elem.set('value', trait_value)
            
            # Add senses
            senses = form_data.get('senses', [])
            if senses and isinstance(senses, list):
                for sense_data in senses:
                    if sense_data and isinstance(sense_data, dict):
                        sense_elem = ET.SubElement(entry, 'sense')
                        sense_id = sense_data.get('id')
                        if sense_id:
                            sense_elem.set('id', sense_id)
                        
                        grammatical_info = sense_data.get('grammatical_info')
                        if grammatical_info:
                            if isinstance(grammatical_info, dict):
                                if len(grammatical_info) == 1:
                                    grammatical_info = list(grammatical_info.values())[0]
                            gram_elem = ET.SubElement(sense_elem, 'grammatical-info')
                            gram_elem.set('value', str(grammatical_info))
                        
                        definition = sense_data.get('definition', {})
                        if definition:
                            for lang, def_data in definition.items():
                                if isinstance(def_data, dict) and def_data.get('text'):
                                    def_elem = ET.SubElement(sense_elem, 'definition')
                                    form_elem = ET.SubElement(def_elem, 'form')
                                    form_elem.set('lang', lang)
                                    text_elem = ET.SubElement(form_elem, 'text')
                                    text_elem.text = def_data.get('text')
                        
                        gloss = sense_data.get('gloss', {})
                        if gloss:
                            for lang, gloss_data in gloss.items():
                                if isinstance(gloss_data, dict) and gloss_data.get('text'):
                                    gloss_elem = ET.SubElement(sense_elem, 'gloss')
                                    gloss_elem.set('lang', lang)
                                    text_elem = ET.SubElement(gloss_elem, 'text')
                                    text_elem.text = gloss_data.get('text')
            
            # Convert to XML string
            xml_string = ET.tostring(entry, encoding='unicode')
            
            # Add LIFT namespace
            xml_string = f"""<?xml version="1.0" encoding="UTF-8"?>
<lift xmlns="http://fieldworks.sil.org/schemas/lift/0.13" version="0.13">
{xml_string}
</lift>"""
            
            return xml_string
            
        except Exception as e:
            return f"""<?xml version="1.0" encoding="UTF-8"?>
<lift xmlns="http://fieldworks.sil.org/schemas/lift/0.13" version="0.13">
    <entry id="error-entry">
        <lexical-unit>
            <form lang="en"><text>Error generating preview: {str(e)}</text></form>
        </lexical-unit>
    </entry>
</lift>"""