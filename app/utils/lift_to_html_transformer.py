from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re

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

    def __post_init__(self):
        if self.children is None:
            self.children = []

class HTMLBuilder:
    """Builds HTML from LIFT XML elements according to display profile."""

    def __init__(self, profile_elements: List[ElementConfig], entry_level_pos: Optional[str] = None):
        self.profile_elements = sorted(profile_elements, key=lambda x: x.display_order)
        self.element_config_map = {config.lift_element: config for config in self.profile_elements}
        self.html_parts = []
        self.current_indent = 0
        self.entry_level_pos = entry_level_pos
        self.pos_displayed = False  # Track if we've already shown the entry-level PoS

    def process_element(self, element: ET.Element, config: ElementConfig) -> str:
        """Process a single LIFT element according to its configuration."""
        if config.visibility == "never":
            return ""

        # Extract text content from the element
        text_content = self._extract_text_content(element)

        # Apply conditional visibility
        if config.visibility == "if-content" and not text_content.strip():
            return ""

        # Build HTML for this element
        tag = 'div' if config.display_mode == 'block' else 'span'
        html = f'<{tag} class="{config.css_class}">'

        if config.prefix:
            html += f'<span class="prefix">{config.prefix}</span>'

        html += text_content

        if config.suffix:
            html += f'<span class="suffix">{config.suffix}</span>'

        tag = 'div' if config.display_mode == 'block' else 'span'
        html += f'</{tag}>'

        return html

    def _extract_text_content(self, element: ET.Element) -> str:
        """Extract text content from a LIFT element, handling nested structures."""
        if element.text and element.text.strip():
            return element.text.strip()

        # Handle nested elements
        content_parts = []
        for child in element:
            child_text = self._extract_text_content(child)
            if child_text:
                content_parts.append(child_text)

        return ' '.join(content_parts) if content_parts else ""

    def build_html(self, root: ET.Element) -> str:
        """Build HTML from the LIFT XML root element using hierarchical processing."""
        html_parts = []
        processed = set()  # Track processed elements to avoid duplicates

        # Process top-level entry structure hierarchically
        html_parts.append(self._process_hierarchical(root, processed))

        if not html_parts or not html_parts[0].strip():
            return "<div class='entry-empty'>No content to display</div>"
        
        return ' '.join(html_parts)

    def _process_hierarchical(self, element: ET.Element, processed: set) -> str:
        """Process an element and its children hierarchically."""
        elem_id = id(element)
        if elem_id in processed:
            return ""
        
        # Check if we have a config for this element
        config = self.element_config_map.get(element.tag)
        
        if not config:
            # No config for this element - process its children with grouping
            child_parts = []
            i = 0
            children_list = list(element)
            
            while i < len(children_list):
                child = children_list[i]
                
                # If this is the entry element and we have entry-level PoS, 
                # display it before the first sense
                if (element.tag == 'entry' and child.tag == 'sense' and 
                    self.entry_level_pos and not self.pos_displayed):
                    self.pos_displayed = True
                    child_parts.append(f'<span class="entry-pos">{self.entry_level_pos}</span>')
                
                # Check if this child should be grouped
                child_config = self.element_config_map.get(child.tag)
                should_group = child_config and child.tag in ('trait', 'field', 'relation')
                
                if should_group:
                    # Collect all consecutive elements of same type
                    same_type_elements = [child]
                    j = i + 1
                    while j < len(children_list) and children_list[j].tag == child.tag:
                        same_type_elements.append(children_list[j])
                        j += 1
                    
                    # Mark all as processed
                    for elem in same_type_elements:
                        processed.add(id(elem))
                    
                    # Extract text content from all elements
                    same_type_texts = []
                    for elem in same_type_elements:
                        # Apply filter check
                        if child_config.filter and not self._check_filter(elem, child_config.filter):
                            continue
                        
                        text = self._extract_text_from_forms(elem)
                        if text:
                            same_type_texts.append(text)
                    
                    # Join with configured separator and wrap once
                    if same_type_texts:
                        joined_text = child_config.separator.join(same_type_texts)
                        tag = 'div' if child_config.display_mode == 'block' else 'span'

                        # For trait elements, add the trait name as a data attribute for identification
                        if child.tag == 'trait' and same_type_elements:
                            # Use the name from the first trait element for the group
                            first_trait_name = same_type_elements[0].attrib.get('name', '')
                            if first_trait_name:
                                html = f'<{tag} class="{child_config.css_class}" data-trait-name="{first_trait_name}">'
                            else:
                                html = f'<{tag} class="{child_config.css_class}">'
                        else:
                            html = f'<{tag} class="{child_config.css_class}">'

                        if child_config.prefix:
                            html += f'<span class="prefix">{child_config.prefix}</span>'
                        html += joined_text
                        if child_config.suffix:
                            html += f'<span class="suffix">{child_config.suffix}</span>'
                        html += f'</{tag}>'
                        child_parts.append(html)
                    
                    # Skip the elements we just processed
                    i = j
                else:
                    # Process single element normally
                    child_html = self._process_hierarchical(child, processed)
                    if child_html:
                        child_parts.append(child_html)
                    i += 1
            
            return ' '.join(child_parts)
        
        # Mark as processed
        processed.add(elem_id)
        
        # Check visibility
        if config.visibility == "never":
            return ""
        
        # Check filter if present
        if config.filter and not self._check_filter(element, config.filter):
            return ""
        
        # Determine if this is a pure structural element (sense, subsense)
        # These elements should NOT extract their own text, only wrap children
        structural_only_elements = {'sense', 'subsense', 'entry'}
        
        # Get text content - most elements should extract their own text
        if element.tag in structural_only_elements:
            # Pure structural element - don't extract text
            text_content = ""
        elif element.tag == 'grammatical-info' and self.entry_level_pos:
            # Skip sense-level grammatical-info if we're showing entry-level PoS
            # But only if this grammatical-info matches the entry-level PoS
            gram_value = element.attrib.get('value', '').strip()
            if gram_value == self.entry_level_pos:
                # This sense has same PoS as entry level, skip it
                return ""
            # Different PoS at sense level - show it (heterogeneous entry)
            text_content = self._extract_text_from_forms(element)
        else:
            # Content or mixed element - extract text from form/text or attributes
            text_content = self._extract_text_from_forms(element)
        
        # Process configured children with grouping for same-type elements
        child_html_parts = []
        i = 0
        children_list = list(element)
        
        while i < len(children_list):
            child = children_list[i]
            
            # If this is the entry element and we have entry-level PoS, 
            # display it before the first sense
            if (element.tag == 'entry' and child.tag == 'sense' and 
                self.entry_level_pos and not self.pos_displayed):
                self.pos_displayed = True
                child_html_parts.append(f'<span class="entry-pos">{self.entry_level_pos}</span>')
            
            # Check if this child has a config and if we should group it
            child_config = self.element_config_map.get(child.tag)
            # Group elements that can appear multiple times: trait, field, relation
            should_group = child_config and child.tag in ('trait', 'field', 'relation')
            
            if should_group:
                # Collect all consecutive elements of same type
                same_type_elements = [child]
                j = i + 1
                while j < len(children_list) and children_list[j].tag == child.tag:
                    same_type_elements.append(children_list[j])
                    j += 1
                
                # Mark all as processed
                for elem in same_type_elements:
                    processed.add(id(elem))
                
                # Extract text content from all elements
                same_type_texts = []
                for elem in same_type_elements:
                    # Apply filter check
                    if child_config.filter and not self._check_filter(elem, child_config.filter):
                        continue
                    
                    text = self._extract_text_from_forms(elem)
                    if text:
                        same_type_texts.append(text)
                
                # Join with configured separator and wrap once
                if same_type_texts:
                    joined_text = child_config.separator.join(same_type_texts)
                    tag = 'div' if child_config.display_mode == 'block' else 'span'

                    # For trait elements, add the trait name as a data attribute for identification
                    if child.tag == 'trait' and same_type_elements:
                        # Use the name from the first trait element for the group
                        first_trait_name = same_type_elements[0].attrib.get('name', '')
                        if first_trait_name:
                            html = f'<{tag} class="{child_config.css_class}" data-trait-name="{first_trait_name}">'
                        else:
                            html = f'<{tag} class="{child_config.css_class}">'
                    else:
                        html = f'<{tag} class="{child_config.css_class}">'

                    if child_config.prefix:
                        html += f'<span class="prefix">{child_config.prefix}</span>'
                    html += joined_text
                    if child_config.suffix:
                        html += f'<span class="suffix">{child_config.suffix}</span>'
                    html += f'</{tag}>'
                    child_html_parts.append(html)
                
                # Skip the elements we just processed
                i = j
            else:
                # Process single element normally
                child_html = self._process_hierarchical(child, processed)
                if child_html:
                    child_html_parts.append(child_html)
                i += 1
        
        # Combine text and child HTML
        combined_content = text_content
        if child_html_parts:
            if text_content:
                combined_content += ' ' + ' '.join(child_html_parts)
            else:
                combined_content = ' '.join(child_html_parts)
        
        # Apply conditional visibility
        if config.visibility == "if-content" and not combined_content.strip():
            return ""
        
        # Build HTML for this element
        tag = 'div' if config.display_mode == 'block' else 'span'
        html = f'<{tag} class="{config.css_class}">'
        
        if config.prefix:
            html += f'<span class="prefix">{config.prefix}</span>'
        
        html += combined_content
        
        if config.suffix:
            html += f'<span class="suffix">{config.suffix}</span>'
        
        html += f'</{tag}>'
        
        return html
    
    def _extract_text_from_forms(self, element: ET.Element) -> str:
        """Extract text from LIFT form/text structure or element attributes.
        
        Args:
            element: Element to extract text from
            
        Returns:
            Extracted text content
        """
        # First, try to extract from form/text structure (most common)
        text_parts = []
        for form in element.findall('./form'):
            # Handle both formats: <form><text>...</text></form> and <form>...</form>
            text_elem = form.find('./text')
            if text_elem and text_elem.text:
                # Format 1: <form><text>...</text></form>
                text_parts.append(text_elem.text.strip())
            elif form.text and form.text.strip():
                # Format 2: <form>...</form> (direct text in form)
                text_parts.append(form.text.strip())
        
        if text_parts:
            return ' '.join(text_parts)
        
        # Handle trait elements specially - show only the resolved value
        if element.tag == 'trait':
            value = element.attrib.get('value', '')
            if value:
                return value
        
        # Handle relation elements specially - show type and headword (or ref if headword not available)
        if element.tag == 'relation':
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
        if element.tag == 'illustration':
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
            for label in element.findall('./label'):
                for form in label.findall('./form'):
                    for text_elem in form.findall('./text'):
                        if text_elem.text and text_elem.text.strip():
                            caption = text_elem.text.strip()
                            break
                    if caption:
                        break
                if caption:
                    break

            # Build image HTML; include caption if available
            img_html = f'<img src="{src}" class="lift-illustration img-thumbnail" style="max-width:300px;max-height:200px;" alt="{caption or "Illustration"}"/>'
            if caption:
                return f'<figure class="illustration-figure">{img_html}<figcaption class="illustration-caption">{caption}</figcaption></figure>'
            return img_html
        
        # Handle field elements - show type in brackets if no content
        if element.tag == 'field' and 'type' in element.attrib:
            # Field content was already checked in form/text above
            # Only show type if no content found
            return f"[{element.attrib['type']}]"
        
        # For elements without form/text, check if content is in attributes
        # Only check 'value' attribute (for grammatical-info, etc.)
        # Do NOT extract from 'type', 'name', etc. as those are metadata, not content
        if 'value' in element.attrib:
            return element.attrib['value']
        
        # Fallback: direct text content
        if element.text and element.text.strip():
            return element.text.strip()
        
        return ""

    def _check_filter(self, element: ET.Element, filter_str: str) -> bool:
        """Check if element matches the filter configuration.
        
        Args:
            element: The XML element to check
            filter_str: The filter string configuration
            
        Returns:
            True if element should be displayed, False otherwise
        """
        if not filter_str:
            return True
            
        if element.tag == 'relation':
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
            
        elif element.tag == 'trait':
            trait_name = element.attrib.get('name', '')
            return trait_name == filter_str
            
        elif element.tag == 'field':
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
        """Transform LIFT XML to HTML using the provided element configurations.
        
        Args:
            lift_xml: LIFT XML string to transform
            element_configs: List of element configurations
            entry_level_pos: Optional entry-level part of speech to display before first sense
            
        Returns:
            HTML string
        """
        try:
            # Parse the XML
            root = self._parse_lift_xml(lift_xml)

            # Create HTML builder with the profile configurations
            html_builder = HTMLBuilder(element_configs, entry_level_pos=entry_level_pos)

            # Build and return the HTML
            return html_builder.build_html(root)

        except Exception as e:
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
        # Remove namespace declarations
        clean_xml = re.sub(r'\sxmlns(:[^=]+)?="[^"]+"', '', xml_string)
        # Remove namespace prefixes
        clean_xml = re.sub(r'<([a-z]+):', r'<\1', clean_xml)
        clean_xml = re.sub(r'</([a-z]+):', r'</\1', clean_xml)
        return clean_xml

    def extract_element_metadata(self, lift_xml: str) -> Dict[str, Any]:
        """Extract metadata about LIFT elements for documentation purposes."""
        try:
            root = self._parse_lift_xml(lift_xml)
            elements = {}

            # Find all unique element types
            for elem in root.iter():
                tag = elem.tag
                if tag not in elements:
                    elements[tag] = {
                        'tag': tag,
                        'attributes': list(elem.attrib.keys()),
                        'children': [],
                        'description': f"LIFT {tag} element"
                    }

                # Track child relationships
                for child in elem:
                    child_tag = child.tag
                    if child_tag not in elements[tag]['children']:
                        elements[tag]['children'].append(child_tag)

            return elements

        except Exception as e:
            return {'error': str(e)}

    def generate_lift_xml_from_form_data(self, form_data: Dict[str, Any]) -> str:
        """
        Generate LIFT XML from form data structure.
        
        This is a simplified version that creates basic LIFT XML structure
        for live preview purposes.
        """
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
                    form_elem.text = str(text)  # Ensure it's a string
            elif lexical_unit_lang:
                # New format: lexical_unit_lang contains the language forms
                lexical_unit_elem = ET.SubElement(entry, 'lexical-unit')
                for lang, text in lexical_unit_lang.items():
                    form_elem = ET.SubElement(lexical_unit_elem, 'form')
                    form_elem.set('lang', lang)
                    form_elem.text = str(text)  # Ensure it's a string
            else:
                # Add a fallback lexical unit if none provided
                lexical_unit_elem = ET.SubElement(entry, 'lexical-unit')
                form_elem = ET.SubElement(lexical_unit_elem, 'form')
                form_elem.set('lang', 'en')
                form_elem.text = 'unknown'
            
            # Add entry-level grammatical info
            grammatical_info = form_data.get('grammatical_info')
            if grammatical_info:
                # Handle dictionary representation
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
            
            # Add pronunciations
            pronunciations = form_data.get('pronunciations', [])
            if pronunciations and isinstance(pronunciations, list):
                for pron_data in pronunciations:
                    if pron_data and isinstance(pron_data, dict):
                        pron_elem = ET.SubElement(entry, 'pronunciation')
                        
                        # Add pronunciation value
                        if pron_data.get('value'):
                            pron_elem.set('value', pron_data.get('value'))
                        
                        # Add pronunciation type
                        if pron_data.get('type'):
                            pron_elem.set('type', pron_data.get('type'))
                        
                        # Add audio reference if available
                        if pron_data.get('audio_path'):
                            audio_elem = ET.SubElement(pron_elem, 'audio')
                            audio_elem.set('href', pron_data.get('audio_path'))
            
            # Add senses
            senses = form_data.get('senses', [])
            if senses and isinstance(senses, list):
                for sense_data in senses:
                    if sense_data and isinstance(sense_data, dict):
                        sense_elem = ET.SubElement(entry, 'sense')
                        
                        # Add sense ID if available
                        sense_id = sense_data.get('id')
                        if sense_id:
                            sense_elem.set('id', sense_id)
                        
                        # Add grammatical info
                        grammatical_info = sense_data.get('grammatical_info')
                        if grammatical_info:
                            # Handle dictionary representation (e.g., {'part_of_speech': 'Noun'})
                            if isinstance(grammatical_info, dict):
                                # Extract the first value if it's a single-key dict
                                if len(grammatical_info) == 1:
                                    grammatical_info = list(grammatical_info.values())[0]
                            gram_elem = ET.SubElement(sense_elem, 'grammatical-info')
                            gram_elem.set('value', str(grammatical_info))
                        
                        # Add definition
                        definition = sense_data.get('definition', {})
                        if definition:
                            for lang, def_data in definition.items():
                                if isinstance(def_data, dict) and def_data.get('text'):
                                    def_elem = ET.SubElement(sense_elem, 'definition')
                                    def_elem.set('lang', lang)
                                    def_elem.text = def_data.get('text')
                        
                        # Add gloss
                        gloss = sense_data.get('gloss', {})
                        if gloss:
                            for lang, gloss_data in gloss.items():
                                if isinstance(gloss_data, dict) and gloss_data.get('text'):
                                    gloss_elem = ET.SubElement(sense_elem, 'gloss')
                                    gloss_elem.set('lang', lang)
                                    gloss_elem.text = gloss_data.get('text')
                        
                        # Add examples
                        examples = sense_data.get('examples', [])
                        if examples and isinstance(examples, list):
                            for example_data in examples:
                                if example_data and isinstance(example_data, dict):
                                    example_elem = ET.SubElement(sense_elem, 'example')
                                    
                                    # Add example text
                                    if example_data.get('text'):
                                        text_elem = ET.SubElement(example_elem, 'text')
                                        text_elem.text = example_data.get('text')
                                    
                                    # Add translation
                                    if example_data.get('translation'):
                                        trans_elem = ET.SubElement(example_elem, 'translation')
                                        trans_elem.set('type', example_data.get('translation_type', 'free'))
                                        trans_elem.text = example_data.get('translation')
                        
                        # Add sense-level traits (usage types, domains, etc.)
                        for trait_field in ['usage_type', 'domain_type', 'semantic_domain']:
                            trait_value = sense_data.get(trait_field)
                            if trait_value:
                                if isinstance(trait_value, list):
                                    for value in trait_value:
                                        trait_elem = ET.SubElement(sense_elem, 'trait')
                                        trait_elem.set('name', trait_field)
                                        # Handle dictionary representation
                                        if isinstance(value, dict):
                                            if len(value) == 1:
                                                value = list(value.values())[0]
                                        trait_elem.set('value', str(value))
                                else:
                                    trait_elem = ET.SubElement(sense_elem, 'trait')
                                    trait_elem.set('name', trait_field)
                                    # Handle dictionary representation
                                    if isinstance(trait_value, dict):
                                        if len(trait_value) == 1:
                                            trait_value = list(trait_value.values())[0]
                                    trait_elem.set('value', str(trait_value))
            
            # Add notes
            notes = form_data.get('notes', {})
            if notes:
                for note_type, note_text in notes.items():
                    if note_text:
                        note_elem = ET.SubElement(entry, 'note')
                        note_elem.set('type', note_type)
                        note_elem.text = note_text
            
            # Add etymology
            etymology = form_data.get('etymology')
            if etymology:
                etym_elem = ET.SubElement(entry, 'etymology')
                etym_elem.text = etymology
            
            # Convert to XML string
            xml_string = ET.tostring(entry, encoding='unicode')
            
            # Add LIFT namespace and schema location
            xml_string = f'<?xml version="1.0" encoding="UTF-8"?>\n<lift xmlns="urn:sil:lift:0.13" version="0.13">\n{xml_string}\n</lift>'
            
            return xml_string
            
        except Exception as e:
            # Return a minimal valid LIFT XML with error message
            return f'<?xml version="1.0" encoding="UTF-8"?>\n<lift xmlns="urn:sil:lift:0.13" version="0.13">\n    <entry id="error-entry">\n        <lexical-unit>\n            <form lang="en">Error generating preview: {str(e)}</form>\n        </lexical-unit>\n    </entry>\n</lift>'