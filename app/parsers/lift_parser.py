"""
LIFT format parser and generator for dictionary data.

The LIFT (Lexicon Interchange Format) is an XML format for lexicographic data.
This module provides functionality for parsing and generating LIFT files.
"""

import logging
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from xml.dom import minidom

from app.models.entry import Entry, Etymology, Relation, Variant, Form, Gloss
from app.models.sense import Sense
from app.models.example import Example
from app.utils.exceptions import ValidationError


class LIFTParser:
    """
    Parser for LIFT format dictionary files.
    
    This class handles the parsing of LIFT XML files into model objects
    and the generation of LIFT XML from model objects.
    """
    
    # LIFT XML namespace
    NSMAP = {
        'lift': 'http://fieldworks.sil.org/schemas/lift/0.13',
        'flex': 'http://fieldworks.sil.org/schemas/flex/0.1'
    }
    
    # XPath constants
    XPATH_FORM = './/lift:form'
    XPATH_TEXT = './/lift:text'
    XPATH_LABEL = './/lift:label'
    XPATH_RANGE_ELEMENT = './/lift:range-element'
    
    # XML element constants
    ELEM_FORM = '}form'
    ELEM_TEXT = '}text'
    
    def __init__(self, validate: bool = True):
        """
        Initialize a LIFT parser.
        
        Args:
            validate: Whether to validate entries during parsing.        """
        self.validate = validate
        self.logger = logging.getLogger(__name__)

    def parse_entry(self, xml_string: str) -> Entry:
        """
        Parse a single LIFT entry XML string into an Entry object.
        
        Args:
            xml_string: LIFT XML string for a single entry.
            
        Returns:
            The parsed Entry object.
        """
        entries = self.parse_string(xml_string)
        if not entries:
            raise ValueError("No entry found in the provided XML string.")
        return entries[0]

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

    def _find_element_with_fallback(self, element: ET.Element, xpath_with_ns: str, xpath_without_ns: Optional[str] = None) -> Optional[ET.Element]:
        """
        Find an element with namespace fallback.
        
        Args:
            element: The parent element to search in
            xpath_with_ns: XPath with namespace prefix
            xpath_without_ns: XPath without namespace prefix (optional, auto-generated if None)
            
        Returns:
            Found element or None
        """
        # Try with namespace first
        found = element.find(xpath_with_ns, self.NSMAP)
        if found is not None:
            return found
        
        # Fallback to without namespace
        if xpath_without_ns is None:
            # Auto-generate xpath without namespace by removing 'lift:' prefixes
            xpath_without_ns = xpath_with_ns.replace('lift:', '')
        
        return element.find(xpath_without_ns)
    
    def _find_elements_with_fallback(self, element: ET.Element, xpath_with_ns: str, xpath_without_ns: Optional[str] = None) -> List[ET.Element]:
        """
        Find elements with namespace fallback.
        
        Args:
            element: The parent element to search in
            xpath_with_ns: XPath with namespace prefix
            xpath_without_ns: XPath without namespace prefix (optional, auto-generated if None)
            
        Returns:
            List of found elements
        """
        # Try with namespace first
        found = element.findall(xpath_with_ns, self.NSMAP)
        if found:
            return found
        
        # Fallback to without namespace
        if xpath_without_ns is None:
            # Auto-generate xpath without namespace by removing 'lift:' prefixes
            xpath_without_ns = xpath_with_ns.replace('lift:', '')
        
        return element.findall(xpath_without_ns)

    def _find_elements(self, parent: ET.Element, xpath: str) -> List[ET.Element]:
        """
        Find elements with fallback to non-namespaced xpath.
        
        Args:
            parent: Parent element to search in.
            xpath: XPath expression with lift: namespace prefix.
            
        Returns:
            List of matching elements.
        """
        # Try namespace-aware first
        elements = parent.findall(xpath, self.NSMAP)
        if not elements:
            # Fallback to non-namespaced
            non_ns_xpath = xpath.replace('lift:', '').replace('.//lift:', './/')
            elements = parent.findall(non_ns_xpath)
        return elements

    def _find_element(self, parent: ET.Element, xpath: str) -> Optional[ET.Element]:
        """
        Find single element with fallback to non-namespaced xpath.
        
        Args:
            parent: Parent element to search in.
            xpath: XPath expression with lift: namespace prefix.
            
        Returns:
            Matching element or None.
        """
        # Try namespace-aware first
        element = parent.find(xpath, self.NSMAP)
        if element is None:
            # Fallback to non-namespaced
            non_ns_xpath = xpath.replace('lift:', '').replace('.//lift:', './/')
            element = parent.find(non_ns_xpath)
        return element
    
    def parse_file(self, file_path: str) -> List[Entry]:
        """
        Parse a LIFT file into a list of Entry objects.
        
        Args:
            file_path: Path to the LIFT file.
            
        Returns:
            List of Entry objects.
              Raises:
            FileNotFoundError: If the file does not exist.
            ValidationError: If validation is enabled and an entry fails validation.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"LIFT file not found: {file_path}")
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            entries = []
            # Try namespace-aware first, then fallback to non-namespaced
            entry_elems = root.findall('.//lift:entry', self.NSMAP)
            if not entry_elems:
                entry_elems = root.findall('.//entry')
            
            for entry_elem in entry_elems:
                try:
                    entry = self._parse_entry(entry_elem)
                    if self.validate:
                        entry.validate()
                    entries.append(entry)
                except ValidationError as e:
                    self.logger.warning(f"Skipping invalid entry: {e}")
                    if self.validate:
                        raise
                except Exception as e:
                    self.logger.error(f"Error parsing entry: {e}")
                    raise
            
            return entries
            
        except ET.ParseError as e:
            self.logger.error(f"XML parsing error: {e}")
            raise

    def parse_string(self, xml_string: str) -> List[Entry]:
        """
        Parse a LIFT XML string into a list of Entry objects.
        
        Args:
            xml_string: LIFT XML string.
            
        Returns:
            List of Entry objects.
            
        Raises:
            ValidationError: If validation is enabled and an entry fails validation.
        """
        try:
            root = ET.fromstring(xml_string)
            
            entries = []
            entry_elems = []

            # Check if the root element is an entry
            if root.tag.endswith('entry'):
                entry_elems.append(root)
            else:
                # Try namespace-aware first, then fallback to non-namespaced
                entry_elems = root.findall('.//lift:entry', self.NSMAP)
                if not entry_elems:
                    entry_elems = root.findall('.//entry')
            
            for entry_elem in entry_elems:
                try:
                    entry = self._parse_entry(entry_elem)
                    if self.validate:
                        entry.validate()
                    entries.append(entry)
                except ValidationError as e:
                    self.logger.warning(f"Skipping invalid entry: {e}")
                    if self.validate:
                        raise
                except Exception as e:
                    self.logger.error(f"Error parsing entry: {e}")
                    raise
            
            return entries
        
        except ET.ParseError as e:
            self.logger.error(f"XML parsing error: {e}")
            raise
    
    def parse_entry_element(self, entry_elem: ET.Element) -> Entry:
        """
        Parse a single entry element into an Entry object.
        
        Args:
            entry_elem: Element representing an entry.
            
        Returns:
            Entry object.
            
        Raises:
            ValidationError: If validation is enabled and the entry fails validation.
        """
        entry = self._parse_entry(entry_elem)
        if self.validate:
            entry.validate()
        return entry
    
    def _parse_entry(self, entry_elem: ET.Element) -> Entry:
        """
        Parse an entry element into an Entry object.
        
        Args:
            entry_elem: Element representing an entry.
            
        Returns:
            Entry object.
        """
        # Get entry ID
        entry_id = entry_elem.get('id')
        if not entry_id:
            self.logger.warning("Entry without ID found, generating a new one")        # Parse lexical unit
        lexical_unit = {}
        lexical_unit_elem = self._find_element(entry_elem, './/lift:lexical-unit')
        if lexical_unit_elem is not None:
            for form_elem in self._find_elements(lexical_unit_elem, './/lift:form'):
                lang = form_elem.get('lang')
                text_elem = self._find_element(form_elem, './/lift:text')
                if lang and text_elem is not None and text_elem.text:
                    lexical_unit[lang] = text_elem.text
        
        # Parse etymologies
        etymologies = []
        for etymology_elem in self._find_elements(entry_elem, './/lift:etymology'):
            etymology_type = etymology_elem.get('type', '')
            etymology_source = etymology_elem.get('source', '')
            
            form_elem = self._find_element(etymology_elem, './/lift:form')
            gloss_elem = self._find_element(etymology_elem, './/lift:gloss')

            form = None
            if form_elem is not None:
                lang = form_elem.get('lang')
                text_elem = self._find_element(form_elem, './/lift:text')
                if text_elem is not None and text_elem.text:
                    form = Form(lang=lang or '', text=text_elem.text)

            gloss = None
            if gloss_elem is not None:
                lang = gloss_elem.get('lang')
                text_elem = self._find_element(gloss_elem, './/lift:text')
                if text_elem is not None and text_elem.text:
                    gloss = Gloss(lang=lang or '', text=text_elem.text)
            
            if form and gloss:
                etymologies.append(Etymology(
                    type=etymology_type,
                    source=etymology_source,
                    form=form,
                    gloss=gloss
                ))

          # Parse citations
        citations = []
        for citation_elem in entry_elem.findall('.//lift:citation', self.NSMAP):
            citation = {}
            for form_elem in citation_elem.findall(self.XPATH_FORM, self.NSMAP):
                lang = form_elem.get('lang')
                text_elem = form_elem.find(self.XPATH_TEXT, self.NSMAP)
                if lang and text_elem is not None and text_elem.text:
                    citation[lang] = text_elem.text
            if citation:
                citations.append(citation)
          # Parse pronunciations
        pronunciations = {}
        for pron_elem in self._find_elements(entry_elem, './/lift:pronunciation'):
            writing_system = pron_elem.get('writing-system')
            value = pron_elem.get('value')
            if writing_system and value:
                pronunciations[writing_system] = value
        
        # Parse variant forms
        variants = []
        for variant_elem in self._find_elements(entry_elem, './/lift:variant'):
            form_elem = self._find_element(variant_elem, './/lift:form')
            if form_elem is not None:
                lang = form_elem.get('lang')
                text_elem = self._find_element(form_elem, './/lift:text')
                if text_elem is not None and text_elem.text:
                    form = Form(lang=lang or '', text=text_elem.text)
                    variants.append(Variant(form=form))
        
        # Parse grammatical info
        grammatical_info = None
        gram_info_elem = entry_elem.find('.//lift:grammatical-info', self.NSMAP)
        if gram_info_elem is not None:
            grammatical_info = gram_info_elem.get('value')
        
        # Parse relations
        relations = []
        for relation_elem in self._find_elements(entry_elem, './/lift:relation'):
            relation_type = relation_elem.get('type')
            ref = relation_elem.get('ref')
            if relation_type and ref:
                relations.append(Relation(type=relation_type, ref=ref))
        
        # Parse notes
        notes = {}
        for note_elem in entry_elem.findall('.//lift:note', self.NSMAP):
            note_type = note_elem.get('type', 'general')
            if note_elem.text:
                notes[note_type] = note_elem.text
        
        # Parse custom fields
        custom_fields = {}
        for field_elem in entry_elem.findall('.//lift:field', self.NSMAP):
            field_type = field_elem.get('type', '')
            if field_type:
                value_elem = field_elem.find('.//lift:form/lift:text', self.NSMAP)
                if value_elem is not None and value_elem.text:
                    custom_fields[field_type] = value_elem.text
          # Parse senses
        senses = []
        for sense_elem in self._find_elements(entry_elem, './/lift:sense'):
            sense_id = sense_elem.get('id')
            sense = self._parse_sense(sense_elem, sense_id)
            senses.append(sense)  # Keep as Sense object, don't convert to dict
        
        # Create and return Entry object
        entry = Entry(
            id_=entry_id,
            lexical_unit=lexical_unit,
            citations=citations,
            pronunciations=pronunciations,
            variants=variants,
            grammatical_info=grammatical_info,
            relations=relations,
            etymologies=etymologies,
            notes=notes,
            custom_fields=custom_fields,
            senses=senses
        )
        
        return entry
        
    def _parse_sense(self, sense_elem: ET.Element, sense_id: Optional[str] = None) -> Sense:
        """
        Parse a sense element into a Sense object.
        
        Args:
            sense_elem: Element representing a sense.
            sense_id: Optional ID for the sense.
            
        Returns:
            Sense object.
        """        # Parse glosses
        glosses = {}
        for gloss_elem in self._find_elements(sense_elem, './/lift:gloss'):
            lang = gloss_elem.get('lang')
            text_elem = self._find_element(gloss_elem, './/lift:text')
            if lang and text_elem is not None and text_elem.text:
                glosses[lang] = text_elem.text
        
        # Parse definitions
        definitions = {}
        for def_elem in self._find_elements(sense_elem, './/lift:definition'):
            for form_elem in self._find_elements(def_elem, './/lift:form'):
                lang = form_elem.get('lang')
                text_elem = self._find_element(form_elem, './/lift:text')
                if lang and text_elem is not None and text_elem.text:
                    definitions[lang] = text_elem.text
        
        # Parse examples
        examples = []
        for example_elem in self._find_elements(sense_elem, './/lift:example'):
            example_id = example_elem.get('id')
            example = self._parse_example(example_elem, example_id)
            examples.append(example.to_dict())
        
        # Parse relations
        relations = []
        for relation_elem in self._find_elements(sense_elem, './/lift:relation'):
            relation = {
                'type': relation_elem.get('type', 'unspecified'),
                'ref': relation_elem.get('ref', ''),
            }
            if relation['ref']:
                relations.append(relation)
        
        # Parse grammatical info
        grammatical_info = None
        # Use the new helper method with namespace fallback
        gram_info_elem = self._find_element_with_fallback(sense_elem, './/lift:grammatical-info')
        
        if gram_info_elem is not None:
            grammatical_info = gram_info_elem.get('value')
        
        # Create and return Sense object
        return Sense(
            id_=sense_id,            glosses=glosses,            definitions=definitions,
            examples=examples,
            relations=relations,
            grammatical_info=grammatical_info
        )
        
    def _parse_example(self, example_elem: ET.Element, example_id: Optional[str] = None) -> Example:
        """
        Parse an example element into an Example object.
        
        Args:
            example_elem: Element representing an example.
            example_id: Optional ID for the example.
            
        Returns:
            Example object.
        """
        # Parse forms - should be direct children of example
        form = {}
        for form_elem in self._find_elements(example_elem, './lift:form'):
            lang = form_elem.get('lang')
            text_elem = self._find_element(form_elem, './/lift:text')
            if lang and text_elem is not None and text_elem.text:
                form[lang] = text_elem.text
        
        # Parse translations
        translations = {}
        for trans_elem in self._find_elements(example_elem, './/lift:translation'):
            for form_elem in self._find_elements(trans_elem, './/lift:form'):
                lang = form_elem.get('lang')
                text_elem = self._find_element(form_elem, './/lift:text')
                if lang and text_elem is not None and text_elem.text:
                    translations[lang] = text_elem.text
        
        # Create and return Example object
        return Example(
            id_=example_id,
            form=form,
            translations=translations
        )
    
    def generate_lift_file(self, entries: List[Entry], file_path: str) -> None:
        """
        Generate a LIFT file from a list of Entry objects.
        
        Args:
            entries: List of Entry objects.
            file_path: Path to the output LIFT file.
            
        Raises:
            ValidationError: If validation is enabled and an entry fails validation.
        """
        lift_xml = self.generate_lift_string(entries)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(lift_xml)
    
    def generate_lift_string(self, entries: List[Entry]) -> str:
        """
        Generate a LIFT XML string from a list of Entry objects.
        
        Args:
            entries: List of Entry objects.
            
        Returns:
            LIFT XML string.
              Raises:
            ValidationError: If validation is enabled and an entry fails validation.
        """
        root = self._generate_lift_root()
        
        for entry in entries:
            if self.validate:
                entry.validate()
            self._generate_entry_element(root, entry)
        
        xml_str = ET.tostring(root, encoding='utf-8')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")
        
        return pretty_xml
    
    def _generate_lift_root(self) -> ET.Element:
        """
        Generate the root element for a LIFT document.
        
        Returns:
            Root element.
        """
        ET.register_namespace('lift', self.NSMAP['lift'])
        ET.register_namespace('flex', self.NSMAP['flex'])
        
        root = ET.Element('{' + self.NSMAP['lift'] + '}lift')
        root.set('version', '0.13')
        
        return root
    
    def _generate_entry_element(self, parent: ET.Element, entry: Entry) -> ET.Element:
        """
        Generate an entry element from an Entry object.
        
        Args:
            parent: Parent element.
            entry: Entry object.
              Returns:
            Entry element.
        """
        entry_elem = ET.SubElement(parent, '{' + self.NSMAP['lift'] + '}entry')
        entry_elem.set('id', entry.id)
        
        # Add lexical unit
        if entry.lexical_unit:
            lex_unit = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}lexical-unit')
            for lang, text in entry.lexical_unit.items():
                form = ET.SubElement(lex_unit, '{' + self.NSMAP['lift'] + self.ELEM_FORM)
                form.set('lang', lang)
                text_elem = ET.SubElement(form, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                text_elem.text = text
        
        # Add etymologies
        for etymology in entry.etymologies:
            etymology_elem = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}etymology')
            etymology_elem.set('type', etymology.type)
            etymology_elem.set('source', etymology.source)
            
            if etymology.form:
                form_elem = ET.SubElement(etymology_elem, '{' + self.NSMAP['lift'] + '}form')
                form_elem.set('lang', etymology.form.lang)
                text_elem = ET.SubElement(form_elem, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                text_elem.text = etymology.form.text
            
            if etymology.gloss:
                gloss_elem = ET.SubElement(etymology_elem, '{' + self.NSMAP['lift'] + '}gloss')
                gloss_elem.set('lang', etymology.gloss.lang)
                text_elem = ET.SubElement(gloss_elem, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                text_elem.text = etymology.gloss.text

        # Add citations
        for citation in entry.citations:
            citation_elem = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}citation')
            for lang, text in citation.items():
                form = ET.SubElement(citation_elem, '{' + self.NSMAP['lift'] + self.ELEM_FORM)
                form.set('lang', lang)
                text_elem = ET.SubElement(form, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                text_elem.text = text
        
        # Add pronunciations
        for writing_system, value in entry.pronunciations.items():
            pron_elem = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}pronunciation')
            pron_elem.set('writing-system', writing_system)
            pron_elem.set('value', value)
        
        # Add variant forms
        for variant in entry.variants:
            variant_elem = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}variant')
            variant_type = variant.get('type', 'unspecified')
            variant_elem.set('type', variant_type)
            
            for lang, text in variant.items():
                if lang != 'type':
                    form = ET.SubElement(variant_elem, '{' + self.NSMAP['lift'] + self.ELEM_FORM)
                    form.set('lang', lang)
                    text_elem = ET.SubElement(form, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                    text_elem.text = text
        
        # Add grammatical info
        if entry.grammatical_info:
            gram_info = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}grammatical-info')
            gram_info.set('value', entry.grammatical_info)
        
        # Add relations
        for relation in entry.relations:
            relation_elem = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}relation')
            # Handle both Relation objects and dictionaries
            if hasattr(relation, 'type') and hasattr(relation, 'ref'):
                relation_elem.set('type', relation.type)
                relation_elem.set('ref', relation.ref)
            elif isinstance(relation, dict):
                # Fallback for dictionary format
                relation_elem.set('type', relation.get('type', 'unspecified'))
                relation_elem.set('ref', relation.get('ref', ''))
            else:
                # Default fallback
                relation_elem.set('type', 'unspecified')
                relation_elem.set('ref', '')
        
        # Add notes
        for note_type, note_text in entry.notes.items():
            note_elem = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}note')
            note_elem.set('type', note_type)
            note_elem.text = note_text
        
        # Add custom fields
        for field_type, field_value in entry.custom_fields.items():
            field_elem = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}field')
            field_elem.set('type', field_type)
            form = ET.SubElement(field_elem, '{' + self.NSMAP['lift'] + self.ELEM_FORM)
            text_elem = ET.SubElement(form, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
            text_elem.text = field_value
        
        # Add senses
        for sense_item in entry.senses:
            if isinstance(sense_item, dict):
                sense = Sense.from_dict(sense_item)
            else:
                # Already a Sense object
                sense = sense_item
            sense_elem = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}sense')
            if sense.id:
                sense_elem.set('id', sense.id)
              # Add glosses
            for lang, text in sense.glosses.items():
                gloss_elem = ET.SubElement(sense_elem, '{' + self.NSMAP['lift'] + '}gloss')
                gloss_elem.set('lang', lang)
                text_elem = ET.SubElement(gloss_elem, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                text_elem.text = text
            
            # Add definitions
            if sense.definitions:
                def_elem = ET.SubElement(sense_elem, '{' + self.NSMAP['lift'] + '}definition')
                for lang, text in sense.definitions.items():
                    form = ET.SubElement(def_elem, '{' + self.NSMAP['lift'] + self.ELEM_FORM)
                    form.set('lang', lang)
                    text_elem = ET.SubElement(form, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                    text_elem.text = text
            
            # Add examples
            for example_item in sense.examples:
                if isinstance(example_item, dict):
                    example = Example.from_dict(example_item)
                else:
                    # Already an Example object
                    example = example_item
                example_elem = ET.SubElement(sense_elem, '{' + self.NSMAP['lift'] + '}example')
                if example.id:
                    example_elem.set('id', example.id)                # Add forms
                for lang, text in example.form.items():
                    form = ET.SubElement(example_elem, '{' + self.NSMAP['lift'] + self.ELEM_FORM)
                    form.set('lang', lang)
                    text_elem = ET.SubElement(form, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                    text_elem.text = text
                
                # Add translations
                if example.translations:
                    trans_elem = ET.SubElement(example_elem, '{' + self.NSMAP['lift'] + '}translation')
                    for lang, text in example.translations.items():
                        form = ET.SubElement(trans_elem, '{' + self.NSMAP['lift'] + self.ELEM_FORM)
                        form.set('lang', lang)
                        text_elem = ET.SubElement(form, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                        text_elem.text = text
            
            # Add grammatical info
            if sense.grammatical_info:
                gram_info = ET.SubElement(sense_elem, '{' + self.NSMAP['lift'] + '}grammatical-info')
                gram_info.set('value', sense.grammatical_info)
            
            # Add relations
            for relation in sense.relations:
                relation_elem = ET.SubElement(sense_elem, '{' + self.NSMAP['lift'] + '}relation')
                relation_elem.set('type', relation.get('type', 'unspecified'))
                relation_elem.set('ref', relation.get('ref', ''))
        
        return entry_elem


class LIFTRangesParser:
    """
    Parser for LIFT ranges files.
    
    This class handles the parsing of LIFT ranges XML files, which define
    the allowed values for various fields in a LIFT dictionary.
    """
    
    # LIFT ranges XML namespace
    NSMAP = {
        'lift': 'http://fieldworks.sil.org/schemas/lift/0.13/ranges',
    }
    
    # XPath constants
    XPATH_LABEL = './/lift:label'
    XPATH_RANGE_ELEMENT = './/lift:range-element'
    
    def __init__(self):
        """Initialize a LIFT ranges parser."""
        self.logger = logging.getLogger(__name__)
    
    def parse_string(self, xml_string: str) -> Dict[str, Dict[str, Any]]:
        """
        Parse a LIFT ranges XML string into a dictionary of ranges.
        
        Args:
            xml_string: LIFT ranges XML string.
            
        Returns:
            Dictionary of ranges, keyed by range ID.
        """
        try:
            root = ET.fromstring(xml_string)
            
            ranges = {}
            # Try namespace-aware first, then fallback to non-namespaced
            range_elems = root.findall('.//lift:range', self.NSMAP)
            if not range_elems:
                range_elems = root.findall('.//range')
            
            for range_elem in range_elems:
                range_id = range_elem.get('id')
                if range_id:
                    range_data = self._parse_range(range_elem)
                    ranges[range_id] = range_data
            
            return ranges
        
        except ET.ParseError as e:
            self.logger.error(f"XML parsing error: {e}")
            raise

    def _find_elements(self, parent: ET.Element, xpath_with_ns: str, xpath_without_ns: str) -> List[ET.Element]:
        """
        Find elements with fallback from namespaced to non-namespaced.
        
        Args:
            parent: Parent element to search in.
            xpath_with_ns: XPath with namespace.
            xpath_without_ns: XPath without namespace.
            
        Returns:
            List of found elements.
        """
        elements = parent.findall(xpath_with_ns, self.NSMAP)
        if not elements:
            elements = parent.findall(xpath_without_ns)
        return elements
    
    def _find_element(self, parent: ET.Element, xpath_with_ns: str, xpath_without_ns: str) -> Optional[ET.Element]:
        """
        Find single element with fallback from namespaced to non-namespaced.
        
        Args:
            parent: Parent element to search in.
            xpath_with_ns: XPath with namespace.
            xpath_without_ns: XPath without namespace.
            
        Returns:
            Found element or None.
        """
        element = parent.find(xpath_with_ns, self.NSMAP)
        if element is None:
            element = parent.find(xpath_without_ns)
        return element

    def parse_file(self, file_path: str) -> Dict[str, Dict[str, Any]]:
        """
        Parse a LIFT ranges file into a dictionary of ranges.
        
        Args:
            file_path: Path to the LIFT ranges file.
            
        Returns:
            Dictionary of ranges, keyed by range ID.
              Raises:
            FileNotFoundError: If the file does not exist.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"LIFT ranges file not found: {file_path}")
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            ranges = {}
            # Try namespace-aware first, then fallback to non-namespaced
            range_elems = root.findall('.//lift:range', self.NSMAP)
            if not range_elems:
                range_elems = root.findall('.//range')
            
            for range_elem in range_elems:
                range_id = range_elem.get('id')
                if range_id:
                    range_data = self._parse_range(range_elem)
                    ranges[range_id] = range_data
            
            return ranges
        
        except ET.ParseError as e:
            self.logger.error(f"XML parsing error: {e}")
            raise
    
    def _parse_range(self, range_elem: ET.Element) -> Dict[str, Any]:
        """
        Parse a range element into a dictionary.
        
        Args:
            range_elem: Element representing a range.
            
        Returns:
            Dictionary containing range data.
        """
        range_id = range_elem.get('id', '')
        range_data = {
            'id': range_id,
            'guid': range_elem.get('guid', ''),
            'values': [],
            'description': {}
        }
        # Parse range labels (handle LIFT form structure)
        for label_elem in self._find_elements(range_elem, './lift:label', './label'):
            lang = label_elem.get('lang')
            if lang:
                # First try direct text content
                if label_elem.text and label_elem.text.strip():
                    range_data['description'][lang] = label_elem.text.strip()
                else:
                    # Try form/text structure
                    text_elem = self._find_element(label_elem, './lift:form/lift:text', './form/text')
                    if text_elem is not None and text_elem.text:
                        range_data['description'][lang] = text_elem.text.strip()
                    # Also try nested form elements with matching lang attribute
                    for form_elem in self._find_elements(label_elem, './lift:form', './form'):
                        form_lang = form_elem.get('lang')
                        if form_lang == lang or not form_lang:
                            text_elem = self._find_element(form_elem, './lift:text', './text')
                            if text_elem is not None and text_elem.text:
                                range_data['description'][lang] = text_elem.text.strip()
                                break
        # Parse range values (only direct children)
        for value_elem in self._find_elements(range_elem, './lift:range-element', './range-element'):
            value_id = value_elem.get('id', '')
            # Normalize orthographic -> spelling for variant types
            if range_id in ('variant-type', 'variant-types') and value_id == 'orthographic':
                value_id = 'spelling'
            value = {
                'id': value_id,
                'guid': value_elem.get('guid', ''),
                'value': value_elem.get('value', '') or value_id,
                'abbrev': '',  # Will be set below if abbrev element exists
                'description': {},
                'children': []
            }
            
            # Parse abbrev element (handle LIFT form structure)
            abbrev_elem = self._find_element(value_elem, './lift:abbrev', './abbrev')
            if abbrev_elem is not None:
                # First try direct text content
                if abbrev_elem.text and abbrev_elem.text.strip():
                    value['abbrev'] = abbrev_elem.text.strip()
                else:
                    # Try form/text structure
                    text_elem = self._find_element(abbrev_elem, './lift:form/lift:text', './form/text')
                    if text_elem is not None and text_elem.text:
                        value['abbrev'] = text_elem.text.strip()            # Parse value labels (handle LIFT form structure)
            for label_elem in self._find_elements(value_elem, './lift:label', './label'):
                lang = label_elem.get('lang')
                if lang:
                    # First try direct text content
                    if label_elem.text and label_elem.text.strip():
                        value['description'][lang] = label_elem.text.strip()
                    else:
                        # Try form/text structure
                        text_elem = self._find_element(label_elem, './lift:form/lift:text', './form/text')
                        if text_elem is not None and text_elem.text:
                            value['description'][lang] = text_elem.text.strip()
                        # Also try nested form elements with matching lang attribute
                        for form_elem in self._find_elements(label_elem, './lift:form', './form'):
                            form_lang = form_elem.get('lang')
                            if form_lang == lang or not form_lang:
                                text_elem = self._find_element(form_elem, './lift:text', './text')
                                if text_elem is not None and text_elem.text:
                                    value['description'][lang] = text_elem.text.strip()
                                    break
              # Parse child values (for hierarchical ranges, direct children only)
            for child_elem in self._find_elements(value_elem, './lift:range-element', './range-element'):
                child_value = self._parse_range_element(child_elem)
                value['children'].append(child_value)
            
            range_data['values'].append(value)
        
        return range_data
    
    def _parse_range_element(self, elem: ET.Element) -> Dict[str, Any]:
        """
        Parse a range element (hierarchical) into a dictionary.
        
        Args:
            elem: Element representing a range element.
              Returns:
            Dictionary containing range element data.
        """
        element_data = {
            'id': elem.get('id', ''),
            'guid': elem.get('guid', ''),
            'value': elem.get('value', ''),
            'abbrev': '',  # Will be set below if abbrev element exists
            'description': {},
            'children': []
        }
        
        # Parse abbrev element (handle LIFT form structure)
        abbrev_elem = self._find_element(elem, './lift:abbrev', './abbrev')
        if abbrev_elem is not None:
            # First try direct text content
            if abbrev_elem.text and abbrev_elem.text.strip():
                element_data['abbrev'] = abbrev_elem.text.strip()
            else:
                # Try form/text structure
                text_elem = self._find_element(abbrev_elem, './lift:form/lift:text', './form/text')
                if text_elem is not None and text_elem.text:
                    element_data['abbrev'] = text_elem.text.strip()
        
        # Parse element labels (handle LIFT form structure)
        for label_elem in self._find_elements(elem, './lift:label', './label'):
            lang = label_elem.get('lang')
            if lang:
                # First try direct text content
                if label_elem.text and label_elem.text.strip():
                    element_data['description'][lang] = label_elem.text.strip()
                else:
                    # Try form/text structure
                    text_elem = self._find_element(label_elem, './lift:form/lift:text', './form/text')
                    if text_elem is not None and text_elem.text:
                        element_data['description'][lang] = text_elem.text.strip()
                    # Also try nested form elements with matching lang attribute
                    for form_elem in self._find_elements(label_elem, './lift:form', './form'):
                        form_lang = form_elem.get('lang')
                        if form_lang == lang or not form_lang:
                            text_elem = self._find_element(form_elem, './lift:text', './text')
                            if text_elem is not None and text_elem.text:
                                element_data['description'][lang] = text_elem.text.strip()
                                break
        
        # Parse child elements (recursive, direct children only)
        for child_elem in self._find_elements(elem, './lift:range-element', './range-element'):
            child_data = self._parse_range_element(child_elem)
            element_data['children'].append(child_data)
        
        return element_data
