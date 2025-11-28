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

from app.models.entry import Entry, Etymology, Relation, Variant
from app.models.sense import Sense
from app.models.example import Example
from app.utils.exceptions import ValidationError


class LIFTParser:
    """
    Parser for LIFT format dictionary files.
    
    This class handles the parsing of LIFT XML files into model objects
    and the generation of LIFT XML from model objects.
    """
    @staticmethod
    def _normalize_multilingual_dict(d: dict) -> dict:
        """
        Ensure all values in a multilingual dict are {"text": ...} dicts, but do not double-wrap.
        """
        for k, v in list(d.items()):
            if isinstance(v, dict) and set(v.keys()) == {"text"} and isinstance(v["text"], str):
                # Already normalized
                continue
            elif isinstance(v, dict):
                d[k] = LIFTParser._normalize_multilingual_dict(v)
            else:
                d[k] = {"text": v}
        return d
    
    
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

    def _find_elements(self, parent: ET.Element, xpath_with_ns: str, xpath_without_ns: Optional[str] = None) -> List[ET.Element]:
        """
        Find elements with fallback to non-namespaced xpath.
        
        Args:
            parent: Parent element to search in.
            xpath_with_ns: XPath expression with lift: namespace prefix.
            xpath_without_ns: Optional XPath without namespace prefix (auto-generated if None).
            
        Returns:
            List of found elements or empty list if none found.
        """
        if xpath_without_ns is None:
            # Auto-generate non-namespaced version by removing 'lift:' prefix
            xpath_without_ns = xpath_with_ns.replace('lift:', '')
            
        # Try with namespace first
        found = parent.findall(xpath_with_ns, self.NSMAP)
        if found:
            return found
            
        # Fall back to non-namespaced version
        return parent.findall(xpath_without_ns)

    def _find_element(self, parent: ET.Element, xpath_with_ns: str, xpath_without_ns: Optional[str] = None) -> Optional[ET.Element]:
        """
        Find single element with fallback to non-namespaced xpath.
        
        Args:
            parent: Parent element to search in.
            xpath_with_ns: XPath expression with lift: namespace prefix.
            xpath_without_ns: Optional XPath without namespace prefix (auto-generated if None).
            
        Returns:
            Matching element or None.
        """
        if xpath_without_ns is None:
            # Auto-generate non-namespaced version by removing 'lift:' prefix
            xpath_without_ns = xpath_with_ns.replace('lift:', '')
            
        # Try namespace-aware first
        element = parent.find(xpath_with_ns, self.NSMAP)
        if element is not None:
            return element
            
        # Fall back to non-namespaced version
        return parent.find(xpath_without_ns)
    
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
        return self.parse_lift_content(xml_string)
    
    def parse_lift_content(self, xml_string: str) -> List[Entry]:
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
            # Clean up the XML string to handle potential whitespace issues
            xml_string = xml_string.strip()
            
            # Handle case where we have multiple entry elements without a root
            # This is common in test mocks and some database responses
            if xml_string.startswith('<entry') and not xml_string.startswith('<entry>'):
                # Multiple entries without a root - wrap them
                xml_string = f"<lift>{xml_string}</lift>"
            
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
        
        except ValidationError:
            # Re-raise ValidationError as-is (already logged in inner try-except)
            raise
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
            self.logger.warning("Entry without ID found, generating a new one")
            
        # Get homograph number from order attribute (LIFT specification)
        homograph_number = entry_elem.get('order')
        if homograph_number:
            try:
                homograph_number = int(homograph_number)
            except ValueError:
                self.logger.warning(f"Invalid homograph number '{homograph_number}' for entry {entry_id}")
                homograph_number = None
        else:
            homograph_number = None        # Parse lexical unit
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

            form: dict[str, str] = {}
            if form_elem is not None:
                lang = form_elem.get('lang')
                text_elem = self._find_element(form_elem, './/lift:text')
                if text_elem is not None and text_elem.text:
                    form = {lang or '': text_elem.text}

            gloss: dict[str, str] = {}
            if gloss_elem is not None:
                lang = gloss_elem.get('lang')
                text_elem = self._find_element(gloss_elem, './/lift:text')
                if text_elem is not None and text_elem.text:
                    gloss = {lang or '': text_elem.text}

            if form and gloss:
                # Ensure form and gloss are always {lang: text, ...}
                if not (isinstance(form, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in form.items())):
                    raise ValueError("Etymology 'form' must be a nested dict {lang: text, ...}")
                if not (isinstance(gloss, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in gloss.items())):
                    raise ValueError("Etymology 'gloss' must be a nested dict {lang: text, ...}")
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
        pron_elements = self._find_elements(entry_elem, './/lift:pronunciation')
        self.logger.debug(f"Found {len(pron_elements)} pronunciation elements")
        
        for pron_elem in pron_elements:
            form_elem = self._find_element(pron_elem, './/lift:form')
            if form_elem is not None:
                writing_system = form_elem.get('lang', '')
                text_elem = self._find_element(form_elem, './/lift:text')
                value = text_elem.text if text_elem is not None else ''
                
                self.logger.debug(f"Extracted pronunciation: {writing_system} = '{value}'")
                if writing_system and value:
                    pronunciations[writing_system] = value
            else:
                # Legacy format
                writing_system = pron_elem.get('writing-system')
                value = pron_elem.get('value')
                if writing_system and value:
                    pronunciations[writing_system] = value
        
        if pronunciations:
            self.logger.debug(f"Final pronunciations: {pronunciations}")
        else:
            self.logger.debug("No pronunciations found")
        
        # Parse variant forms
        variants = []
        for variant_elem in self._find_elements(entry_elem, './/lift:variant'):
            form_elem = self._find_element(variant_elem, './/lift:form')
            if form_elem is not None:
                lang = form_elem.get('lang')
                text_elem = self._find_element(form_elem, './/lift:text')
                if text_elem is not None and text_elem.text:
                    form = {lang or '': text_elem.text}
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
                # Parse traits within this relation
                traits = {}
                for trait_elem in self._find_elements(relation_elem, './/lift:trait'):
                    trait_name = trait_elem.get('name')
                    trait_value = trait_elem.get('value')
                    if trait_name and trait_value:
                        traits[trait_name] = trait_value
                
                relations.append(Relation(type=relation_type, ref=ref, traits=traits))
        
        # Parse notes
        notes = {}
        for note_elem in self._find_elements(entry_elem, './/lift:note', './/note'):
            note_type = note_elem.get('type', 'general')
            # Check for multilingual structured format: <note><form lang=...><text>...</text></form></note>
            form_elements = self._find_elements(note_elem, './/lift:form', './/form')

            note_has_content = False
            if form_elements:
                # New structured format with potentially multiple languages
                if note_type not in notes:
                    notes[note_type] = {}
                for form_elem in form_elements:
                    lang = form_elem.get('lang', '')
                    text_elem = self._find_element(form_elem, './/lift:text', './/text')
                    if text_elem is not None and text_elem.text and text_elem.text.strip():
                        # Always wrap as dict
                        notes[note_type][lang] = {"text": text_elem.text}
                        note_has_content = True
            elif note_elem.text and note_elem.text.strip():
                # Legacy format: <note>text</note>
                notes[note_type] = {"und": {"text": note_elem.text}}
                note_has_content = True

            # If a note element exists but has no content, remove it
            if not note_has_content and note_type in notes:
                del notes[note_type]

        # Final normalization to ensure all values are nested dicts
        notes = self._normalize_multilingual_dict(notes)
        
        # Parse custom fields
        custom_fields = {}
        for field_elem in entry_elem.findall('.//lift:field', self.NSMAP):
            field_type = field_elem.get('type', '')
            if field_type:
                # Check for multilingual structured format: <field><form lang=...><text>...</text></form></field>
                form_elements = self._find_elements(field_elem, './/lift:form', './/form')
                
                if form_elements:
                    # Multilingual format
                    for form_elem in form_elements:
                        lang = form_elem.get('lang', '')
                        text_elem = self._find_element(form_elem, './/lift:text', './/text')
                        if text_elem is not None and text_elem.text:
                            if field_type not in custom_fields:
                                custom_fields[field_type] = {}
                            if isinstance(custom_fields[field_type], dict):
                                custom_fields[field_type][lang] = {"text": text_elem.text}
                            else:
                                # Convert single value to multilingual
                                old_value = custom_fields[field_type]
                                custom_fields[field_type] = {'': old_value, lang: {"text": text_elem.text}}
                else:
                    # Legacy format - single value
                    if field_elem.text:
                        custom_fields[field_type] = {"und": {"text": field_elem.text}}
          # Parse senses
        senses = []
        for sense_elem in self._find_elements(entry_elem, './/lift:sense'):
            sense_id = sense_elem.get('id')
            sense = self._parse_sense(sense_elem, sense_id)
            senses.append(sense)  # Keep as Sense object, don't convert to dict
        
        # Parse entry-level traits (like morph-type, academic-domain)
        morph_type = None
        academic_domain = None
        for trait_elem in self._find_elements(entry_elem, './/lift:trait', './/trait'):
            trait_name = trait_elem.get('name')
            trait_value = trait_elem.get('value')
            if trait_name == 'morph-type' and trait_value:
                morph_type = trait_value
            elif trait_name == 'academic-domain' and trait_value:
                academic_domain = trait_value
        
        date_created = entry_elem.get('dateCreated')
        date_modified = entry_elem.get('dateModified')
        # Create and return Entry object
        entry = Entry(
            id_=entry_id,
            date_created=date_created,
            date_modified=date_modified,
            lexical_unit=lexical_unit,
            citations=citations,
            pronunciations=pronunciations,
            variants=variants,
            grammatical_info=grammatical_info,
            morph_type=morph_type,  # Add morph_type
            academic_domain=academic_domain,  # Add academic_domain
            relations=relations,
            etymologies=etymologies,
            notes=notes,
            custom_fields=custom_fields,
            senses=senses,
            homograph_number=homograph_number
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
                glosses[lang] = {"text": text_elem.text}
        
        # Parse definitions
        definitions = {}
        for def_elem in self._find_elements(sense_elem, './/lift:definition'):
            for form_elem in self._find_elements(def_elem, './/lift:form'):
                lang = form_elem.get('lang')
                text_elem = self._find_element(form_elem, './/lift:text')
                if lang and text_elem is not None and text_elem.text:
                    definitions[lang] = {"text": text_elem.text}
        
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
        
        # Parse sense-level traits (usage-type, domain-type)
        usage_type = []
        domain_type = []
        for trait_elem in self._find_elements(sense_elem, './/lift:trait', './/trait'):
            trait_name = trait_elem.get('name')
            trait_value = trait_elem.get('value')
            if trait_name == 'usage-type' and trait_value:
                usage_type.append(trait_value)
            elif trait_name == 'domain-type' and trait_value:
                domain_type.append(trait_value)
        
        # Parse notes
        notes = {}
        for note_elem in self._find_elements(sense_elem, './/lift:note', './/note'):
            note_type = note_elem.get('type', 'general')
            # Check for multilingual structured format: <note><form lang=...><text>...</text></form></note>
            form_elements = self._find_elements(note_elem, './/lift:form', './/form')

            note_has_content = False
            if form_elements:
                # New structured format with potentially multiple languages
                if note_type not in notes:
                    notes[note_type] = {}
                for form_elem in form_elements:
                    lang = form_elem.get('lang', '')
                    text_elem = self._find_element(form_elem, './/lift:text', './/text')
                    if text_elem is not None and text_elem.text and text_elem.text.strip():
                        notes[note_type][lang] = {"text": text_elem.text}
                        note_has_content = True
            elif note_elem.text and note_elem.text.strip():
                # Legacy format: <note>text</note>
                notes[note_type] = {"und": {"text": note_elem.text}}
                note_has_content = True

            # If a note element exists but has no content, remove it
            if not note_has_content and note_type in notes:
                del notes[note_type]

        # Final normalization: ensure all note values are nested dicts
        for note_type in list(notes.keys()):
            if isinstance(notes[note_type], str):
                notes[note_type] = {"und": {"text": notes[note_type]}}
            elif isinstance(notes[note_type], dict):
                notes[note_type] = self._normalize_multilingual_dict(notes[note_type])
        
        # Create and return Sense object
        return Sense(
            id_=sense_id,
            glosses=glosses,
            definitions=definitions,
            examples=examples,
            relations=relations,
            grammatical_info=grammatical_info,
            usage_type=usage_type,
            domain_type=domain_type,
            notes=notes
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
        
        # Add dateCreated and dateModified if present
        if entry.date_created:
            entry_elem.set('dateCreated', entry.date_created)
        if entry.date_modified:
            entry_elem.set('dateModified', entry.date_modified)

        # Add homograph number if present (using 'order' attribute per LIFT specification)
        if entry.homograph_number is not None:
            entry_elem.set('order', str(entry.homograph_number))
        
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
            # Output all languages in form and gloss as nested dicts
            if etymology.form:
                for lang, text in etymology.form.items():
                    form_elem = ET.SubElement(etymology_elem, '{' + self.NSMAP['lift'] + '}form')
                    form_elem.set('lang', lang)
                    text_elem = ET.SubElement(form_elem, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                    text_elem.text = text
            if etymology.gloss:
                for lang, text in etymology.gloss.items():
                    gloss_elem = ET.SubElement(etymology_elem, '{' + self.NSMAP['lift'] + '}gloss')
                    gloss_elem.set('lang', lang)
                    text_elem = ET.SubElement(gloss_elem, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
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
            pron_elem.set('writing-system', writing_system)
            pron_elem.set('value', value)
        
        # Add variant forms
        for variant in entry.variants:
            variant_elem = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}variant')
            # Output all languages in variant.form as nested dicts
            variant_type = getattr(variant, 'type', None)
            if variant_type:
                variant_elem.set('type', variant_type)
            if hasattr(variant, 'form') and isinstance(variant.form, dict):
                for lang, text in variant.form.items():
                    form = ET.SubElement(variant_elem, '{' + self.NSMAP['lift'] + self.ELEM_FORM)
                    form.set('lang', lang)
                    text_elem = ET.SubElement(form, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                    text_elem.text = text
            elif isinstance(variant, dict):
                for lang, text in variant.items():
                    if lang != 'type':
                        form = ET.SubElement(variant_elem, '{' + self.NSMAP['lift'] + self.ELEM_FORM)
                        form.set('lang', lang)
                        text_elem = ET.SubElement(form, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                        text_elem.text = text
        
        # Add grammatical info
        if entry.grammatical_info:
            gram_info = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}grammatical-info')
            # If grammatical_info is a dict, extract the part_of_speech or join values
            if isinstance(entry.grammatical_info, dict):
                # Prefer 'part_of_speech' key if present, else join all values
                value: str | None = entry.grammatical_info['part_of_speech'] if 'part_of_speech' in entry.grammatical_info else None
                if value is None:
                    value = ','.join(str(v) for v in entry.grammatical_info.values())
                gram_info.set('value', value)
            else:
                gram_info.set('value', str(entry.grammatical_info))
        
        # Add morph-type trait if present (preserve LIFT data)
        if hasattr(entry, 'morph_type') and entry.morph_type:
            trait_elem = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}trait')
            trait_elem.set('name', 'morph-type')
            trait_elem.set('value', entry.morph_type)
        
        # Add relations
        for relation in entry.relations:
            relation_elem = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}relation')
            # Handle both Relation objects and dictionaries
            if hasattr(relation, 'type') and hasattr(relation, 'ref'):
                relation_elem.set('type', relation.type)
                relation_elem.set('ref', relation.ref)
                
                # Add traits if present
                if hasattr(relation, 'traits') and relation.traits:
                    for trait_name, trait_value in relation.traits.items():
                        trait_elem = ET.SubElement(relation_elem, '{' + self.NSMAP['lift'] + '}trait')
                        trait_elem.set('name', trait_name)
                        trait_elem.set('value', trait_value)
                        
            elif isinstance(relation, dict):
                # Fallback for dictionary format
                relation_elem.set('type', relation.get('type', 'unspecified'))
                relation_elem.set('ref', relation.get('ref', ''))
                
                # Add traits from dictionary format if present
                if 'traits' in relation and relation['traits']:
                    for trait_name, trait_value in relation['traits'].items():
                        trait_elem = ET.SubElement(relation_elem, '{' + self.NSMAP['lift'] + '}trait')
                        trait_elem.set('name', trait_name)
                        trait_elem.set('value', trait_value)
            else:
                # Default fallback
                relation_elem.set('type', 'unspecified')
                relation_elem.set('ref', '')
        
        # Add notes
        for note_type, note_content in entry.notes.items():
            note_elem = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}note')
            note_elem.set('type', note_type)
            
            # Check if this is the new structured format (dict of languages) or legacy format (string)
            if isinstance(note_content, dict):
                # New format: Create form elements for each language
                for lang, text in note_content.items():
                    form_elem = ET.SubElement(note_elem, '{' + self.NSMAP['lift'] + self.ELEM_FORM)
                    form_elem.set('lang', lang)
                    text_elem = ET.SubElement(form_elem, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                    text_elem.text = text
            else:
                # Legacy format: Direct text content
                note_elem.text = note_content
        
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
                sense = sense_item
            sense_elem = ET.SubElement(entry_elem, '{' + self.NSMAP['lift'] + '}sense')
            if sense.id:
                sense_elem.set('id', sense.id)
            # Add glosses (multitext)
            for lang, val in sense.glosses.items():
                gloss_elem = ET.SubElement(sense_elem, '{' + self.NSMAP['lift'] + '}gloss')
                gloss_elem.set('lang', lang)
                text_elem = ET.SubElement(gloss_elem, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                if isinstance(val, dict):
                    text_elem.text = val.get('text', '')
                else:
                    text_elem.text = str(val)
            # Add definitions (multitext)
            if sense.definitions:
                def_elem = ET.SubElement(sense_elem, '{' + self.NSMAP['lift'] + '}definition')
                for lang, val in sense.definitions.items():
                    form = ET.SubElement(def_elem, '{' + self.NSMAP['lift'] + self.ELEM_FORM)
                    form.set('lang', lang)
                    text_elem = ET.SubElement(form, '{' + self.NSMAP['lift'] + self.ELEM_TEXT)
                    if isinstance(val, dict):
                        text_elem.text = val.get('text', '')
                    else:
                        text_elem.text = str(val)
            
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
            
            # Add sense-level traits (usage-type, domain-type)
            if sense.usage_type:
                for usage_value in sense.usage_type:
                    trait_elem = ET.SubElement(sense_elem, '{' + self.NSMAP['lift'] + '}trait')
                    trait_elem.set('name', 'usage-type')
                    trait_elem.set('value', usage_value)
            
            if sense.domain_type:
                for domain_value in sense.domain_type:
                    trait_elem = ET.SubElement(sense_elem, '{' + self.NSMAP['lift'] + '}trait')
                    trait_elem.set('name', 'domain-type')
                    trait_elem.set('value', domain_value)
            
            # Add relations
            for relation in sense.relations:
                relation_elem = ET.SubElement(sense_elem, '{' + self.NSMAP['lift'] + '}relation')
                relation_elem.set('type', relation.get('type', 'unspecified'))
                relation_elem.set('ref', relation.get('ref', ''))
        
        return entry_elem

    def _parse_multilingual_content(self, element: ET.Element, element_types: List[str]) -> Dict[str, str]:
        """
        Parse multilingual content from label and description elements.
        
        Args:
            element: Parent element to search in
            element_types: List of element types to search for (e.g., ['label', 'description'])
            
        Returns:
            Dictionary mapping language codes to text content
        """
        content = {}
        
        for element_type in element_types:
            # Find all elements of this type
            for content_elem in self._find_elements(element, f'./lift:{element_type}', f'./{element_type}'):
                # Check for direct lang attribute and text
                lang = content_elem.get('lang')
                if lang and content_elem.text and content_elem.text.strip():
                    content[lang] = content_elem.text.strip()
                    continue
                
                # Look for form/text structure
                for form_elem in self._find_elements(content_elem, './lift:form', './form'):
                    form_lang = form_elem.get('lang')
                    if form_lang:
                        text_elem = self._find_element(form_elem, './lift:text', './text')
                        if text_elem is not None and text_elem.text and text_elem.text.strip():
                            content[form_lang] = text_elem.text.strip()
        
        return content

    def _parse_range_element_full(self, elem: ET.Element, element_id: str) -> Dict[str, Any]:
        """
        Parse a range element with full feature support.
        
        Args:
            elem: Element representing a range element
            element_id: ID of the element
            
        Returns:
            Dictionary containing range element data
        """
        element_data = {
            'id': element_id,
            'guid': elem.get('guid', ''),
            'value': elem.get('value', '') or element_id,
            'abbrev': '',
            'description': {},
            'children': [],
            'traits': {}
        }
        
        # Parse multilingual labels and descriptions
        element_data['description'] = self._parse_multilingual_content(elem, ['label', 'description'])
        
        # Parse abbreviation (handle LIFT form structure)
        abbrev_elem = self._find_element(elem, './lift:abbrev', './abbrev')
        if abbrev_elem is not None:
            # First try direct text content
            if abbrev_elem.text and abbrev_elem.text.strip():
                element_data['abbrev'] = abbrev_elem.text.strip()
            else:
                # Try form/text structure
                for form_elem in self._find_elements(abbrev_elem, './lift:form', './form'):
                    text_elem = self._find_element(form_elem, './lift:text', './text')
                    if text_elem is not None and text_elem.text and text_elem.text.strip():
                        element_data['abbrev'] = text_elem.text.strip()
                        break
        
        # Parse traits (name-value pairs)
        for trait_elem in self._find_elements(elem, './lift:trait', './trait'):
            trait_name = trait_elem.get('name')
            trait_value = trait_elem.get('value')
            if trait_name:
                element_data['traits'][trait_name] = trait_value or ''
        
        return element_data
        

    def extract_variant_types_from_traits(self, lift_xml_string: str) -> List[Dict[str, Any]]:
        """
        Extract all unique variant types from <trait> elements in variant forms.
        
        This extracts the 'type' traits from all variant elements in the LIFT file,
        which represent the actual variant types used in the document rather than
        using the standard ranges.
        
        Args:
            lift_xml_string: LIFT XML string
            
        Returns:
            List of variant type objects in the format expected by the range API
        """
        self.logger.info("Extracting variant types from traits in LIFT file")
        try:
            root = ET.fromstring(lift_xml_string)
            # Find all variant elements and extract their types
            variant_types: set[str] = set()
            
            # Use both namespaced and non-namespaced XPath for compatibility
            variant_elems = self._find_elements(root, './/lift:variant', './/variant')
            
            for variant_elem in variant_elems:
                # Extract the type attribute directly from variant element
                variant_type = variant_elem.get('type')
                if variant_type and variant_type.strip():
                    variant_types.add(variant_type.strip())
                
                # Also look for trait elements that might indicate variant types
                for trait_elem in self._find_elements(variant_elem, './/lift:trait', './/trait'):
                    trait_name = trait_elem.get('name')
                    trait_value = trait_elem.get('value')
                    if trait_name == 'type' and trait_value and trait_value.strip():
                        variant_types.add(trait_value.strip())
            
            # Format the results as expected by the ranges API
            result: List[Dict[str, Any]] = []
            for variant_type in sorted(variant_types):
                # Create a standardized structure for each variant type
                result.append({
                    'id': variant_type,
                    'value': variant_type,
                    'abbrev': variant_type[:3].lower(),  # Simple abbreviation
                    'description': {'en': f'{variant_type} variant'}
                })
                
            self.logger.info(f"Extracted {len(result)} variant types from LIFT file")
            return result
            
        except Exception as e:
            self.logger.error(f"Error extracting variant types from LIFT: {e}", exc_info=True)
            return []
            



    def extract_variant_types_from_traits(self, lift_xml_string: str) -> List[Dict[str, Any]]:
        """
        Extract all unique variant types from <trait> elements in variant forms.
        
        This extracts the 'type' traits from all variant elements in the LIFT file,
        which represent the actual variant types used in the document rather than
        using the standard ranges.
        
        Args:
            lift_xml_string: LIFT XML string
            
        Returns:
            List of variant type objects in the format expected by the range API
        """
        self.logger.info("Extracting variant types from traits in LIFT file")
        try:
            root = ET.fromstring(lift_xml_string)
            # Find all variant elements and extract their types
            variant_types: set[str] = set()
            
            # Use both namespaced and non-namespaced XPath for compatibility
            variant_elems = self._find_elements(root, './/lift:variant', './/variant')
            
            for variant_elem in variant_elems:
                # Extract the type attribute directly from variant element
                variant_type = variant_elem.get('type')
                if variant_type and variant_type.strip():
                    variant_types.add(variant_type.strip())
                
                # Also look for trait elements that might indicate variant types
                for trait_elem in self._find_elements(variant_elem, './/lift:trait', './/trait'):
                    trait_name = trait_elem.get('name')
                    trait_value = trait_elem.get('value')
                    if trait_name == 'type' and trait_value and trait_value.strip():
                        variant_types.add(trait_value.strip())
            
            # Format the results as expected by the ranges API
            result: List[Dict[str, Any]] = []
            for variant_type in sorted(variant_types):
                # Create a standardized structure for each variant type
                result.append({
                    'id': variant_type,
                    'value': variant_type,
                    'abbrev': variant_type[:3].lower(),  # Simple abbreviation
                    'description': {'en': f'{variant_type} variant'}
                })
                
            self.logger.info(f"Extracted {len(result)} variant types from LIFT file")
            return result
            
        except Exception as e:
            self.logger.error(f"Error extracting variant types from LIFT: {e}", exc_info=True)
            return []
            

    def extract_language_codes_from_file(self, xml_string: str) -> List[str]:
        """
        Extract all unique language codes used in the LIFT file.
        
        This scans all elements with 'lang' attributes to find the actual 
        language codes used in the project, rather than using a predefined list.
        
        Args:
            xml_string: LIFT XML string
            
        Returns:
            List of unique language codes found in the LIFT file
        """
        self.logger.info("Extracting language codes from LIFT file")
        try:
            root = ET.fromstring(xml_string)
            # Find all elements with lang attributes
            language_codes: set[str] = set()
            
            # Function to collect lang attributes from any element
            def collect_lang_attrs(element: ET.Element) -> None:
                lang = element.get('lang')
                if lang and lang.strip():
                    language_codes.add(lang.strip())
                for child in element:
                    collect_lang_attrs(child)
            
            # Traverse the XML tree
            collect_lang_attrs(root)
            
            # Always include seh-fonipa for IPA pronunciations if not already found
            if 'seh-fonipa' not in language_codes:
                language_codes.add('seh-fonipa')
                
            self.logger.info(f"Extracted {len(language_codes)} language codes from LIFT file")
            return sorted(list(language_codes))
            
        except Exception as e:
            self.logger.error(f"Error extracting language codes from LIFT: {e}", exc_info=True)
            # Return a minimal default set
            return ['seh-fonipa']


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
        
        # Parse range labels and descriptions
        range_data['description'] = self._parse_multilingual_content(range_elem, ['label', 'description'])
        
        # Check if this range uses parent attributes for hierarchy
        # Look for ANY range-element with a parent attribute, including nested ones
        has_parent_attributes = False
        for elem in self._find_elements(range_elem, './/lift:range-element', './/range-element'):
            if elem.get('parent'):
                has_parent_attributes = True
                break
        
        if has_parent_attributes:
            # Handle parent-attribute based hierarchy
            range_data['values'] = self._parse_parent_based_hierarchy(range_elem, range_id)
        else:
            # Handle nested XML hierarchy
            range_data['values'] = self._parse_nested_hierarchy(range_elem, range_id)
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
            'parent': elem.get('parent', ''),  # Add parent attribute parsing
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
        
        # Parse element labels and descriptions (handle LIFT form structure)
        element_data['description'] = self._parse_multilingual_content(elem, ['label', 'description'])
        
        # Parse child elements (recursive, direct children only)
        for child_elem in self._find_elements(elem, './lift:range-element', './range-element'):
            child_data = self._parse_range_element(child_elem)
            element_data['children'].append(child_data)
        
        return element_data

    def _parse_parent_based_hierarchy(self, range_elem: ET.Element, range_id: str) -> List[Dict[str, Any]]:
        """
        Parse hierarchy using parent attributes (flat structure with parent references).
        
        Args:
            range_elem: Range element containing range-elements with parent attributes
            range_id: ID of the range
            
        Returns:
            List of root elements with nested children
        """
        # Collect all elements (including nested ones)
        all_elements = {}
        parent_child_map = {}
        
        for value_elem in self._find_elements(range_elem, './/lift:range-element', './/range-element'):
            value_id = value_elem.get('id', '')
            parent_id = value_elem.get('parent', '')
            
            # Normalize orthographic -> spelling for variant types
            if range_id in ('variant-type', 'variant-types') and value_id == 'orthographic':
                value_id = 'spelling'
                
            value = self._parse_range_element_full(value_elem, value_id)
            all_elements[value_id] = value
            
            # Track parent-child relationships
            if parent_id:
                if parent_id not in parent_child_map:
                    parent_child_map[parent_id] = []
                parent_child_map[parent_id].append(value_id)
        
        # Build hierarchical structure recursively
        built = set()  # Track which elements have had their children built
        
        def build_children(element_id: str) -> None:
            """Recursively build children for an element."""
            if element_id in built or element_id not in parent_child_map:
                return
                
            built.add(element_id)
            element = all_elements[element_id]
            
            for child_id in parent_child_map[element_id]:
                if child_id in all_elements:
                    child_element = all_elements[child_id]
                    element['children'].append(child_element)
                    # Recursively build children for this child
                    build_children(child_id)
        
        # Build all hierarchical relationships
        for element_id in all_elements:
            build_children(element_id)
        
        # Find root elements (those with no parent or parent not in our set)
        root_elements = []
        for element_id, element in all_elements.items():
            is_root = True
            for parent_id, children in parent_child_map.items():
                if element_id in children and parent_id in all_elements:
                    is_root = False
                    break
            
            if is_root:
                root_elements.append(element)
        
        return root_elements

    def _parse_nested_hierarchy(self, range_elem: ET.Element, range_id: str) -> List[Dict[str, Any]]:
        """
        Parse hierarchy using nested XML structure (parent-child via nesting).
        
        Args:
            range_elem: Range element containing nested range-elements
            range_id: ID of the range
            
        Returns:
            List of top-level elements with nested children
        """
        root_elements = []
        
        # Only get direct children, not all descendants
        for value_elem in self._find_elements(range_elem, './lift:range-element', './range-element'):
            value_id = value_elem.get('id', '')
            
            # Normalize orthographic -> spelling for variant types
            if range_id in ('variant-type', 'variant-types') and value_id == 'orthographic':
                value_id = 'spelling'
            
            # Parse the element and its children recursively
            value = self._parse_range_element(value_elem)
            root_elements.append(value)
        
        return root_elements

    def _parse_multilingual_content(self, element: ET.Element, element_types: List[str]) -> Dict[str, str]:
        """
        Parse multilingual content from label and description elements.
        
        Args:
            element: Parent element to search in
            element_types: List of element types to search for (e.g., ['label', 'description'])
            
        Returns:
            Dictionary mapping language codes to text content
        """
        content = {}
        
        for element_type in element_types:
            # Find all elements of this type
            for content_elem in self._find_elements(element, f'./lift:{element_type}', f'./{element_type}'):
                # Check for direct lang attribute and text
                lang = content_elem.get('lang')
                if lang and content_elem.text and content_elem.text.strip():
                    content[lang] = content_elem.text.strip()
                    continue
                
                # Look for form/text structure
                for form_elem in self._find_elements(content_elem, './lift:form', './form'):
                    form_lang = form_elem.get('lang')
                    if form_lang:
                        text_elem = self._find_element(form_elem, './lift:text', './text')
                        if text_elem is not None and text_elem.text and text_elem.text.strip():
                            content[form_lang] = text_elem.text.strip()
        
        return content

    def _parse_range_element_full(self, elem: ET.Element, element_id: str) -> Dict[str, Any]:
        """
        Parse a range element with full feature support.
        
        Args:
            elem: Element representing a range element
            element_id: ID of the element
            
        Returns:
            Dictionary containing range element data
        """
        element_data = {
            'id': element_id,
            'guid': elem.get('guid', ''),
            'value': elem.get('value', '') or element_id,
            'abbrev': '',
            'description': {},
            'children': [],
            'traits': {}
        }
        
        # Parse multilingual labels and descriptions
        element_data['description'] = self._parse_multilingual_content(elem, ['label', 'description'])
        
        # Parse abbreviation (handle LIFT form structure)
        abbrev_elem = self._find_element(elem, './lift:abbrev', './abbrev')
        if abbrev_elem is not None:
            # First try direct text content
            if abbrev_elem.text and abbrev_elem.text.strip():
                element_data['abbrev'] = abbrev_elem.text.strip()
            else:
                # Try form/text structure
                for form_elem in self._find_elements(abbrev_elem, './lift:form', './form'):
                    text_elem = self._find_element(form_elem, './lift:text', './text')
                    if text_elem is not None and text_elem.text and text_elem.text.strip():
                        element_data['abbrev'] = text_elem.text.strip()
                        break
        
        # Parse traits (name-value pairs)
        for trait_elem in self._find_elements(elem, './lift:trait', './trait'):
            trait_name = trait_elem.get('name')
            trait_value = trait_elem.get('value')
            if trait_name:
                element_data['traits'][trait_name] = trait_value or ''
        
        return element_data

    def extract_variant_types_from_traits(self, lift_xml_string: str) -> List[Dict[str, Any]]:
        """
        Extract all unique variant types from <trait> elements in variant forms.
        
        This extracts the 'type' traits from all variant elements in the LIFT file,
        which represent the actual variant types used in the document rather than
        using the standard ranges.
        
        Args:
            lift_xml_string: LIFT XML string
            
        Returns:
            List of variant type objects in the format expected by the range API
        """
        self.logger.info("Extracting variant types from traits in LIFT file")
        try:
            root = ET.fromstring(lift_xml_string)
            # Find all variant elements and extract their types
            variant_types: set[str] = set()
            
            # Use both namespaced and non-namespaced XPath for compatibility
            variant_elems = self._find_elements(root, './/lift:variant', './/variant')
            
            for variant_elem in variant_elems:
                # Extract the type attribute directly from variant element
                variant_type = variant_elem.get('type')
                if variant_type and variant_type.strip():
                    variant_types.add(variant_type.strip())
                
                # Also look for trait elements that might indicate variant types
                for trait_elem in self._find_elements(variant_elem, './/lift:trait', './/trait'):
                    trait_name = trait_elem.get('name')
                    trait_value = trait_elem.get('value')
                    if trait_name == 'type' and trait_value and trait_value.strip():
                        variant_types.add(trait_value.strip())
            
            # Format the results as expected by the ranges API
            result: List[Dict[str, Any]] = []
            for variant_type in sorted(variant_types):
                # Create a standardized structure for each variant type
                result.append({
                    'id': variant_type,
                    'value': variant_type,
                    'abbrev': variant_type[:3].lower(),  # Simple abbreviation
                    'description': {'en': f'{variant_type} variant'}
                })
                
            self.logger.info(f"Extracted {len(result)} variant types from LIFT file")
            return result
            
        except Exception as e:
            self.logger.error(f"Error extracting variant types from LIFT: {e}", exc_info=True)
            return []
            
    def extract_language_codes_from_file(self, xml_string: str) -> List[str]:
        """
        Extract all unique language codes used in the LIFT file.
        
        This scans all elements with 'lang' attributes to find the actual 
        language codes used in the project, rather than using a predefined list.
        
        Args:
            xml_string: LIFT XML string
            
        Returns:
            List of unique language codes found in the LIFT file
        """
        self.logger.info("Extracting language codes from LIFT file")
        try:
            root = ET.fromstring(xml_string)
            # Find all elements with lang attributes
            language_codes: set[str] = set()
            
            # Function to collect lang attributes from any element
            def collect_lang_attrs(element: ET.Element) -> None:
                lang = element.get('lang')
                if lang and lang.strip():
                    language_codes.add(lang.strip())
                for child in element:
                    collect_lang_attrs(child)
            
            # Traverse the XML tree
            collect_lang_attrs(root)
            
            # Always include seh-fonipa for IPA pronunciations if not already found
            if 'seh-fonipa' not in language_codes:
                language_codes.add('seh-fonipa')
                
            self.logger.info(f"Extracted {len(language_codes)} language codes from LIFT file")
            return sorted(list(language_codes))
            
        except Exception as e:
            self.logger.error(f"Error extracting language codes from LIFT: {e}", exc_info=True)
            # Return a minimal default set
            return ['seh-fonipa']
