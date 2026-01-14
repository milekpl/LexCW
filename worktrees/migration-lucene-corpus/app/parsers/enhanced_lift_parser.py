"""
Enhanced LIFT parser with improved namespace handling.

This module provides an enhanced version of the LIFT parser that uses
the new namespace management utilities for consistent XML handling.
"""

import logging
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from xml.dom import minidom

from app.models import Entry, Sense, Example
from app.utils.exceptions import ValidationError
from app.utils.namespace_manager import LIFTNamespaceManager, XPathBuilder
from app.utils.xquery_builder import XQueryBuilder

logger = logging.getLogger(__name__)


class EnhancedLiftParser:
    """
    Enhanced LIFT parser with proper namespace handling.
    
    This parser automatically detects namespace usage and handles both
    namespaced and non-namespaced LIFT files consistently.
    """
    
    def __init__(self, validate: bool = True, normalize_namespaces: bool = True):
        """
        Initialize enhanced LIFT parser.
        
        Args:
            validate: Whether to validate entries during parsing
            normalize_namespaces: Whether to normalize namespaces for consistency
        """
        self.validate = validate
        self.normalize_namespaces = normalize_namespaces
        self.logger = logging.getLogger(__name__)
        
        # Namespace state for current document
        self._has_lift_namespace = False
        self._namespace_map = {}
    
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
    
    def parse_file(self, file_path: str) -> List[Entry]:
        """
        Parse a LIFT file into a list of Entry objects.
        
        Args:
            file_path: Path to the LIFT file
            
        Returns:
            List of Entry objects
            
        Raises:
            FileNotFoundError: If the file does not exist
            ValidationError: If validation is enabled and an entry fails validation
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"LIFT file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            return self.parse_string(xml_content)
            
        except Exception as e:
            self.logger.error("Error parsing LIFT file %s: %s", file_path, str(e))
            raise
    
    def parse_string(self, xml_content: str) -> List[Entry]:
        """
        Parse LIFT XML string into a list of Entry objects.
        
        Args:
            xml_content: LIFT XML string
            
        Returns:
            List of Entry objects
            
        Raises:
            ValidationError: If validation is enabled and an entry fails validation
        """
        try:
            # Detect namespace usage
            self._has_lift_namespace, self._namespace_map = LIFTNamespaceManager.get_namespace_info(xml_content)
            
            # Normalize namespaces if requested
            if self.normalize_namespaces:
                if self._has_lift_namespace:
                    # Keep namespace but ensure it's properly declared
                    xml_content = LIFTNamespaceManager.normalize_lift_xml(
                        xml_content, LIFTNamespaceManager.LIFT_NAMESPACE
                    )
                else:
                    # Add namespace for consistency
                    xml_content = LIFTNamespaceManager.normalize_lift_xml(
                        xml_content, LIFTNamespaceManager.LIFT_NAMESPACE
                    )
                    self._has_lift_namespace = True
            
            # Register namespaces for ElementTree
            LIFTNamespaceManager.register_namespaces(self._has_lift_namespace)
            
            # Parse XML
            root = ET.fromstring(xml_content)
            
            # Find all entry elements using appropriate namespace handling
            # Note: ElementTree.findall doesn't support absolute XPath, so we use relative path
            if self._has_lift_namespace:
                entry_elements = root.findall('.//lift:entry', LIFTNamespaceManager.NAMESPACE_MAP)
            else:
                entry_elements = root.findall('.//entry')
            
            entries = []
            for entry_elem in entry_elements:
                try:
                    entry = self._parse_entry(entry_elem)
                    if self.validate:
                        entry.validate()
                    entries.append(entry)
                except ValidationError as e:
                    self.logger.warning("Skipping invalid entry: %s", str(e))
                    if self.validate:
                        raise
                except Exception as e:
                    self.logger.error("Error parsing entry: %s", str(e))
                    raise
            
            return entries
            
        except ET.ParseError as e:
            self.logger.error("XML parsing error: %s", str(e))
            raise
    
    def _parse_entry(self, entry_elem: ET.Element) -> Entry:
        """
        Parse an entry element into an Entry object.
        
        Args:
            entry_elem: XML element representing an entry
            
        Returns:
            Entry object
        """
        # Extract entry ID
        entry_id = entry_elem.get('id', '')
        
        # Parse lexical unit
        lexical_unit = self._parse_multitext(
            self._find_element(entry_elem, 'lexical-unit')
        )
        
        # Parse citation form
        citation = self._parse_multitext(
            self._find_element(entry_elem, 'citation')
        )
        
        # Parse senses
        senses = []
        sense_elements = self._find_elements(entry_elem, 'sense')
        for sense_elem in sense_elements:
            sense = self._parse_sense(sense_elem)
            senses.append(sense)
        
        # Parse pronunciations - build dict {lang: text}
        pronunciations = {}
        pronunciation_elements = self._find_elements(entry_elem, 'pronunciation')
        for pron_elem in pronunciation_elements:
            pronunciation = self._parse_pronunciation(pron_elem)
            # Merge the forms dict into pronunciations
            if isinstance(pronunciation, dict) and 'forms' in pronunciation:
                pronunciations.update(pronunciation['forms'])
        
        # Parse notes
        notes = []
        note_elements = self._find_elements(entry_elem, 'note')
        for note_elem in note_elements:
            note = self._parse_note(note_elem)
            notes.append(note)
        
        # Parse variants
        variants = []
        variant_elements = self._find_elements(entry_elem, 'variant')
        for variant_elem in variant_elements:
            variant = self._parse_variant(variant_elem)
            variants.append(variant)
        
        # Parse relations
        relations = []
        relation_elements = self._find_elements(entry_elem, 'relation')
        for relation_elem in relation_elements:
            relation = self._parse_relation(relation_elem)
            relations.append(relation)
        
        # Parse etymologies
        etymologies = []
        etymology_elements = self._find_elements(entry_elem, 'etymology')
        for etymology_elem in etymology_elements:
            etymology = self._parse_etymology(etymology_elem)
            etymologies.append(etymology)
        
        # Create Entry object
        return Entry(
            id_=entry_id,
            lexical_unit=lexical_unit,
            citation=citation,
            senses=senses,
            pronunciations=pronunciations,
            notes=notes,
            variants=variants,
            relations=relations,
            etymologies=etymologies,
            date_created=entry_elem.get('dateCreated'),
            date_modified=entry_elem.get('dateModified')
        )
    
    def _parse_sense(self, sense_elem: ET.Element) -> Sense:
        """Parse a sense element."""
        sense_id = sense_elem.get('id', '')
        order = sense_elem.get('order')
        
        # Parse gloss
        gloss = {}
        gloss_elements = self._find_elements(sense_elem, 'gloss')
        for gloss_elem in gloss_elements:
            lang = gloss_elem.get('lang', 'en')
            text_elem = self._find_element(gloss_elem, 'text')
            if text_elem is not None:
                # LIFT format: flat structure {lang: text}
                gloss[lang] = text_elem.text or ''
        
        # Parse definition
        definition = self._parse_multitext(
            self._find_element(sense_elem, 'definition')
        )
        
        # Parse grammatical info
        grammatical_info = None
        grammatical_info_elem = self._find_element(sense_elem, 'grammatical-info')
        if grammatical_info_elem is not None:
            grammatical_info = grammatical_info_elem.get('value')
        
        # Parse examples
        examples = []
        example_elements = self._find_elements(sense_elem, 'example')
        for example_elem in example_elements:
            example = self._parse_example(example_elem)
            examples.append(example)
        
        # Parse notes
        notes = []
        note_elements = self._find_elements(sense_elem, 'note')
        for note_elem in note_elements:
            note = self._parse_note(note_elem)
            notes.append(note)
        
        # Parse relations
        relations = []
        relation_elements = self._find_elements(sense_elem, 'relation')
        for relation_elem in relation_elements:
            relation = self._parse_relation(relation_elem)
            relations.append(relation)
        
        return Sense(
            id_=sense_id,
            order=int(order) if order else None,
            gloss=gloss,
            definition=definition,
            grammatical_info=grammatical_info,
            examples=examples,
            notes=notes,
            relations=relations
        )
    
    def _parse_example(self, example_elem: ET.Element) -> Example:
        """Parse an example element."""
        source = example_elem.get('source')
        
        # Parse example text
        example_text = self._parse_multitext(example_elem)
        
        # Parse translations
        translations = {}
        translation_elements = self._find_elements(example_elem, 'translation')
        for trans_elem in translation_elements:
            trans_type = trans_elem.get('type', 'free')
            trans_text = self._parse_multitext(trans_elem)
            translations[trans_type] = trans_text
        
        return Example(
            form=example_text,
            translations=translations,
            source=source
        )
    
    def _parse_multitext(self, element: Optional[ET.Element]) -> Dict[str, str]:
        """Parse a multitext element into language-text dictionary.
        
        LIFT format: flat structure {lang: text}
        """
        if element is None:
            return {}
        
        result = {}
        form_elements = self._find_elements(element, 'form')
        
        for form_elem in form_elements:
            lang = form_elem.get('lang', 'en')
            text_elem = self._find_element(form_elem, 'text')
            if text_elem is not None:
                result[lang] = text_elem.text or ''
        
        return result
    
    def _parse_pronunciation(self, pron_elem: ET.Element) -> Dict[str, Any]:
        """Parse a pronunciation element."""
        # Parse pronunciation forms
        forms = self._parse_multitext(pron_elem)
        
        # Parse media references
        media = []
        media_elements = self._find_elements(pron_elem, 'media')
        for media_elem in media_elements:
            href = media_elem.get('href')
            if href:
                media.append(href)
        
        return {
            'forms': forms,
            'media': media
        }
    
    def _parse_note(self, note_elem: ET.Element) -> Dict[str, Any]:
        """Parse a note element."""
        note_type = note_elem.get('type', 'general')
        content = self._parse_multitext(note_elem)
        
        return {
            'type': note_type,
            'content': content
        }
    
    def _parse_variant(self, variant_elem: ET.Element) -> Dict[str, Any]:
        """Parse a variant element."""
        ref = variant_elem.get('ref')
        forms = self._parse_multitext(variant_elem)
        
        return {
            'ref': ref,
            'forms': forms
        }
    
    def _parse_relation(self, relation_elem: ET.Element) -> Dict[str, Any]:
        """Parse a relation element."""
        relation_type = relation_elem.get('type')
        ref = relation_elem.get('ref')
        order = relation_elem.get('order')
        
        return {
            'type': relation_type,
            'ref': ref,
            'order': int(order) if order else None
        }
    
    def _parse_etymology(self, etymology_elem: ET.Element) -> Dict[str, Any]:
        """Parse an etymology element."""
        etymology_type = etymology_elem.get('type')
        source = etymology_elem.get('source')
        
        # Parse etymology forms
        forms = []
        form_elements = self._find_elements(etymology_elem, 'form')
        for form_elem in form_elements:
            forms.append(self._parse_multitext_form(form_elem))
        
        # Parse glosses
        glosses = []
        gloss_elements = self._find_elements(etymology_elem, 'gloss')
        for gloss_elem in gloss_elements:
            glosses.append(self._parse_multitext_form(gloss_elem))
        
        return {
            'type': etymology_type,
            'source': source,
            'forms': forms,
            'glosses': glosses
        }
    
    def _parse_multitext_form(self, form_elem: ET.Element) -> Dict[str, str]:
        """Parse a single form element."""
        lang = form_elem.get('lang', 'en')
        text_elem = self._find_element(form_elem, 'text')
        text = text_elem.text if text_elem is not None else ''
        
        return {lang: text}
    
    def _find_element(self, parent: ET.Element, tag: str) -> Optional[ET.Element]:
        """Find single element with namespace awareness."""
        # Use direct child search for most elements, recursive only for entry
        xpath = XPathBuilder.entry() if tag == 'entry' else f"./{tag}"
        xpath = LIFTNamespaceManager.get_xpath_with_namespace(xpath, self._has_lift_namespace)
        
        if self._has_lift_namespace:
            return parent.find(xpath, LIFTNamespaceManager.NAMESPACE_MAP)
        else:
            return parent.find(xpath)
    
    def _find_elements(self, parent: ET.Element, tag: str) -> List[ET.Element]:
        """Find multiple elements with namespace awareness."""
        # Use direct child search for most elements
        xpath = f"./{tag}"
        xpath = LIFTNamespaceManager.get_xpath_with_namespace(xpath, self._has_lift_namespace)
        
        if self._has_lift_namespace:
            return parent.findall(xpath, LIFTNamespaceManager.NAMESPACE_MAP)
        else:
            return parent.findall(xpath)
    
    def generate_lift_string(self, entries: List[Entry], 
                           include_namespace: bool = True) -> str:
        """
        Generate LIFT XML string from Entry objects.
        
        Args:
            entries: List of Entry objects
            include_namespace: Whether to include LIFT namespace
            
        Returns:
            LIFT XML string
        """
        # Create root element
        if include_namespace:
            root = LIFTNamespaceManager.create_element_with_namespace(
                'lift', {'version': '0.13'}, has_namespace=True
            )
        else:
            root = ET.Element('lift', {'version': '0.13'})
        
        # Add entries
        for entry in entries:
            entry_elem = self._generate_entry_element(entry, include_namespace)
            root.append(entry_elem)
        
        # Format XML
        xml_str = ET.tostring(root, encoding='unicode')
        
        # Pretty print
        try:
            dom = minidom.parseString(xml_str)
            return dom.toprettyxml(indent="  ", encoding=None)
        except Exception:
            return xml_str
    
    def _generate_entry_element(self, entry: Entry, include_namespace: bool) -> ET.Element:
        """Generate XML element for an entry."""
        # Create entry element
        entry_elem = LIFTNamespaceManager.create_element_with_namespace(
            'entry', {'id': entry.id}, has_namespace=include_namespace
        )
        
        # Add lexical unit
        if entry.lexical_unit:
            lexical_unit_elem = self._generate_multitext_element(
                'lexical-unit', entry.lexical_unit, include_namespace
            )
            entry_elem.append(lexical_unit_elem)
        
        # Add citation
        if entry.citation:
            citation_elem = self._generate_multitext_element(
                'citation', entry.citation, include_namespace
            )
            entry_elem.append(citation_elem)
        
        # Add senses
        for sense in entry.senses:
            sense_elem = self._generate_sense_element(sense, include_namespace)
            entry_elem.append(sense_elem)
        
        return entry_elem
    
    def _generate_sense_element(self, sense: Sense, include_namespace: bool) -> ET.Element:
        """Generate XML element for a sense."""
        attrib = {}
        if sense.id:
            attrib['id'] = sense.id
        if sense.order is not None:
            attrib['order'] = str(sense.order)
        
        sense_elem = LIFTNamespaceManager.create_element_with_namespace(
            'sense', attrib, has_namespace=include_namespace
        )
        
        # Add grammatical info
        if sense.grammatical_info:
            grammatical_info_elem = LIFTNamespaceManager.create_element_with_namespace(
                'grammatical-info', {'value': sense.grammatical_info}, 
                has_namespace=include_namespace
            )
            sense_elem.append(grammatical_info_elem)
        
        # Add gloss
        if sense.gloss:
            for lang, text in sense.gloss.items():
                gloss_elem = LIFTNamespaceManager.create_element_with_namespace(
                    'gloss', {'lang': lang}, has_namespace=include_namespace
                )
                text_elem = LIFTNamespaceManager.create_element_with_namespace(
                    'text', has_namespace=include_namespace
                )
                text_elem.text = text
                gloss_elem.append(text_elem)
                sense_elem.append(gloss_elem)
        
        # Add definition
        if sense.definition:
            definition_elem = self._generate_multitext_element(
                'definition', sense.definition, include_namespace
            )
            sense_elem.append(definition_elem)
        
        # Add examples
        for example in sense.examples:
            example_elem = self._generate_example_element(example, include_namespace)
            sense_elem.append(example_elem)
        
        return sense_elem
    
    def _generate_example_element(self, example: Example, include_namespace: bool) -> ET.Element:
        """Generate XML element for an example."""
        attrib = {}
        if example.source:
            attrib['source'] = example.source
        
        example_elem = LIFTNamespaceManager.create_element_with_namespace(
            'example', attrib, has_namespace=include_namespace
        )
        
        # Add example text
        if example.text:
            for lang, text in example.text.items():
                form_elem = LIFTNamespaceManager.create_element_with_namespace(
                    'form', {'lang': lang}, has_namespace=include_namespace
                )
                text_elem = LIFTNamespaceManager.create_element_with_namespace(
                    'text', has_namespace=include_namespace
                )
                text_elem.text = text
                form_elem.append(text_elem)
                example_elem.append(form_elem)
        
        # Add translations
        for trans_type, trans_text in example.translations.items():
            translation_elem = self._generate_multitext_element(
                'translation', trans_text, include_namespace
            )
            translation_elem.set('type', trans_type)
            example_elem.append(translation_elem)
        
        return example_elem
    
    def _generate_multitext_element(self, tag: str, content: Dict[str, str], 
                                  include_namespace: bool) -> ET.Element:
        """Generate multitext XML element."""
        element = LIFTNamespaceManager.create_element_with_namespace(
            tag, has_namespace=include_namespace
        )
        
        for lang, text in content.items():
            form_elem = LIFTNamespaceManager.create_element_with_namespace(
                'form', {'lang': lang}, has_namespace=include_namespace
            )
            text_elem = LIFTNamespaceManager.create_element_with_namespace(
                'text', has_namespace=include_namespace
            )
            text_elem.text = text
            form_elem.append(text_elem)
            element.append(form_elem)
        
        return element
