"""
LIFT format parser and generator for dictionary data.

The LIFT (Lexicon Interchange Format) is an XML format for lexicographic data.
This module provides functionality for parsing and generating LIFT files.
"""

import logging
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Iterator, Union
from xml.dom import minidom

from app.models.entry import Entry
from app.models.sense import Sense
from app.models.example import Example
from app.models.pronunciation import Pronunciation
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
    
    def __init__(self, validate: bool = True):
        """
        Initialize a LIFT parser.
        
        Args:
            validate: Whether to validate entries during parsing.
        """
        self.validate = validate
        self.logger = logging.getLogger(__name__)
    
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
        
        self.logger.info(f"Parsing LIFT file: {file_path}")
        
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        return self.parse_root(root)
    
    def parse_string(self, lift_string: str) -> List[Entry]:
        """
        Parse a LIFT XML string into a list of Entry objects.
        
        Args:
            lift_string: LIFT XML string.
            
        Returns:
            List of Entry objects.
            
        Raises:
            ValidationError: If validation is enabled and an entry fails validation.
        """
        self.logger.info("Parsing LIFT string")
        
        root = ET.fromstring(lift_string)
        
        return self.parse_root(root)
    
    def parse_root(self, root: ET.Element) -> List[Entry]:
        """
        Parse a LIFT XML root element into a list of Entry objects.
        
        Args:
            root: LIFT XML root element.
            
        Returns:
            List of Entry objects.
            
        Raises:
            ValidationError: If validation is enabled and an entry fails validation.
        """
        entries = []
        
        # Register namespaces for XPath
        for prefix, uri in self.NSMAP.items():
            ET.register_namespace(prefix, uri)
        
        # Find all entry elements
        for entry_elem in root.findall('.//entry'):
            try:
                entry = self.parse_entry(entry_elem)
                
                if self.validate:
                    entry.validate()
                
                entries.append(entry)
            except Exception as e:
                entry_id = entry_elem.get('id', 'unknown')
                self.logger.warning(f"Error parsing entry {entry_id}: {e}")
                if self.validate:
                    raise
        
        self.logger.info(f"Parsed {len(entries)} entries")
        
        return entries
    
    def parse_entry(self, entry_elem: ET.Element) -> Entry:
        """
        Parse an entry element into an Entry object.
        
        Args:
            entry_elem: Entry element.
            
        Returns:
            Entry object.
        """
        entry_id = entry_elem.get('id')
        
        # Parse lexical unit
        lexical_unit = {}
        lexical_unit_elem = entry_elem.find('.//lexical-unit')
        if lexical_unit_elem is not None:
            for form_elem in lexical_unit_elem.findall('.//form'):
                lang = form_elem.get('lang')
                text_elem = form_elem.find('.//text')
                if lang and text_elem is not None and text_elem.text:
                    lexical_unit[lang] = text_elem.text
        
        # Parse grammatical info
        grammatical_info = None
        grammatical_info_elem = entry_elem.find('.//grammatical-info')
        if grammatical_info_elem is not None:
            grammatical_info = grammatical_info_elem.get('value')
        
        # Parse senses
        senses = []
        for sense_elem in entry_elem.findall('.//sense'):
            sense = self.parse_sense(sense_elem)
            senses.append(sense.__dict__)
        
        # Parse pronunciations
        pronunciations = {}
        for pronunciation_elem in entry_elem.findall('.//pronunciation'):
            for form_elem in pronunciation_elem.findall('.//form'):
                lang = form_elem.get('lang')
                text_elem = form_elem.find('.//text')
                if lang and text_elem is not None and text_elem.text:
                    pronunciations[lang] = text_elem.text
        
        # Parse variant forms
        variant_forms = []
        for variant_elem in entry_elem.findall('.//variant'):
            variant = {}
            for form_elem in variant_elem.findall('.//form'):
                lang = form_elem.get('lang')
                text_elem = form_elem.find('.//text')
                if lang and text_elem is not None and text_elem.text:
                    if 'form' not in variant:
                        variant['form'] = {}
                    variant['form'][lang] = text_elem.text
            
            if variant:
                variant_forms.append(variant)
        
        # Parse relations
        relations = []
        for relation_elem in entry_elem.findall('.//relation'):
            relation_type = relation_elem.get('type')
            ref = relation_elem.get('ref')
            if relation_type and ref:
                relations.append({
                    'type': relation_type,
                    'ref': ref
                })
        
        # Parse notes
        notes = {}
        for note_elem in entry_elem.findall('.//note'):
            note_type = note_elem.get('type')
            for form_elem in note_elem.findall('.//form'):
                lang = form_elem.get('lang')
                text_elem = form_elem.find('.//text')
                if note_type and lang and text_elem is not None and text_elem.text:
                    notes[note_type] = text_elem.text
        
        # Create and return Entry object
        return Entry(
            id_=entry_id,
            lexical_unit=lexical_unit,
            pronunciations=pronunciations,
            grammatical_info=grammatical_info,
            senses=senses,
            variant_forms=variant_forms,
            relations=relations,
            notes=notes
        )
    
    def parse_sense(self, sense_elem: ET.Element) -> Sense:
        """
        Parse a sense element into a Sense object.
        
        Args:
            sense_elem: Sense element.
            
        Returns:
            Sense object.
        """
        sense_id = sense_elem.get('id')
        
        # Parse definitions
        definitions = {}
        for definition_elem in sense_elem.findall('.//definition'):
            for form_elem in definition_elem.findall('.//form'):
                lang = form_elem.get('lang')
                text_elem = form_elem.find('.//text')
                if lang and text_elem is not None and text_elem.text:
                    definitions[lang] = text_elem.text
        
        # Parse grammatical info
        grammatical_info = None
        grammatical_info_elem = sense_elem.find('.//grammatical-info')
        if grammatical_info_elem is not None:
            grammatical_info = grammatical_info_elem.get('value')
        
        # Parse examples
        examples = []
        for example_elem in sense_elem.findall('.//example'):
            example = self.parse_example(example_elem)
            examples.append(example.__dict__)
        
        # Parse relations
        relations = []
        for relation_elem in sense_elem.findall('.//relation'):
            relation_type = relation_elem.get('type')
            ref = relation_elem.get('ref')
            if relation_type and ref:
                relations.append({
                    'type': relation_type,
                    'ref': ref
                })
        
        # Parse notes
        notes = {}
        for note_elem in sense_elem.findall('.//note'):
            note_type = note_elem.get('type')
            for form_elem in note_elem.findall('.//form'):
                lang = form_elem.get('lang')
                text_elem = form_elem.find('.//text')
                if note_type and lang and text_elem is not None and text_elem.text:
                    notes[note_type] = text_elem.text
        
        # Create and return Sense object
        return Sense(
            id_=sense_id,
            definitions=definitions,
            grammatical_info=grammatical_info,
            examples=examples,
            relations=relations,
            notes=notes
        )
    
    def parse_example(self, example_elem: ET.Element) -> Example:
        """
        Parse an example element into an Example object.
        
        Args:
            example_elem: Example element.
            
        Returns:
            Example object.
        """
        example_id = example_elem.get('id')
        
        # Parse forms
        forms = {}
        for form_elem in example_elem.findall('.//form'):
            lang = form_elem.get('lang')
            text_elem = form_elem.find('.//text')
            if lang and text_elem is not None and text_elem.text:
                forms[lang] = text_elem.text
        
        # Parse translations
        translations = {}
        for translation_elem in example_elem.findall('.//translation'):
            for form_elem in translation_elem.findall('.//form'):
                lang = form_elem.get('lang')
                text_elem = form_elem.find('.//text')
                if lang and text_elem is not None and text_elem.text:
                    translations[lang] = text_elem.text
        
        # Create and return Example object
        return Example(
            id_=example_id,
            forms=forms,
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
        # Create root element
        root = ET.Element('lift')
        root.set('version', '0.13')
        root.set('producer', 'Dictionary Writing System')
        
        # Create header element
        header = ET.SubElement(root, 'header')
        
        return root
    
    def _generate_entry_element(self, root: ET.Element, entry: Entry) -> ET.Element:
        """
        Generate an entry element from an Entry object.
        
        Args:
            root: Root element.
            entry: Entry object.
            
        Returns:
            Entry element.
        """
        # Create entry element
        entry_elem = ET.Element('entry')
        entry_elem.set('id', entry.id)
        
        # Add lexical unit
        if entry.lexical_unit:
            lexical_unit = ET.SubElement(entry_elem, 'lexical-unit')
            for lang, text in entry.lexical_unit.items():
                form = ET.SubElement(lexical_unit, 'form')
                form.set('lang', lang)
                text_elem = ET.SubElement(form, 'text')
                text_elem.text = text
        
        # Add grammatical info
        if entry.grammatical_info:
            grammatical_info = ET.SubElement(entry_elem, 'grammatical-info')
            grammatical_info.set('value', entry.grammatical_info)
        
        # Add pronunciations
        for lang, text in entry.pronunciations.items():
            pronunciation = ET.SubElement(entry_elem, 'pronunciation')
            form = ET.SubElement(pronunciation, 'form')
            form.set('lang', lang)
            text_elem = ET.SubElement(form, 'text')
            text_elem.text = text
        
        # Add variant forms
        for variant in entry.variant_forms:
            variant_elem = ET.SubElement(entry_elem, 'variant')
            if 'form' in variant:
                for lang, text in variant['form'].items():
                    form = ET.SubElement(variant_elem, 'form')
                    form.set('lang', lang)
                    text_elem = ET.SubElement(form, 'text')
                    text_elem.text = text
        
        # Add senses
        for sense_data in entry.senses:
            sense = Sense(**sense_data)
            sense_elem = self._generate_sense_element(entry_elem, sense)
            entry_elem.append(sense_elem)
        
        # Add relations
        for relation in entry.relations:
            relation_elem = ET.SubElement(entry_elem, 'relation')
            relation_elem.set('type', relation['type'])
            relation_elem.set('ref', relation['ref'])
        
        # Add notes
        for note_type, text in entry.notes.items():
            note = ET.SubElement(entry_elem, 'note')
            note.set('type', note_type)
            form = ET.SubElement(note, 'form')
            form.set('lang', 'en')  # Default to English
            text_elem = ET.SubElement(form, 'text')
            text_elem.text = text
        
        return entry_elem
    
    def _generate_sense_element(self, entry_elem: ET.Element, sense: Sense) -> ET.Element:
        """
        Generate a sense element from a Sense object.
        
        Args:
            entry_elem: Entry element.
            sense: Sense object.
            
        Returns:
            Sense element.
        """
        # Create sense element
        sense_elem = ET.Element('sense')
        sense_elem.set('id', sense.id)
        
        # Add definitions
        for lang, text in sense.definitions.items():
            definition = ET.SubElement(sense_elem, 'definition')
            form = ET.SubElement(definition, 'form')
            form.set('lang', lang)
            text_elem = ET.SubElement(form, 'text')
            text_elem.text = text
        
        # Add grammatical info
        if sense.grammatical_info:
            grammatical_info = ET.SubElement(sense_elem, 'grammatical-info')
            grammatical_info.set('value', sense.grammatical_info)
        
        # Add examples
        for example_data in sense.examples:
            example = Example(**example_data)
            example_elem = self._generate_example_element(sense_elem, example)
            sense_elem.append(example_elem)
        
        # Add relations
        for relation in sense.relations:
            relation_elem = ET.SubElement(sense_elem, 'relation')
            relation_elem.set('type', relation['type'])
            relation_elem.set('ref', relation['ref'])
        
        # Add notes
        for note_type, text in sense.notes.items():
            note = ET.SubElement(sense_elem, 'note')
            note.set('type', note_type)
            form = ET.SubElement(note, 'form')
            form.set('lang', 'en')  # Default to English
            text_elem = ET.SubElement(form, 'text')
            text_elem.text = text
        
        return sense_elem
    
    def _generate_example_element(self, sense_elem: ET.Element, example: Example) -> ET.Element:
        """
        Generate an example element from an Example object.
        
        Args:
            sense_elem: Sense element.
            example: Example object.
            
        Returns:
            Example element.
        """
        # Create example element
        example_elem = ET.Element('example')
        if example.id:
            example_elem.set('id', example.id)
        
        # Add forms
        for lang, text in example.forms.items():
            form = ET.SubElement(example_elem, 'form')
            form.set('lang', lang)
            text_elem = ET.SubElement(form, 'text')
            text_elem.text = text
        
        # Add translations
        for lang, text in example.translations.items():
            translation = ET.SubElement(example_elem, 'translation')
            form = ET.SubElement(translation, 'form')
            form.set('lang', lang)
            text_elem = ET.SubElement(form, 'text')
            text_elem.text = text
        
        return example_elem


class LIFTRangesParser:
    """
    Parser for LIFT ranges files.
    
    LIFT ranges files define the valid values for fields in a LIFT file.
    """
    
    def __init__(self):
        """Initialize a LIFT ranges parser."""
        self.logger = logging.getLogger(__name__)
    
    def parse_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a LIFT ranges file.
        
        Args:
            file_path: Path to the LIFT ranges file.
            
        Returns:
            Dictionary of range definitions.
            
        Raises:
            FileNotFoundError: If the file does not exist.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"LIFT ranges file not found: {file_path}")
        
        self.logger.info(f"Parsing LIFT ranges file: {file_path}")
        
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        ranges = {}
        
        # Process each range element
        for range_elem in root.findall('.//range'):
            range_id = range_elem.get('id')
            
            if not range_id:
                continue
            
            range_data = {
                'id': range_id,
                'values': []
            }
            
            # Process range values
            for range_element in range_elem.findall('.//range-element'):
                guid = range_element.get('guid')
                
                if not guid:
                    continue
                
                value_data = {
                    'guid': guid,
                    'values': {}
                }
                
                # Process value labels
                for label_elem in range_element.findall('.//label'):
                    lang = label_elem.get('lang', 'en')
                    value_data['values'][lang] = label_elem.text or ''
                
                range_data['values'].append(value_data)
            
            ranges[range_id] = range_data
        
        self.logger.info(f"Parsed {len(ranges)} ranges")
        
        return ranges
