"""
LIFT format parser and generator for dictionary data (DRY/KISS optimized).
"""

import logging
import os
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Set

from app.models.entry import Entry, Etymology, Relation, Variant
from app.models.sense import Sense
from app.models.example import Example
from app.utils.exceptions import ValidationError

class LIFTParser:
    """Parser for LIFT format dictionary files."""
    
    NSMAP = {
        'lift': 'http://fieldworks.sil.org/schemas/lift/0.13',
        'flex': 'http://fieldworks.sil.org/schemas/flex/0.1'
    }
    
    def __init__(self, validate: bool = True):
        self.validate = validate
        self.logger = logging.getLogger(__name__)
        # Cache for common parsing results if needed, but currently not used
        self._cached_parsers = {}  # Placeholder for future caching

    # ==================== COMMON PARSING HELPERS ====================
    
    def _parse_common_fields(self, elem: ET.Element) -> Dict[str, Any]:
        """
        Parse common fields present in entries and senses: traits, notes, custom_fields, annotations.
        
        Returns:
            Dict with 'traits', 'notes', 'custom_fields', 'annotations' keys.
        """
        return {
            'traits': self._parse_traits(elem),
            'notes': self._parse_notes(elem),
            'custom_fields': self._parse_custom_fields(elem),
            'annotations': [self._parse_annotation(a) for a in self._find_elements(elem, './lift:annotation')]
        }

    def parse(self, input_data: str, is_file_path: bool = False) -> List[Entry]:
        """
        Generic parse method that can handle either file paths or XML strings.
        
        Args:
            input_data: Either a file path or XML string
            is_file_path: True if input_data is a file path, False if it's an XML string
            
        Returns:
            List of parsed Entry objects
        """
        if is_file_path:
            return self.parse_file(input_data)
        else:
            return self.parse_string(input_data)

    def parse_lift_content(self, xml_string: str) -> List[Entry]:
        """
        Parse LIFT XML content from a string.
        
        This is an alias for parse_string for backward compatibility.
        
        Args:
            xml_string: LIFT XML content as a string
            
        Returns:
            List of parsed Entry objects
        """
        return self.parse_string(xml_string)

    # ==================== NAMESPACE-AWARE FINDERS ====================
    
    def _find(self, parent: ET.Element, xpath: str, single: bool = False) -> Any:
        """Unified finder with namespace fallback."""
        # Trust the caller's xpath for namespaced search (assumes 'lift:' prefix is used where needed)
        ns_xpath = xpath
        plain_xpath = xpath.replace('lift:', '')
        
        result = parent.find(ns_xpath, self.NSMAP) if single else parent.findall(ns_xpath, self.NSMAP)
        
        failed = result is None if single else not result
        if failed:
            result = parent.find(plain_xpath) if single else parent.findall(plain_xpath)
        return result

    def _find_element(self, parent: ET.Element, xpath: str) -> Optional[ET.Element]:
        return self._find(parent, xpath, single=True)
    
    def _find_elements(self, parent: ET.Element, xpath: str) -> List[ET.Element]:
        return self._find(parent, xpath, single=False)

    # ==================== ATTRIBUTE HELPER ====================
    
    def _get_attr(self, parent: ET.Element, xpath: str, attr: str) -> Optional[str]:
        """Get attribute from element if it exists."""
        elem = self._find_element(parent, xpath)
        if elem is not None:
            return elem.get(attr)
        return None

    # ==================== MULTILINGUAL PARSING ====================
    
    # ==================== MULTILINGUAL PARSING ====================
    
    def _parse_multitext(self, parent: ET.Element, xpath: str, form_tag: str = 'lift:form', flatten: bool = False) -> Dict:
        """Parse multilingual form/text structure.
        Set flatten=True to get Dict[str, str], otherwise Dict[str, Dict[str, str]]."""
        result = {}
        target_path = f'{xpath}/{form_tag}' if xpath != '.' else f'./{form_tag}'
        
        for form in self._find_elements(parent, target_path):
            lang = form.get('lang', 'und')
            text = self._find_element(form, 'lift:text')
            if text is not None:
                if text.text and text.text.strip():
                    if flatten:
                        result[lang] = text.text.strip()
                    else:
                        result[lang] = {'text': text.text.strip()}
        return result

    def _parse_text_content(self, elem: ET.Element) -> Dict:
        """Parse <form><text> or direct text content."""
        if content := self._parse_multitext(elem, '.', flatten=False):
            return content
        if elem.text and elem.text.strip():
            return {'und': elem.text.strip()}
        return {}

    # ==================== ENTRY PARSING ====================
    
    def parse_file(self, file_path: str) -> List[Entry]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"LIFT file not found: {file_path}")
        return self._parse_entries(ET.parse(file_path).getroot())

    def parse_string(self, xml_string: str) -> List[Entry]:
        xml_string = self._normalize_xml(xml_string)
        return self._parse_entries(ET.fromstring(xml_string))

    def _normalize_xml(self, xml: str) -> str:
        """Handle multiple entries without root or extra XML declarations."""
        xml = re.sub(r'<\?xml[^>]*\?>', '', xml).strip()
        # Always wrap in <lift> if not already wrapped as <lift> or <lift:lift>
        if not re.match(r'^<(\w+:)?lift(\s|>)', xml):
            ns_uri = self.NSMAP['lift']
            xml = f'<lift xmlns="{ns_uri}" xmlns:lift="{ns_uri}">{xml}</lift>'
        
        self.logger.debug(f"Normalized XML: {xml[:100]}...")
        return xml

    def _parse_entries(self, root: ET.Element) -> List[Entry]:
        """Parse all entries from root."""
        # Parse header information if present
        header_info = self._parse_header(root)

        entries = []
        for entry_elem in self._find_elements(root, './/lift:entry'):
            try:
                # Pass header_info to each entry if needed
                entry = self._parse_entry(entry_elem)
                # Store header_info in entry if it's not None
                if header_info:
                    entry.header_info = header_info
                if self.validate:
                    entry.validate()
                entries.append(entry)
            except ValidationError as e:
                self.logger.warning(f"Skipping invalid entry {entry_elem.get('id', 'unknown')}: {e}")
                if self.validate:
                    raise
        return entries

    def generate_lift_string(self, entries: List[Entry]) -> str:
        """Generate LIFT XML string from Entry objects."""
        # Ensure namespaces are registered
        for prefix, uri in self.NSMAP.items():
            ET.register_namespace(prefix, uri)
        # Avoid registering lift as default if tests expect explicit lift: prefix
        # ET.register_namespace('', self.NSMAP['lift'])

        root = ET.Element(f"{{{self.NSMAP['lift']}}}lift", {
            'version': '0.13',
            'producer': 'slownik-wielki'
        })

        # Add header information if any entry has header_info
        if entries and hasattr(entries[0], 'header_info') and entries[0].header_info:
            self._add_header_to_root(root, entries[0].header_info)

        for entry in entries:
            attrib = {'id': entry.id} if entry.id else {}
            if entry.date_created:
                attrib['dateCreated'] = entry.date_created
            if entry.date_modified:
                attrib['dateModified'] = entry.date_modified
            if entry.date_deleted:
                attrib['dateDeleted'] = entry.date_deleted
            # Use homograph_number for 'order' attribute if present
            if entry.homograph_number is not None:
                attrib['order'] = str(entry.homograph_number)
            elif entry.order is not None:
                attrib['order'] = str(entry.order)

            entry_elem = ET.SubElement(root, f"{{{self.NSMAP['lift']}}}entry", attrib)
            
            # Lexical unit - follows LIFT standard format with forms inside lexical-unit
            if entry.lexical_unit:
                lu = ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}lexical-unit")
                for lang, text in entry.lexical_unit.items():
                    form = ET.SubElement(lu, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                    text_val = text['text'] if isinstance(text, dict) and 'text' in text else text
                    ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text_val)

            # Entry-level traits
            traits_to_serialize = entry.traits.copy() if hasattr(entry, 'traits') and entry.traits else {}
            
            # Add domain_type to traits if present (for entry-level domain type)
            # domain_type may be a list of values; write one trait element per value.
            if hasattr(entry, 'domain_type') and entry.domain_type:
                # Remove any existing domain-type in traits_to_serialize - we'll serialize explicitly
                traits_to_serialize.pop('domain-type', None)

            if traits_to_serialize:
                for trait_name, trait_value in traits_to_serialize.items():
                    ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}trait", {
                        'name': trait_name,
                        'value': trait_value
                    })

            # Serialize entry-level domain-type(s) explicitly (one trait per value)
            if hasattr(entry, 'domain_type') and entry.domain_type:
                if isinstance(entry.domain_type, list):
                    for dt in entry.domain_type:
                        ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}trait", {
                            'name': 'domain-type',
                            'value': dt
                        })
                else:
                    ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}trait", {
                        'name': 'domain-type',
                        'value': entry.domain_type
                    })
            # Pronunciations (text-based)
            if hasattr(entry, 'pronunciations') and entry.pronunciations:
                for lang, text in entry.pronunciations.items():
                    pron_elem = ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}pronunciation")
                    form = ET.SubElement(pron_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                    ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)

            # Pronunciation media
            if hasattr(entry, 'pronunciation_media') and entry.pronunciation_media:
                for media in entry.pronunciation_media:
                    pron_elem = ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}pronunciation")
                    media_elem = ET.SubElement(pron_elem, f"{{{self.NSMAP['lift']}}}media", {'href': media['href']})
                    
                    # Add label if present
                    if 'label' in media and media['label']:
                        label_elem = ET.SubElement(media_elem, f"{{{self.NSMAP['lift']}}}label")
                        for lang, text in media['label'].items():
                            form = ET.SubElement(label_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                            ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)

            # Entry-level custom fields
            if hasattr(entry, 'custom_fields') and entry.custom_fields:
                for field_type, field_content in entry.custom_fields.items():
                    field_elem = ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}field", {'type': field_type})
                    for lang, text in field_content.items():
                        form = ET.SubElement(field_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                        ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
            # Entry-level custom fields
            if hasattr(entry, 'custom_fields') and entry.custom_fields:
                for field_type, field_content in entry.custom_fields.items():
                    field_elem = ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}field", {'type': field_type})
                    for lang, text in field_content.items():
                        form = ET.SubElement(field_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                        ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
            
            # Annotations
            if hasattr(entry, 'annotations') and entry.annotations:
                for annotation in entry.annotations:
                    annotation_attrib = {
                        'name': annotation.get('name', '')
                    }
                    if 'value' in annotation and annotation['value']:
                        annotation_attrib['value'] = annotation['value']
                    if 'who' in annotation and annotation['who']:
                        annotation_attrib['who'] = annotation['who']
                    if 'when' in annotation and annotation['when']:
                        annotation_attrib['when'] = annotation['when']
                    
                    annotation_elem = ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}annotation", annotation_attrib)
                    
                    # Add content if present
                    if 'content' in annotation and annotation['content']:
                        for lang, text in annotation['content'].items():
                            form = ET.SubElement(annotation_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                            ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
            
            # Senses
            for sense in entry.senses:
                s_attrib = {'id': sense.id} if sense.id else {}
                sense_elem = ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}sense", s_attrib)
                
                if sense.grammatical_info:
                    gram_info = ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}grammatical-info", {'value': sense.grammatical_info})
                    # Add grammatical traits inside grammatical-info
                    if hasattr(sense, 'grammatical_traits') and sense.grammatical_traits:
                        for trait_name, trait_value in sense.grammatical_traits.items():
                            ET.SubElement(gram_info, f"{{{self.NSMAP['lift']}}}trait", {
                                'name': trait_name, 
                                'value': trait_value
                            })
                
                if hasattr(sense, 'definition') and sense.definition:
                    defn = ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}definition")
                    for lang, text in sense.definition.items():
                        form = ET.SubElement(defn, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                        text_val = text['text'] if isinstance(text, dict) else text
                        ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text_val)
                
                if hasattr(sense, 'gloss') and sense.gloss:
                    for lang, text in sense.gloss.items():
                        gloss = ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}gloss", {'lang': lang})
                        text_val = text['text'] if isinstance(text, dict) else text
                        ET.SubElement(gloss, f"{{{self.NSMAP['lift']}}}text").text = str(text_val)
                
                # Add sense-level traits
                if hasattr(sense, 'usage_type') and sense.usage_type:
                    for usage in sense.usage_type:
                        ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}trait", {
                            'name': 'usage-type', 
                            'value': usage
                        })
                
                if hasattr(sense, 'domain_type') and sense.domain_type:
                    # domain_type is a list of values; serialize one trait per value
                    for domain in sense.domain_type:
                        ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}trait", {
                            'name': 'domain-type', 
                            'value': domain
                        })
                
                if hasattr(sense, 'semantic_domains') and sense.semantic_domains:
                    for domain in sense.semantic_domains:
                        ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}trait", {
                            'name': 'semantic-domain-ddp4', 
                            'value': domain
                        })
                
                # Add other sense traits if present
                if hasattr(sense, 'traits') and sense.traits:
                    for trait_name, trait_value in sense.traits.items():
                        ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}trait", {
                            'name': trait_name, 
                            'value': trait_value
                        })
                # Add examples
                # Add specific custom fields first (exemplar, scientific-name, literal-meaning)
                if hasattr(sense, 'exemplar') and sense.exemplar:
                    field_elem = ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}field", {'type': 'exemplar'})
                    for lang, text in sense.exemplar.items():
                        form = ET.SubElement(field_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                        ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
                
                if hasattr(sense, 'scientific_name') and sense.scientific_name:
                    field_elem = ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}field", {'type': 'scientific-name'})
                    for lang, text in sense.scientific_name.items():
                        form = ET.SubElement(field_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                        ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
                
                if hasattr(sense, 'literal_meaning') and sense.literal_meaning:
                    field_elem = ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}field", {'type': 'literal-meaning'})
                    for lang, text in sense.literal_meaning.items():
                        form = ET.SubElement(field_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                        ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
                
                # Add other sense-level custom fields
                if hasattr(sense, 'custom_fields') and sense.custom_fields:
                    for field_type, field_content in sense.custom_fields.items():
                        # Skip specific field types that are handled separately
                        if field_type in ['exemplar', 'scientific-name', 'literal-meaning']:
                            continue
                        field_elem = ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}field", { 'type': field_type})
                        for lang, text in field_content.items():
                            form = ET.SubElement(field_elem, f"{{{self.NSMAP['lift']}}}form", { 'lang': lang})
                            ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
                if hasattr(sense, 'examples') and sense.examples:
                    for example in sense.examples:
                        # Handle both dict and Example object formats
                        if isinstance(example, dict):
                            # Legacy format - simple example
                            example_elem = ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}example")
                            if 'en' in example:
                                form = ET.SubElement(example_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': 'en'})
                                ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(example['en'])
                        elif hasattr(example, 'form') and example.form:
                            # New Example object format with enhancements
                            example_attrib = {}
                            if hasattr(example, 'id') and example.id:
                                example_attrib['id'] = example.id
                            if hasattr(example, 'source') and example.source:
                                example_attrib['source'] = example.source
                            
                            example_elem = ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}example", example_attrib)
                            
                            # Add form
                            for lang, text in example.form.items():
                                form = ET.SubElement(example_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                                ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
                            
                            # Add translations
                            if hasattr(example, 'translations') and example.translations:
                                for lang, text in example.translations.items():
                                    translation = ET.SubElement(example_elem, f"{{{self.NSMAP['lift']}}}translation")
                                    form = ET.SubElement(translation, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                                    ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
                            
                            # Add note if present
                            if hasattr(example, 'note') and example.note:
                                note_field = ET.SubElement(example_elem, f"{{{self.NSMAP['lift']}}}field", {'type': 'note'})
                                for lang, text in example.note.items():
                                    form = ET.SubElement(note_field, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                                    ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
                            
                            # Add custom fields if present
                            if hasattr(example, 'custom_fields') and example.custom_fields:
                                for field_type, field_content in example.custom_fields.items():
                                    field_elem = ET.SubElement(example_elem, f"{{{self.NSMAP['lift']}}}field", {'type': field_type})
                                    for lang, text in field_content.items():
                                        form = ET.SubElement(field_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                                        ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
                
                # Add sense-level annotations
                if hasattr(sense, 'annotations') and sense.annotations:
                    for annotation in sense.annotations:
                        annotation_attrib = {
                            'name': annotation.get('name', '')
                        }
                        if 'value' in annotation and annotation['value']:
                            annotation_attrib['value'] = annotation['value']
                        if 'who' in annotation and annotation['who']:
                            annotation_attrib['who'] = annotation['who']
                        if 'when' in annotation and annotation['when']:
                            annotation_attrib['when'] = annotation['when']
                        
                        annotation_elem = ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}annotation", annotation_attrib)
                        
                        # Add content if present
                        if 'content' in annotation and annotation['content']:
                            for lang, text in annotation['content'].items():
                                form = ET.SubElement(annotation_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                                ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
                
                # Add sense-level relations
                if hasattr(sense, 'relations') and sense.relations:
                    for relation in sense.relations:
                        rel_attrib = {'type': relation.get('type', ''), 'ref': relation.get('ref', '')}
                        if 'order' in relation and relation['order'] is not None:
                            rel_attrib['order'] = str(relation['order'])
                        
                        relation_elem = ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}relation", rel_attrib)
                        
                        # Add traits if present
                        if 'traits' in relation and relation['traits']:
                            for trait_name, trait_value in relation['traits'].items():
                                ET.SubElement(relation_elem, f"{{{self.NSMAP['lift']}}}trait", {
                                    'name': trait_name, 
                                    'value': trait_value
                                })

                # Add illustrations
                if hasattr(sense, 'illustrations') and sense.illustrations:
                    for illustration in sense.illustrations:
                        ill_elem = ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}illustration", {'href': illustration['href']})
                        
                        # Add label if present
                        if 'label' in illustration and illustration['label']:
                            label_elem = ET.SubElement(ill_elem, f"{{{self.NSMAP['lift']}}}label")
                            for lang, text in illustration['label'].items():
                                form = ET.SubElement(label_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                                ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
        
        # Variants
        for variant in entry.variants:
            variant_elem = ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}variant")

            # Add variant form
            if variant.form:
                for lang, text in variant.form.items():
                    form = ET.SubElement(variant_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                    text_val = text['text'] if isinstance(text, dict) else text
                    ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text_val)

            # Add direct traits if present
            if hasattr(variant, 'traits') and variant.traits:
                for trait_name, trait_value in variant.traits.items():
                    ET.SubElement(variant_elem, f"{{{self.NSMAP['lift']}}}trait", {
                        'name': trait_name,
                        'value': trait_value
                    })

            # Add grammatical-info with traits if present
            if hasattr(variant, 'grammatical_info') and variant.grammatical_info:
                gram_info = ET.SubElement(variant_elem, f"{{{self.NSMAP['lift']}}}grammatical-info", {'value': variant.grammatical_info})
                if hasattr(variant, 'grammatical_traits') and variant.grammatical_traits:
                    for trait_name, trait_value in variant.grammatical_traits.items():
                        ET.SubElement(gram_info, f"{{{self.NSMAP['lift']}}}trait", {
                            'name': trait_name,
                            'value': trait_value
                        })

        # Relations
        for relation in entry.relations:
            rel_attrib = {'type': relation.type, 'ref': relation.ref}
            if hasattr(relation, 'order') and relation.order is not None:
                rel_attrib['order'] = str(relation.order)
            
            relation_elem = ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}relation", rel_attrib)
            
            # Add traits if present
            if hasattr(relation, 'traits') and relation.traits:
                for trait_name, trait_value in relation.traits.items():
                    ET.SubElement(relation_elem, f"{{{self.NSMAP['lift']}}}trait", {
                        'name': trait_name, 
                        'value': trait_value
                    })

        # Etymologies
        if hasattr(entry, 'etymologies') and entry.etymologies:
            for etym in entry.etymologies:
                etym_attrib = {}
                if etym.type:
                    etym_attrib['type'] = etym.type
                if etym.source:
                    etym_attrib['source'] = etym.source
                
                etym_elem = ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}etymology", etym_attrib)
                
                # Add form if present
                if etym.form:
                    for lang, text in etym.form.items():
                        form = ET.SubElement(etym_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                        ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
                
                # Add gloss if present
                if etym.gloss:
                    for lang, text in etym.gloss.items():
                        gloss = ET.SubElement(etym_elem, f"{{{self.NSMAP['lift']}}}gloss", {'lang': lang})
                        ET.SubElement(gloss, f"{{{self.NSMAP['lift']}}}text").text = str(text)
                
                # Add comment if present
                if etym.comment:
                    comment_field = ET.SubElement(etym_elem, f"{{{self.NSMAP['lift']}}}field", {'type': 'comment'})
                    for lang, text in etym.comment.items():
                        form = ET.SubElement(comment_field, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                        ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)
                
                # Add custom fields if present
                if etym.custom_fields:
                    for field_type, field_content in etym.custom_fields.items():
                        if field_type != 'comment':  # Skip comment as it's handled separately
                            field_elem = ET.SubElement(etym_elem, f"{{{self.NSMAP['lift']}}}field", {'type': field_type})
                            for lang, text in field_content.items():
                                form = ET.SubElement(field_elem, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                                ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text)

        # Convert to string and pretty print
        xml_str = ET.tostring(root, encoding='utf-8', xml_declaration=True).decode('utf-8')
        try:
            from xml.dom import minidom
            dom = minidom.parseString(xml_str)
            return dom.toprettyxml(indent="  ")
        except Exception:
            return xml_str

    def parse_entry(self, xml_string: str) -> Entry:
        """Backward compatible wrapper for parse_string(...)[0]."""
        entries = self.parse_string(xml_string)
        if not entries:
            raise ValueError("No entries found in XML string")
        return entries[0]

    def parse_entry_element(self, elem: ET.Element) -> Entry:
        """Backward compatible wrapper for _parse_entry."""
        return self._parse_entry(elem)

    def _parse_entry(self, elem: ET.Element) -> Entry:
        """Parse single entry element."""
        order_val = None
        if elem.get('order'):
            try:
                order_val = int(elem.get('order'))
            except ValueError:
                self.logger.warning(f"Invalid order value: {elem.get('order')}")
                
        # Parse traits first to extract morph-type and domain-type
        traits = self._parse_traits(elem) or {}
        morph_type = traits.get('morph-type') if traits else None
        domain_type = traits.get('domain-type') if traits else None
        
        # Parse common fields
        common = self._parse_common_fields(elem)
        
        return Entry(
            id_=elem.get('id') if elem.get('id') is not None else self._generate_id(),
            date_created=elem.get('dateCreated'),
            date_modified=elem.get('dateModified'),
            date_deleted=elem.get('dateDeleted'),
            order=order_val,
            homograph_number=order_val, # LIFT 'order' is often used for homograph numbers
            lexical_unit=self._parse_multitext(elem, './lift:lexical-unit', flatten=True),
            citations=[self._parse_multitext(c, '.', flatten=True) for c in self._find_elements(elem, './lift:citation')],
            pronunciations=self._parse_pronunciations(elem),
            pronunciation_media=self._parse_pronunciation_media(elem),
            variants=[self._parse_variant(v) for v in self._find_elements(elem, './lift:variant')],
            grammatical_info=self._get_attr(elem, './lift:grammatical-info', 'value'),
            morph_type=morph_type,
            domain_type=domain_type,
            traits=traits,
            relations=[self._parse_relation(r) for r in self._find_elements(elem, './lift:relation')],
            etymologies=[self._parse_etymology(e) for e in self._find_elements(elem, './lift:etymology')],
            notes=common['notes'],
            custom_fields=common['custom_fields'],
            senses=[self._parse_sense(s) for s in self._find_elements(elem, './lift:sense')],
            annotations=common['annotations']
        )

    def _parse_pronunciations(self, parent: ET.Element) -> Dict[str, str]:
        """Parse pronunciation elements."""
        result = {}
        for pron in self._find_elements(parent, './lift:pronunciation'):
            # LIFT pronunciation can have multiple forms
            forms = self._parse_multitext(pron, '.', flatten=True)
            result.update(forms)
        return result

    def _parse_pronunciation_media(self, parent: ET.Element) -> List[Dict[str, Any]]:
        """Parse media elements within pronunciation elements."""
        media_list = []
        for pron in self._find_elements(parent, './lift:pronunciation'):
            for media in self._find_elements(pron, './lift:media'):
                media_data = {'href': media.get('href', '')}
                
                # Parse label if present
                label_elem = self._find_element(media, './lift:label')
                if label_elem:
                    label_texts = self._parse_multitext(label_elem, '.', flatten=True)
                    if label_texts:
                        media_data['label'] = label_texts
                
                media_list.append(media_data)
        return media_list

    def _parse_lexical_unit(self, parent: ET.Element) -> Dict[str, str]:
        """Parse lexical unit elements from entry."""
        # Use the multitext parser with the form-based approach (standard LIFT format)
        # Format: <lexical-unit><form lang="en"><text>content</text></form></lexical-unit>
        result = {}

        # First, try the standard LIFT format with forms inside lexical-unit
        for lu_elem in self._find_elements(parent, './lift:lexical-unit'):
            for form_elem in self._find_elements(lu_elem, './lift:form'):
                lang = form_elem.get('lang', 'und')
                text_elem = self._find_element(form_elem, './lift:text')
                if text_elem is not None and text_elem.text and text_elem.text.strip():
                    result[lang] = text_elem.text.strip()

        # If no results from form-based approach, try direct text (fallback)
        if not result:
            for lu_elem in self._find_elements(parent, './lift:lexical-unit'):
                lang = lu_elem.get('lang', 'und')
                # Get text directly from the lexical-unit element
                text_elem = self._find_element(lu_elem, './lift:text')
                if text_elem is not None and text_elem.text and text_elem.text.strip():
                    result[lang] = text_elem.text.strip()

        return result

    def _parse_illustrations(self, parent: ET.Element) -> List[Dict[str, Any]]:
        """Parse illustration elements within sense elements."""
        illustrations_list = []
        for illustration in self._find_elements(parent, './lift:illustration'):
            illustration_data = {'href': illustration.get('href', '')}

            # Parse label if present
            label_elem = self._find_element(illustration, './lift:label')
            if label_elem:
                label_texts = self._parse_multitext(label_elem, '.', flatten=True)
                if label_texts:
                    illustration_data['label'] = label_texts

            illustrations_list.append(illustration_data)
        return illustrations_list

    def _parse_variant(self, elem: ET.Element) -> Variant:
        """Parse variant element."""
        # Parse direct trait elements within the variant element
        direct_traits = {}
        # Use the existing _find_elements method which handles namespace fallback
        for trait_elem in self._find_elements(elem, './lift:trait'):
            trait_name = trait_elem.get('name')
            trait_value = trait_elem.get('value')
            if trait_name and trait_value:
                # Add to variant traits, not just grammatical_traits
                direct_traits[trait_name] = trait_value

        return Variant(
            type=elem.get('type', ''),
            ref=elem.get('ref', ''),
            form=self._parse_multitext(elem, '.', flatten=True),
            grammatical_info=self._get_attr(elem, './lift:grammatical-info', 'value'),
            grammatical_traits=self._parse_traits(self._find_element(elem, './lift:grammatical-info')),
            traits=direct_traits if direct_traits else None
        )

    def _parse_relation(self, elem: ET.Element) -> Relation:
        """Parse relation element."""
        return Relation(
            type=elem.get('type', ''),
            ref=elem.get('ref', ''),
            traits=self._parse_traits(elem)
        )

    def _parse_etymology(self, elem: ET.Element) -> Etymology:
        """Parse etymology element."""
        comment_content = self._parse_multitext(elem, './lift:field[@type="comment"]', flatten=True)
        # Convert empty dict to None for backward compatibility
        comment = comment_content if comment_content else None
        
        return Etymology(
            type=elem.get('type', ''),
            source=elem.get('source', ''),
            form=self._parse_multitext(elem, '.', flatten=True),
            gloss=self._parse_multitext(elem, '.', form_tag='lift:gloss', flatten=True),
            comment=comment,
            custom_fields=self._parse_etymology_custom_fields(elem)
        )

    def _parse_header(self, lift_root: ET.Element) -> Dict[str, Any]:
        """Parse header information from LIFT file."""
        header_elem = self._find_element(lift_root, './lift:header')
        if header_elem is None:
            return {}

        header_data = {}

        # Parse description
        description = {}
        for desc_elem in self._find_elements(header_elem, './lift:description'):
            lang = desc_elem.get('lang')
            # First try to get text from <text> sub-element
            text_elem = self._find_element(desc_elem, './lift:text')
            if text_elem is not None and text_elem.text:
                description[lang] = text_elem.text
            # If no <text> sub-element, try direct text content
            elif desc_elem.text:
                description[lang] = desc_elem.text.strip()
        header_data['description'] = description if description else {}

        # Parse ranges reference (just the href to external range files)
        ranges_elem = self._find_element(header_elem, './lift:ranges')
        if ranges_elem is not None:
            href = ranges_elem.get('href')
            if href:
                header_data['ranges_href'] = href

        # Parse fields
        fields_elem = self._find_element(header_elem, './lift:fields')
        if fields_elem is not None:
            fields = []
            for field_elem in self._find_elements(fields_elem, './lift:field'):
                field_type = field_elem.get('type')
                if field_type:
                    field_data = {'type': field_type}
                    # Parse field description, etc.
                    fields.append(field_data)
            header_data['fields'] = fields

        return header_data

    def _add_header_to_root(self, root: ET.Element, header_info: Dict[str, Any]) -> None:
        """Add header information to the root element."""
        if not header_info:
            return

        # Create header element
        header_elem = ET.SubElement(root, f"{{{self.NSMAP['lift']}}}header")

        # Add description if present
        if 'description' in header_info and header_info['description']:
            for lang, text in header_info['description'].items():
                desc_elem = ET.SubElement(header_elem, f"{{{self.NSMAP['lift']}}}description", {'lang': lang})
                text_elem = ET.SubElement(desc_elem, f"{{{self.NSMAP['lift']}}}text")
                text_elem.text = str(text)

        # Add ranges if present
        if 'ranges_href' in header_info and header_info['ranges_href']:
            ranges_elem = ET.SubElement(header_elem, f"{{{self.NSMAP['lift']}}}ranges", {
                'href': header_info['ranges_href']
            })

        # Add fields if present
        if 'fields' in header_info and header_info['fields']:
            fields_elem = ET.SubElement(header_elem, f"{{{self.NSMAP['lift']}}}fields")
            for field_data in header_info['fields']:
                if 'type' in field_data:
                    field_elem = ET.SubElement(fields_elem, f"{{{self.NSMAP['lift']}}}field", {
                        'type': field_data['type']
                    })

    def _parse_etymology_custom_fields(self, parent: ET.Element) -> Dict[str, Dict]:
        """Parse custom field elements in etymology, excluding 'comment' which is handled separately."""
        fields = {}
        for field in self._find_elements(parent, './lift:field'):
            if field_type := field.get('type'):
                # Skip 'comment' field as it's handled separately
                if field_type == 'comment':
                    continue
                # Use flattened multitext for custom fields
                content = self._parse_multitext(field, '.', flatten=True)
                if content:
                    fields[field_type] = content
        return fields

    def _parse_notes(self, parent: ET.Element) -> Dict[str, Dict]:
        """Parse note elements."""
        notes = {}
        for note in self._find_elements(parent, './lift:note'):
            note_type = note.get('type', 'general')
            content = self._parse_text_content(note)
            # Also support direct text-only note without forms
            if not content and note.text and note.text.strip():
                content = {'und': note.text.strip()}
            if content:
                notes[note_type] = content
        return self._normalize_multilingual_dict(notes)

    def _parse_traits(self, parent: ET.Element) -> Optional[Dict[str, str]]:
        """Parse trait elements."""
        if parent is None:
            return None
        traits = {t.get('name'): t.get('value') for t in self._find_elements(parent, './lift:trait') 
                  if t.get('name') and t.get('value')}
        return traits if traits else None
    def _parse_specific_field(self, parent: ET.Element, field_type: str) -> Optional[Dict[str, str]]:
        """Parse a specific field type (exemplar, scientific-name, literal-meaning)."""
        field_elem = self._find_element(parent, f'.//lift:field[@type="{field_type}"]')
        if field_elem is not None:
            content = self._parse_multitext(field_elem, '.', flatten=True)
            return content if content else None
        return None

    def _parse_custom_fields(self, parent: ET.Element) -> Dict[str, Dict]:
        """Parse field elements."""
        fields = {}
        for field in self._find_elements(parent, './lift:field'):
            if field_type := field.get('type'):
                # Skip specific field types that are handled separately
                if field_type in ['exemplar', 'scientific-name', 'literal-meaning']:
                    continue
                # Use flattened multitext for custom fields
                content = self._parse_multitext(field, '.', flatten=True)
                if content:
                    fields[field_type] = content
        return fields

    def _parse_sense(self, elem: ET.Element) -> Sense:
        """Parse sense element."""
        # Parse specific custom field types
        exemplar_field = self._parse_specific_field(elem, 'exemplar')
        scientific_name_field = self._parse_specific_field(elem, 'scientific-name')
        literal_meaning_field = self._parse_specific_field(elem, 'literal-meaning')
        
        # Parse common fields
        common_fields = self._parse_common_fields(elem)
        
        return Sense(
            id_=elem.get('id'),
            glosses=self._parse_multitext(elem, '.', form_tag='lift:gloss', flatten=True),
            definitions=self._parse_multitext(elem, './lift:definition', flatten=True),
            examples=[self._parse_example(e) for e in self._find_elements(elem, './lift:example')],
            relations=[self._parse_relation_dict(r) for r in self._find_elements(elem, './lift:relation')],
            grammatical_info=self._get_attr(elem, './lift:grammatical-info', 'value'),
            grammatical_traits=self._parse_traits(self._find_element(elem, './lift:grammatical-info')),
            usage_type=[v for t in self._find_elements(elem, './lift:trait[@name="usage-type"]') if (v := t.get("value"))],
            domain_type=self._get_attr(elem, './lift:trait[@name="domain-type"]', 'value'),
            semantic_domains=[v for t in self._find_elements(elem, './lift:trait[@name="semantic-domain-ddp4"]') 
                            if (v := t.get('value'))],
            notes=common_fields['notes'],
            custom_fields=common_fields['custom_fields'],
            illustrations=self._parse_illustrations(elem),
            traits={t.get('name'): t.get('value') for t in self._find_elements(elem, './lift:trait') 
                   if t.get('name') not in {'usage-type', 'domain-type', 'semantic-domain-ddp4'}},
            annotations=common_fields['annotations'],
            subsenses=[self._parse_sense(s) for s in self._find_elements(elem, './lift:subsense')],
            exemplar=exemplar_field,
            scientific_name=scientific_name_field,
            literal_meaning=literal_meaning_field
        )

    def _parse_relation_dict(self, elem: ET.Element) -> Dict:
        """Parse relation into dict for sense/subsense."""
        return {'type': elem.get('type', ''), 'ref': elem.get('ref', '')}

    def _parse_example_custom_fields(self, parent: ET.Element) -> Dict[str, Dict]:
        """Parse custom fields from example element."""
        custom_fields = {}
        for field_elem in self._find_elements(parent, './lift:field'):
            field_type = field_elem.get('type')
            if field_type and field_type != 'note':  # Skip note fields, handled separately
                field_content = self._parse_multitext(field_elem, '.', flatten=True)
                if field_content:
                    custom_fields[field_type] = field_content
        return custom_fields
    
    def _parse_example(self, elem: ET.Element) -> Example:
        """Parse example element."""
        # Parse note with flattening for Day 47-48
        note_content = self._parse_multitext(elem, './lift:field[@type="note"]', flatten=True)
        note = note_content if note_content else None
        
        # Parse custom fields with flattening for Day 47-48
        custom_fields = self._parse_example_custom_fields(elem)
        
        return Example(
            id_=elem.get('id'),
            form=self._parse_multitext(elem, '.', flatten=True),
            translations=self._parse_multitext(elem, './lift:translation', flatten=True),
            source=elem.get('source'),
            note=note,
            custom_fields=custom_fields
        )

    def _parse_annotation(self, elem: ET.Element) -> Dict[str, Any]:
        """Parse annotation element."""
        return {
            'name': elem.get('name'),
            'value': elem.get('value'),
            'who': elem.get('who'),
            'when': elem.get('when'),
            'content': self._parse_multitext(elem, '.', flatten=True)
        }

    @staticmethod
    def _normalize_multilingual_dict(d: dict) -> dict:
        """Ensure all values are {"text": ...} dicts."""
        for k, v in list(d.items()):
            if isinstance(v, dict):
                if set(v.keys()) == {"text"} and isinstance(v["text"], str):
                    continue
                d[k] = LIFTParser._normalize_multilingual_dict(v)
            else:
                d[k] = {"text": v}
        return d

    @staticmethod
    def _generate_id() -> str:
        """Generate unique ID for entry without one."""
        import uuid
        return str(uuid.uuid4())

    # ==================== EXTRACTION HELPERS ====================
    
    def _extract_trait_values(self, xml_string: str, trait_name: str, from_relation: bool = True) -> List[Dict[str, Any]]:
        """Generic trait value extractor."""
        try:
            root = ET.fromstring(xml_string)
            values: Set[str] = set()
            xpath = f".//lift:relation//lift:trait[@name='{trait_name}']" if from_relation else f".//lift:trait[@name='{trait_name}']"
            
            for trait in self._find_elements(root, xpath):
                if value := trait.get('value', '').strip():
                    values.add(value)
            
            return [{'id': v, 'value': v, 'abbrev': v[:3].lower(),
                     'description': {'en': f'{v} {trait_name.replace("-", " ")}'}} 
                    for v in sorted(values)]
        except Exception as e:
            self.logger.error(f"Error extracting {trait_name}: {e}")
            return []

    # Method aliases using lambda
    def extract_variant_types_from_traits(self, xml: str) -> List[Dict[str, Any]]:
        """Extract variant-type values from traits on either relation elements or variant elements.
        Tests expect collecting trait name 'variant-type' on relations and 'type' on variant elements."""
        results = self._extract_trait_values(xml, 'variant-type', from_relation=True)
        try:
            root = ET.fromstring(xml)
            extra: Set[str] = set()
            for var in root.findall('.//lift:variant', self.NSMAP) or root.findall('.//variant'):
                # LIFT variant elements may carry a trait name="type" with values like spelling/dialectal
                for trait in var.findall("lift:trait", self.NSMAP) or var.findall("trait"):
                    if trait.get('name') == 'type' and trait.get('value'):
                        extra.add(trait.get('value').strip())
            for v in sorted(extra):
                if not any(r['id'] == v for r in results):
                    results.append({'id': v, 'value': v, 'abbrev': v[:3].lower(), 'description': {'en': f"{v} variant-type"}})
        except Exception as e:
            self.logger.error(f"Error extracting variant types from variant traits: {e}")
        return results

    extract_complex_form_types_from_traits = lambda self, xml: self._extract_trait_values(xml, 'complex-form-type')
    extract_relation_types = lambda self, xml: self._extract_trait_values(xml, 'type', from_relation=False)

    # ===== Language code extraction helpers expected by tests =====
    def extract_language_codes_from_string(self, xml_string: str) -> List[str]:
        """Extract distinct @lang codes from form/text occurrences in the XML string."""
        try:
            root = ET.fromstring(xml_string)
            langs = set()
            for form in root.findall('.//lift:form', self.NSMAP) or root.findall('.//form'):
                if (lang := form.get('lang')):
                    langs.add(lang)
            return sorted(langs)
        except Exception as e:
            self.logger.error(f"Error extracting language codes: {e}")
            return []

    def extract_language_codes_from_file(self, file_path: str) -> List[str]:
        """Extract distinct @lang codes from a LIFT file on disk.
        If the input contains XML markup, treat it as raw XML content."""
        if '<' in file_path and '>' in file_path:
            return self.extract_language_codes_from_string(file_path)
        with open(file_path, 'r', encoding='utf-8') as f:
            return self.extract_language_codes_from_string(f.read())


class LIFTRangesParser:
    """Parser for LIFT ranges files."""
    
    NSMAP = {'lift': 'http://fieldworks.sil.org/schemas/lift/0.13/ranges'}
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def parse_file(self, file_path: str) -> Dict[str, Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"LIFT ranges file not found: {file_path}")
        return self._parse_ranges(ET.parse(file_path).getroot())

    def parse_string(self, xml_string: str) -> Dict[str, Dict[str, Any]]:
        print(f"DEBUG: LIFTRangesParser.parse_string called with XML length {len(xml_string)}")
        # Handle multiple roots if concatenated
        if not xml_string.strip().startswith('<lift-ranges') and not xml_string.strip().startswith('<?xml'):
             xml_string = f"<root>{xml_string}</root>"
             print("DEBUG: Wrapped in <root> (no lift-ranges header)")
        elif xml_string.strip().count('<lift-ranges') > 1:
             xml_string = f"<root>{xml_string}</root>"
             print("DEBUG: Wrapped in <root> (multiple lift-ranges)")
             
        try:
            res = self._parse_ranges(ET.fromstring(xml_string))
            print(f"DEBUG: _parse_ranges returned {len(res)} results")
            if 'variant-type' in res:
                v_values = res['variant-type'].get('values', [])
                print(f"DEBUG: variant-type values count: {len(v_values)}")
                if len(v_values) == 0:
                     print(f"DEBUG: variant-type is EMPTY in parsed_ranges")
            return res
        except ET.ParseError as e:
            print(f"DEBUG: ParseError in parse_string: {e}")
            try:
                wrapped = f"<root>{xml_string}</root>"
                return self._parse_ranges(ET.fromstring(wrapped))
            except Exception:
                raise e  # Re-raise the original ParseError

    def _parse_ranges(self, root: ET.Element) -> Dict[str, Dict[str, Any]]:
        """Parse all ranges from root."""
        ranges = {}
        for range_elem in self._find_elements(root, './/lift:range'):
            if range_id := range_elem.get('id'):
                ranges[range_id] = self._parse_range(range_elem)
        return ranges

    def _find(self, parent: ET.Element, xpath: str, single: bool = False) -> Any:
        """Namespace-aware finder with fallback to non-namespaced and wildcard-namespace search.

        This handles three cases in order:
        1. Namespaced XPath using `lift:` prefix (normal case when ranges use the expected namespace).
        2. Plain XPath without any namespace (FieldWorks exports often omit namespaces).
        3. Wildcard-namespace XPath (matches elements with any namespace, including default namespace).
        """
        # 1) Try namespaced lookup first
        result = parent.find(xpath, self.NSMAP) if single else parent.findall(xpath, self.NSMAP)

        # 2) Fallback to plain XPath (no namespace prefix)
        if (result is None if single else not result):
            plain_xpath = xpath.replace('lift:', '')
            result = parent.find(plain_xpath) if single else parent.findall(plain_xpath)

        # 3) If still not found, try a wildcard-namespace XPath to match default-namespace elements
        if (result is None if single else not result):
            wildcard_xpath = xpath.replace('lift:', '{*}')
            try:
                result = parent.find(wildcard_xpath) if single else parent.findall(wildcard_xpath)
                if (result is None if single else not result):
                    # Only log missing range-element when it is meaningful — e.g. when searching
                    # directly under a <range> or root <lift-ranges>. Avoid noisy logs when
                    # checking for nested children inside an element that legitimately has none.
                    tag_local = parent.tag.split('}')[-1] if '}' in parent.tag else parent.tag
                    if 'range-element' in xpath and tag_local in ('range', 'lift-ranges'):
                        self.logger.debug(
                            f"MISSING: {xpath} (plain: {plain_xpath}, wildcard: {wildcard_xpath}) in <{parent.tag}>"
                        )
            except Exception:
                # If wildcard lookup raises for some xpath constructs, swallow and leave result empty
                result = None if single else []

        return result

    def _find_element(self, parent: ET.Element, xpath: str) -> Optional[ET.Element]:
        return self._find(parent, xpath, single=True)

    def _find_elements(self, parent: ET.Element, xpath: str) -> List[ET.Element]:
        return self._find(parent, xpath, single=False) or []

    def _parse_range(self, elem: ET.Element) -> Dict[str, Dict[str, Any]]:
        """Parse single range element."""
        range_id = elem.get('id')
        return {
            'id': range_id,
            'guid': elem.get('guid', ''),
            'values': self._parse_range_hierarchy(elem, range_id),
            'labels': self._parse_multitext(elem, './lift:label'),
            'description': self._parse_multitext(elem, './lift:description')
        }

    def _parse_range_hierarchy(self, parent: ET.Element, range_id: str) -> List[Dict[str, Any]]:
        """Parse range hierarchy (parent-based or nested)."""
        all_elements = self._find_elements(parent, './/lift:range-element')
        print(f"DEBUG: _parse_range_hierarchy for {range_id}, total elements found: {len(all_elements)}")
        
        if any(e.get('parent') for e in all_elements):
            print(f"DEBUG: Using parent-based hierarchy for {range_id}")
            return self._parse_parent_based(parent, range_id)
        
        # Check for nested hierarchy (range-element inside range-element)
        direct_elements = self._find_elements(parent, './lift:range-element')
        has_nested = any(self._find_elements(elem, './lift:range-element') for elem in direct_elements)
        
        if has_nested:
            print(f"DEBUG: Using nested hierarchy for {range_id}")
            return self._parse_nested_hierarchy(parent, range_id)
        else:
            print(f"DEBUG: Using direct hierarchy for {range_id}, direct count: {len(direct_elements)}")
            return [self._parse_range_element(e, range_id) for e in direct_elements]

    def _parse_nested_hierarchy(self, parent: ET.Element, range_id: str) -> List[Dict[str, Any]]:
        """Parse nested hierarchy (range-element inside range-element)."""
        def parse_element_with_children(elem: ET.Element) -> Dict[str, Any]:
            """Recursively parse an element and its children."""
            result = self._parse_range_element(elem, range_id)
            children = []
            for child_elem in self._find_elements(elem, './lift:range-element'):
                child_data = parse_element_with_children(child_elem)
                children.append(child_data)
            if children:
                result['children'] = children
            return result
        
        top_level_elements = []
        for elem in self._find_elements(parent, './lift:range-element'):
            element_data = parse_element_with_children(elem)
            top_level_elements.append(element_data)
        return top_level_elements

    def _parse_parent_based(self, parent: ET.Element, range_id: str) -> List[Dict[str, Any]]:
        """Parse parent-attribute based hierarchy."""
        elements = {}
        parent_map = {}
        
        for elem in self._find_elements(parent, './/lift:range-element'):
            elem_id = elem.get('id', '')
            
            data = self._parse_range_element(elem, range_id)
            elements[elem_id] = data
            if parent_id := elem.get('parent'):
                parent_map.setdefault(parent_id, []).append(elem_id)
        
        for pid, children in parent_map.items():
            if pid in elements:
                elements[pid]['children'] = [elements[cid] for cid in children if cid in elements]
        
        return [e for eid, e in elements.items() if not any(eid in kids for kids in parent_map.values())]

    def _parse_range_element(self, elem: ET.Element, range_id: str) -> Dict[str, Any]:
        """Parse single range element."""
        elem_id = elem.get('id', '')
            
        # Parse traits and extract language preference
        traits = {t.get('name'): t.get('value') for t in self._find_elements(elem, './lift:trait') if t.get('name')}
        # Extract language preference from traits if present
        language_preference = traits.get('display-language')

        return {
            'id': elem_id,
            'guid': elem.get('guid', ''),
            'value': elem.get('value', '') or elem_id,
            'parent': elem.get('parent', ''),
            'abbrev': self._parse_abbrev(elem),
            'abbrevs': self._parse_abbrevs(elem),
            'labels': self._parse_multitext(elem, './lift:label'),
            'description': self._parse_multitext(elem, './lift:description'),
            'children': [],
            'traits': traits,
            'language': language_preference,  # Add language preference as a top-level field
            'reverse_labels': self._parse_multitext(elem, "./lift:field[@type='reverse-label']"),
            'reverse_abbrevs': self._parse_multitext(elem, "./lift:field[@type='reverse-abbrev']")
        }



    def _parse_multitext(self, parent: ET.Element, xpath: str) -> Dict[str, str]:
        """Parse multilingual content."""
        result = {}
        for form in self._find_elements(parent, f'{xpath}/lift:form'):
            text_elem = self._find_element(form, './lift:text')
            if text_elem is not None:
                if text_elem.text and text_elem.text.strip():
                    # Use the lang attribute, default to 'und' if not present
                    lang = form.get('lang', 'und')
                    result[lang] = text_elem.text.strip()
        return result

    def _parse_abbrev(self, elem: ET.Element) -> str:
        """Parse abbreviation (direct or nested)."""
        abbrev = self._find_element(elem, './lift:abbrev')
        if abbrev is not None:
            if abbrev.text and abbrev.text.strip():
                return abbrev.text.strip()
            # Get multilingual abbreviations and return the first non-empty one
            abbrevs_dict = self._parse_multitext(abbrev, '.')
            if abbrevs_dict:
                # Prefer English abbreviation if available, otherwise return first available
                if 'en' in abbrevs_dict:
                    return abbrevs_dict['en']
                return next((v for v in abbrevs_dict.values() if v), '')
        return ''

    def _parse_abbrevs(self, elem: ET.Element) -> Dict[str, str]:
        """Parse all abbreviation variants."""
        abbrev = self._find_element(elem, './lift:abbrev')
        if abbrev is not None:
            return self._parse_multitext(abbrev, '.')
        return {}

    def resolve_values_with_inheritance(self, values: List[Dict[str, Any]], prefer_lang: str = 'en') -> List[Dict[str, Any]]:
        """Return a deep-copied values list with *effective* properties applied via inheritance.

        This is non-mutating and computes `effective_label` and `effective_abbrev` for each
        element using the following precedence:
          - element-specific value (prefer `labels[prefer_lang]`)
          - parent's effective value
          - fallback to `value` or `id` (for labels) and a `value[:3]` fallback for abbrev
        """
        import copy
        vals_copy = copy.deepcopy(values)

        def pick_label(labels: Dict[str, str], parent_label: str | None) -> str:
            if not labels and parent_label:
                return parent_label
            if not labels:
                return parent_label or ''
            # prefer language
            if prefer_lang in labels:
                return labels[prefer_lang]
            # otherwise take first
            return next(iter(labels.values()))

        def pick_abbrev(abbrev: str, abbrevs: Dict[str, str], parent_abbrev: str | None, fallback: str) -> str:
            # Prefer explicit abbrev on the element first, then multilingual abbrevs,
            # then parent's effective abbrev, then a simple fallback.
            own = abbrev if abbrev and abbrev.strip() else None
            own_multi = None
            if abbrevs:
                if prefer_lang in abbrevs and abbrevs[prefer_lang].strip():
                    own_multi = abbrevs[prefer_lang]
                else:
                    # take first non-empty
                    for v in abbrevs.values():
                        if v and v.strip():
                            own_multi = v
                            break
            if own:
                return own
            if own_multi:
                return own_multi
            if parent_abbrev:
                return parent_abbrev
            return (fallback[:3] if fallback else '')

        def walk(nodes: List[Dict[str, Any]], parent_label: str | None = None, parent_abbrev: str | None = None) -> None:
            for n in nodes:
                label = pick_label(n.get('labels', {}), parent_label)
                abbrev = pick_abbrev(n.get('abbrev', ''), n.get('abbrevs', {}), parent_abbrev, n.get('value') or n.get('id') or '')
                # Attach effective values
                n['effective_label'] = label or (n.get('value') or n.get('id') or '')
                n['effective_abbrev'] = abbrev
                # Debug: log what we computed for this node
                try:
                    self.logger.debug(
                        f"resolved node {n.get('id')}: raw_abbrev={n.get('abbrev')!r}, raw_abbrevs={n.get('abbrevs')!r}, effective_abbrev={n['effective_abbrev']!r}"
                    )
                except Exception:
                    pass
                # Temporary debug output (pytest -s will show this)
                # Recurse into children
                children = n.get('children') or []
                if children:
                    walk(children, n['effective_label'], n['effective_abbrev'])

        walk(vals_copy, None, None)
        return vals_copy

    # Minimal trait extraction used by DictionaryService.get_trait_values_from_relations tests
    def extract_trait_values_from_relations(self, xml_string: str, trait_name: str) -> List[Dict[str, Any]]:
        try:
            root = ET.fromstring(xml_string)
            values = set()
            for trait in root.findall(f".//trait[@name='{trait_name}']") + root.findall(f".//lift:trait[@name='{trait_name}']", self.NSMAP):
                v = trait.get('value', '').strip()
                if v:
                    values.add(v)
            return [
                {
                    'id': v,
                    'value': v,
                    'abbrev': v[:3].lower(),
                    'description': {'en': f"{v} {trait_name.replace('-', ' ')}"}
                }
                for v in sorted(values)
            ]
        except Exception as e:
            self.logger.error(f"Error extracting {trait_name} values from relations: {e}")
            return []
    