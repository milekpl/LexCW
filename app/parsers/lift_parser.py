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
        entries = []
        for entry_elem in self._find_elements(root, './/lift:entry'):
            try:
                entry = self._parse_entry(entry_elem)
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

        for entry in entries:
            attrib = {'id': entry.id} if entry.id else {}
            if entry.date_created:
                attrib['dateCreated'] = entry.date_created
            if entry.date_modified:
                attrib['dateModified'] = entry.date_modified
            # Use homograph_number for 'order' attribute if present
            if entry.homograph_number is not None:
                attrib['order'] = str(entry.homograph_number)
            elif entry.order is not None:
                attrib['order'] = str(entry.order)

            entry_elem = ET.SubElement(root, f"{{{self.NSMAP['lift']}}}entry", attrib)
            
            # Lexical unit
            if entry.lexical_unit:
                lu = ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}lexical-unit")
                for lang, text in entry.lexical_unit.items():
                    form = ET.SubElement(lu, f"{{{self.NSMAP['lift']}}}form", {'lang': lang})
                    text_val = text['text'] if isinstance(text, dict) else text
                    ET.SubElement(form, f"{{{self.NSMAP['lift']}}}text").text = str(text_val)

            # Senses
            for sense in entry.senses:
                s_attrib = {'id': sense.id} if sense.id else {}
                sense_elem = ET.SubElement(entry_elem, f"{{{self.NSMAP['lift']}}}sense", s_attrib)
                
                if sense.grammatical_info:
                    ET.SubElement(sense_elem, f"{{{self.NSMAP['lift']}}}grammatical-info", {'value': sense.grammatical_info})
                
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
            variants=[self._parse_variant(v) for v in self._find_elements(elem, './lift:variant')],
            grammatical_info=self._get_attr(elem, './lift:grammatical-info', 'value'),
            traits=self._parse_traits(elem),
            relations=[self._parse_relation(r) for r in self._find_elements(elem, './lift:relation')],
            etymologies=[self._parse_etymology(e) for e in self._find_elements(elem, './lift:etymology')],
            notes=self._parse_notes(elem),
            custom_fields=self._parse_custom_fields(elem),
            senses=[self._parse_sense(s) for s in self._find_elements(elem, './lift:sense')],
            annotations=[self._parse_annotation(a) for a in self._find_elements(elem, './lift:annotation')]
        )

    def _parse_pronunciations(self, parent: ET.Element) -> Dict[str, str]:
        """Parse pronunciation elements."""
        result = {}
        for pron in self._find_elements(parent, './lift:pronunciation'):
            # LIFT pronunciation can have multiple forms
            forms = self._parse_multitext(pron, '.', flatten=True)
            result.update(forms)
        return result

    def _parse_variant(self, elem: ET.Element) -> Variant:
        """Parse variant element."""
        return Variant(
            type=elem.get('type', ''),
            ref=elem.get('ref', ''),
            form=self._parse_multitext(elem, '.', flatten=True),
            traits=self._parse_traits(elem)
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
        return Etymology(
            type=elem.get('type', ''),
            source=elem.get('source', ''),
            form=self._parse_multitext(elem, '.', flatten=True),
            gloss=self._parse_multitext(elem, '.', form_tag='lift:gloss', flatten=True),
            comment=self._parse_multitext(elem, './lift:field[@type="comment"]'),
            custom_fields=self._parse_custom_fields(elem)
        )

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

    def _parse_traits(self, parent: ET.Element) -> Dict[str, str]:
        """Parse trait elements."""
        if parent is None:
            return {}
        return {t.get('name'): t.get('value') for t in self._find_elements(parent, './lift:trait') 
                if t.get('name') and t.get('value')}

    def _parse_custom_fields(self, parent: ET.Element) -> Dict[str, Dict]:
        """Parse field elements."""
        fields = {}
        for field in self._find_elements(parent, './lift:field'):
            if field_type := field.get('type'):
                fields[field_type] = self._parse_text_content(field)
        return fields

    def _parse_sense(self, elem: ET.Element) -> Sense:
        """Parse sense element."""
        return Sense(
            id_=elem.get('id'),
            glosses=self._parse_multitext(elem, '.', form_tag='lift:gloss', flatten=True),
            definitions=self._parse_multitext(elem, './lift:definition', flatten=True),
            examples=[self._parse_example(e) for e in self._find_elements(elem, './lift:example')],
            relations=[self._parse_relation_dict(r) for r in self._find_elements(elem, './lift:relation')],
            grammatical_info=self._get_attr(elem, './lift:grammatical-info', 'value'),
            grammatical_traits=self._parse_traits(self._find_element(elem, './lift:grammatical-info')),
            usage_type=[v for t in self._find_elements(elem, './lift:trait[@name="usage-type"]') 
                       if (v := t.get('value'))],
            domain_type=self._get_attr(elem, './lift:trait[@name="domain-type"]', 'value'),
            semantic_domains=[v for t in self._find_elements(elem, './lift:trait[@name="semantic-domain-ddp4"]') 
                            if (v := t.get('value'))],
            notes=self._parse_notes(elem),
            traits={t.get('name'): t.get('value') for t in self._find_elements(elem, './lift:trait') 
                   if t.get('name') not in {'usage-type', 'domain-type', 'semantic-domain-ddp4'}},
            annotations=[self._parse_annotation(a) for a in self._find_elements(elem, './lift:annotation')],
            subsenses=[self._parse_sense(s) for s in self._find_elements(elem, './lift:subsense')]
        )

    def _parse_relation_dict(self, elem: ET.Element) -> Dict:
        """Parse relation into dict for sense/subsense."""
        return {'type': elem.get('type', ''), 'ref': elem.get('ref', '')}

    def _parse_example(self, elem: ET.Element) -> Example:
        """Parse example element."""
        return Example(
            id_=elem.get('id'),
            form=self._parse_multitext(elem, '.'),
            translations=self._parse_multitext(elem, './lift:translation'),
            source=elem.get('source'),
            note=self._parse_multitext(elem, './lift:field[@type="note"]'),
            custom_fields=self._parse_custom_fields(elem)
        )

    def _parse_annotation(self, elem: ET.Element) -> Dict[str, Any]:
        """Parse annotation element."""
        return {
            'name': elem.get('name'),
            'value': elem.get('value'),
            'who': elem.get('who'),
            'when': elem.get('when'),
            'content': self._parse_multitext(elem, '.')
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
                return {}

    def _parse_ranges(self, root: ET.Element) -> Dict[str, Dict[str, Any]]:
        """Parse all ranges from root."""
        ranges = {}
        for range_elem in self._find_elements(root, './/lift:range'):
            if range_id := range_elem.get('id'):
                ranges[range_id] = self._parse_range(range_elem)
        return ranges

    def _find(self, parent: ET.Element, xpath: str, single: bool = False) -> Any:
        """Namespace-aware finder with fallback to non-namespaced search."""
        result = parent.find(xpath, self.NSMAP) if single else parent.findall(xpath, self.NSMAP)
        if (result is None if single else not result):
            plain_xpath = xpath.replace('lift:', '')
            result = parent.find(plain_xpath) if single else parent.findall(plain_xpath)
            if (result is None if single else not result) and 'range-element' in xpath:
                 # Debug only for missing range elements
                 self.logger.debug(f"MISSING: {xpath} (plain: {plain_xpath}) in <{parent.tag}>")
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
            'descriptions': self._parse_multitext(elem, './lift:description')
        }

    def _parse_range_hierarchy(self, parent: ET.Element, range_id: str) -> List[Dict[str, Any]]:
        """Parse range hierarchy (parent-based or nested)."""
        if any(e.get('parent') for e in self._find_elements(parent, './/lift:range-element')):
            return self._parse_parent_based(parent, range_id)
        return [self._parse_range_element(e, range_id) for e in self._find_elements(parent, './lift:range-element')]

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
            
        return {
            'id': elem_id,
            'guid': elem.get('guid', ''),
            'value': elem.get('value', '') or elem_id,
            'parent': elem.get('parent', ''),
            'abbrev': self._parse_abbrev(elem),
            'abbrevs': self._parse_abbrevs(elem),
            'labels': self._parse_multitext(elem, './lift:label'),
            'descriptions': self._parse_multitext(elem, './lift:description'),
            'children': [],
            'traits': {t.get('name'): t.get('value') for t in self._find_elements(elem, './lift:trait') if t.get('name')},
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
                    result[form.get('lang', 'und')] = text_elem.text.strip()
        return result

    def _parse_abbrev(self, elem: ET.Element) -> str:
        """Parse abbreviation (direct or nested)."""
        abbrev = self._find_element(elem, './lift:abbrev')
        if abbrev is not None:
            if abbrev.text and abbrev.text.strip():
                return abbrev.text.strip()
            return next((v for v in self._parse_multitext(abbrev, '.').values() if v), '')
        return ''

    def _parse_abbrevs(self, elem: ET.Element) -> Dict[str, str]:
        """Parse all abbreviation variants."""
        abbrev = self._find_element(elem, './lift:abbrev')
        if abbrev is not None:
            return self._parse_multitext(abbrev, '.')
        return {}

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
    