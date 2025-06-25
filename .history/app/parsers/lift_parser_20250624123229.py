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

from app.models import Entry, Sense, Example
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
            ValidationError: If validation is enabled and an entry fails validation.        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"LIFT file not found: {file_path}")
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            entries = []
            for entry_elem in root.findall('.//lift:entry', self.NSMAP):
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
        variant_forms = []
        for variant_elem in entry_elem.findall('.//lift:variant', self.NSMAP):
            variant = {}
            variant['type'] = variant_elem.get('type', 'unspecified')
            for form_elem in variant_elem.findall(self.XPATH_FORM, self.NSMAP):
                lang = form_elem.get('lang')
                text_elem = form_elem.find(self.XPATH_TEXT, self.NSMAP)
                if lang and text_elem is not None and text_elem.text:
                    variant[lang] = text_elem.text
            if len(variant) > 1:  # Must have at least one form besides type
                variant_forms.append(variant)
        
        # Parse grammatical info
        grammatical_info = None
        gram_info_elem = entry_elem.find('.//lift:grammatical-info', self.NSMAP)
        if gram_info_elem is not None:
            grammatical_info = gram_info_elem.get('value')
        
        # Parse relations
        relations = []
        for relation_elem in entry_elem.findall('.//lift:relation', self.NSMAP):
            relation = {
                'type': relation_elem.get('type', 'unspecified'),
                'ref': relation_elem.get('ref', ''),
            }
            if relation['ref']:
                relations.append(relation)
        
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
            senses.append(sense.to_dict())
        
        # Create and return Entry object
        entry = Entry(
            id_=entry_id,
            lexical_unit=lexical_unit,
            citations=citations,
            pronunciations=pronunciations,
            variant_forms=variant_forms,
            grammatical_info=grammatical_info,
            relations=relations,            notes=notes,
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
        for example_elem in sense_elem.findall('.//lift:example', self.NSMAP):
            example_id = example_elem.get('id')
            example = self._parse_example(example_elem, example_id)
            examples.append(example.to_dict())
        
        # Parse relations
        relations = []
        for relation_elem in sense_elem.findall('.//lift:relation', self.NSMAP):
            relation = {
                'type': relation_elem.get('type', 'unspecified'),
                'ref': relation_elem.get('ref', ''),
            }
            if relation['ref']:
                relations.append(relation)
        
        # Parse grammatical info
        grammatical_info = None
        gram_info_elem = sense_elem.find('.//lift:grammatical-info', self.NSMAP)
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
        # Parse forms
        form = {}
        for form_elem in example_elem.findall(self.XPATH_FORM, self.NSMAP):
            lang = form_elem.get('lang')
            text_elem = form_elem.find(self.XPATH_TEXT, self.NSMAP)
            if lang and text_elem is not None and text_elem.text:
                form[lang] = text_elem.text
          # Parse translations
        translations = {}
        for trans_elem in example_elem.findall('.//lift:translation', self.NSMAP):
            for form_elem in trans_elem.findall(self.XPATH_FORM, self.NSMAP):
                lang = form_elem.get('lang')
                text_elem = form_elem.find(self.XPATH_TEXT, self.NSMAP)
                if lang and text_elem is not None and text_elem.text:
                    translations[lang] = text_elem.text# Create and return Example object
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
            entry_elem = self._generate_entry_element(root, entry)
            root.append(entry_elem)
        
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
            pron_elem.set('writing-system', writing_system)            pron_elem.set('value', value)
        
        # Add variant forms
        for variant in entry.variant_forms:
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
            relation_elem.set('type', relation.get('type', 'unspecified'))
            relation_elem.set('ref', relation.get('ref', ''))
        
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
        for sense_dict in entry.senses:
            sense = Sense.from_dict(sense_dict)
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
            for example_dict in sense.examples:
                example = Example.from_dict(example_dict)
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
            for range_elem in root.findall('.//lift:range', self.NSMAP):
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
        range_data = {
            'id': range_elem.get('id', ''),
            'guid': range_elem.get('guid', ''),
            'values': [],
            'description': {}
        }
          # Parse range labels
        for label_elem in range_elem.findall(self.XPATH_LABEL, self.NSMAP):
            lang = label_elem.get('lang')
            if lang and label_elem.text:
                range_data['description'][lang] = label_elem.text
        
        # Parse range values
        for value_elem in range_elem.findall(self.XPATH_RANGE_ELEMENT, self.NSMAP):
            value = {
                'id': value_elem.get('id', ''),
                'guid': value_elem.get('guid', ''),
                'value': value_elem.get('value', ''),
                'abbrev': value_elem.get('abbrev', ''),
                'description': {},
                'children': []
            }
            
            # Parse value labels
            for label_elem in value_elem.findall(self.XPATH_LABEL, self.NSMAP):
                lang = label_elem.get('lang')
                if lang and label_elem.text:
                    value['description'][lang] = label_elem.text
            
            # Parse child values (for hierarchical ranges)
            for child_elem in value_elem.findall(self.XPATH_RANGE_ELEMENT, self.NSMAP):
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
            'abbrev': elem.get('abbrev', ''),
            'description': {},
            'children': []
        }
          # Parse element labels
        for label_elem in elem.findall(self.XPATH_LABEL, self.NSMAP):
            lang = label_elem.get('lang')
            if lang and label_elem.text:
                element_data['description'][lang] = label_elem.text
        
        # Parse child elements (recursive)
        for child_elem in elem.findall(self.XPATH_RANGE_ELEMENT, self.NSMAP):
            child_data = self._parse_range_element(child_elem)
            element_data['children'].append(child_data)
        
        return element_data
