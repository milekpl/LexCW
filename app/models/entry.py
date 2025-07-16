"""
Entry model representing a dictionary entry in LIFT format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from app.models.base import BaseModel
from app.utils.exceptions import ValidationError

if TYPE_CHECKING:
    from app.models.sense import Sense




class Etymology(BaseModel):
    """
    Represents an etymology in a LIFT entry.
    """

    def __init__(self, type: str, source: str, form: Dict[str, str], gloss: Dict[str, str], **kwargs: Any):
        super().__init__(**kwargs)
        self.type: str = type
        self.source: str = source
        self.form: Dict[str, str] = form
        self.gloss: Dict[str, str] = gloss

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result['form'] = self.form
        result['gloss'] = self.gloss
        return result


class Relation(BaseModel):
    """
    Represents a relation to another entry with optional traits.
    """

    def __init__(self, type: str, ref: str, traits: Optional[Dict[str, str]] = None, order: Optional[int] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.type = type
        self.ref = ref
        self.traits = traits or {}
        self.order = order


class Variant(BaseModel):
    """
    Represents a variant form of a lexical unit.
    """

    def __init__(self, form: Dict[str, str], **kwargs: Any):
        super().__init__(**kwargs)
        self.form: Dict[str, str] = form

    def to_dict(self) -> Dict[str, Any]:
        """Convert variant to dictionary with nested objects."""
        result = super().to_dict()
        
        # Convert nested form object
        if hasattr(self.form, 'to_dict'):
            result['form'] = self.form.to_dict()
            
        return result


class Entry(BaseModel):
    """
    Entry model representing a dictionary entry in LIFT format.

    Attributes:
        id: Unique identifier for the entry.
        lexical_unit: Dictionary mapping language codes to lexical unit forms.
        citations: List of citation forms for the entry.
        pronunciations: Dictionary mapping writing system codes to pronunciation forms.
        senses: List of sense objects for the entry.
        grammatical_info: Grammatical information for the entry.
        etymologies: List of etymology objects for the entry.
        relations: List of semantic relations to other entries.
        variants: List of variant forms for the entry.
        notes: Dictionary mapping note types to either simple text (legacy) or language-text mappings (multilingual).
        custom_fields: Dictionary of custom fields for the entry.
        homograph_number: Optional integer identifying the homograph number when entries share the same lexical unit.
    """

    def __init__(self, id_: Optional[str] = None, date_created: Optional[str] = None, date_modified: Optional[str] = None, **kwargs: Any):
        """
        Initialize an entry.

        Args:
            id_: Unique identifier for the entry.
            date_created: ISO8601 string for creation date.
            date_modified: ISO8601 string for last modification date.
            **kwargs: Additional attributes to set on the entry.
        """
        self.date_created: Optional[str] = date_created
        self.date_modified: Optional[str] = date_modified

        # Extract complex structures before calling super to avoid double processing
        senses_data = kwargs.pop('senses', [])
        etymologies_data = kwargs.pop('etymologies', [])
        relations_data = kwargs.pop('relations', [])
        variants_data = kwargs.pop('variants', [])

        # Handle variant_relations if provided (convert to relations)
        variant_relations_data = kwargs.pop('variant_relations', [])

        super().__init__(id_, **kwargs)
        
        # Handle lexical_unit - ensure it's a dictionary
        lexical_unit_raw = kwargs.get('lexical_unit', {})
        if isinstance(lexical_unit_raw, dict):
            self.lexical_unit: Dict[str, str] = lexical_unit_raw
        elif isinstance(lexical_unit_raw, str):
            # Convert string to dict for backward compatibility
            self.lexical_unit: Dict[str, str] = {'en': lexical_unit_raw} if lexical_unit_raw.strip() else {}
        elif isinstance(lexical_unit_raw, list):
            # Handle case where lexical_unit is passed as a list (form processing error)
            # Take the first non-empty item or use default
            if lexical_unit_raw and isinstance(lexical_unit_raw[0], str):
                self.lexical_unit: Dict[str, str] = {'en': lexical_unit_raw[0]} if lexical_unit_raw[0].strip() else {}
            else:
                self.lexical_unit: Dict[str, str] = {}
        else:
            self.lexical_unit: Dict[str, str] = {}
            
        # Handle citations - ensure it's a list of dictionaries
        citations_raw = kwargs.get('citations', [])
        if isinstance(citations_raw, list):
            self.citations: List[Dict[str, Any]] = []
            for citation in citations_raw:
                if isinstance(citation, dict):
                    self.citations.append(citation)
                elif isinstance(citation, str):
                    # Convert string to dict format for default language
                    self.citations.append({'en': citation})
        else:
            self.citations: List[Dict[str, Any]] = []
        
        # Handle pronunciations - ensure it's a dictionary
        pronunciations_raw = kwargs.get('pronunciations', {})
        if isinstance(pronunciations_raw, dict):
            self.pronunciations: Dict[str, str] = pronunciations_raw
        elif isinstance(pronunciations_raw, list):
            # Handle case where pronunciations might be passed as a list
            # Convert list to dict format expected by the LIFT parser
            self.pronunciations: Dict[str, str] = {}
            for item in pronunciations_raw:
                if isinstance(item, dict):
                    # If list contains dict items with .value, .type' pattern
                    if '.value' in item and '.type' in item:
                        self.pronunciations[item['.type']] = item['.value']
                    elif 'value' in item and 'type' in item:
                        self.pronunciations[item['type']] = item['value']
                elif isinstance(item, str):
                    # If list contains string items, use default type
                    self.pronunciations['seh-fonipa'] = item
        else:
            self.pronunciations: Dict[str, str] = {}
            
        self.grammatical_info: Optional[str] = kwargs.get('grammatical_info')
        
        # Handle morphological type with auto-classification if not provided
        self.morph_type: Optional[str] = self._get_or_classify_morph_type(kwargs.get('morph_type'))
        
        # Handle notes - ensure it's a dictionary and preserve nested dicts
        notes_raw = kwargs.get('notes', {})
        if isinstance(notes_raw, dict):
            self.notes = notes_raw
        elif isinstance(notes_raw, list):
            self.notes = {}
        else:
            self.notes = {}

        # Handle custom_fields - ensure it's a dictionary and flatten nested dicts
        custom_fields_raw = kwargs.get('custom_fields', {})
        if isinstance(custom_fields_raw, dict):
            self.custom_fields: Dict[str, Any] = {
                k: v['text'] if isinstance(v, dict) and 'text' in v and len(v) == 1 else v
                for k, v in custom_fields_raw.items()
            }
        elif isinstance(custom_fields_raw, list):
            self.custom_fields: Dict[str, Any] = {}
        else:
            self.custom_fields: Dict[str, Any] = {}
        self.homograph_number: Optional[int] = kwargs.get('homograph_number')

        # Handle senses
        from app.models.sense import Sense
        self.senses: List[Sense] = []
        for sense_data in senses_data:
            if isinstance(sense_data, dict):
                # Check if ID was explicitly provided
                if 'id' not in sense_data:
                    # Don't auto-generate ID, let validation catch this
                    sense_obj = Sense(**sense_data)
                    sense_obj._has_explicit_id = False
                else:
                    sense_obj = Sense(**sense_data)
                    sense_obj._has_explicit_id = True
                self.senses.append(sense_obj)
            elif isinstance(sense_data, Sense):
                sense_data._has_explicit_id = True  # Assume Sense objects have explicit IDs
                self.senses.append(sense_data)

        # Handle etymologies
        self.etymologies: List[Etymology] = []
        for etymology_data in etymologies_data:
            if isinstance(etymology_data, dict):
                self.etymologies.append(Etymology(**etymology_data))
            elif isinstance(etymology_data, Etymology):
                self.etymologies.append(etymology_data)

        # Handle relations (including converted variant_relations)
        self.relations: List[Relation] = []
        
        # First add regular relations
        for relation_data in relations_data:
            if isinstance(relation_data, dict):
                self.relations.append(Relation(**relation_data))
            elif isinstance(relation_data, Relation):
                self.relations.append(relation_data)
        
        # Convert variant_relations to regular relations with variant-type traits
        for variant_relation_data in variant_relations_data:
            if isinstance(variant_relation_data, dict):
                # Convert variant_relation to a relation with variant-type trait
                relation_dict = {
                    'type': variant_relation_data.get('type', '_component-lexeme'),
                    'ref': variant_relation_data['ref'],
                    'traits': {'variant-type': variant_relation_data.get('variant_type', 'Unspecified Variant')},
                    'order': variant_relation_data.get('order', len(self.relations))
                }
                self.relations.append(Relation(**relation_dict))

        # Handle variants
        self.variants: List[Variant] = []
        for variant_data in variants_data:
            if isinstance(variant_data, dict):
                self.variants.append(Variant(**variant_data))
            elif isinstance(variant_data, Variant):
                self.variants.append(variant_data)

        # Apply part-of-speech inheritance logic
        self._apply_pos_inheritance()

    def validate(self) -> bool:
        """
        Validate the entry using the centralized validation system.

        Returns:
            True if the entry is valid.

        Raises:
            ValidationError: If the entry is invalid.
        """
        from app.services.validation_engine import ValidationEngine
        
        # Use centralized validation system
        engine = ValidationEngine()
        result = engine.validate_entry(self)
        
        if not result.is_valid:
            # Convert ValidationError objects to strings for legacy compatibility
            error_messages = [error.message for error in result.errors]
            raise ValidationError("Entry validation failed", error_messages)
        
        return True

    def _is_valid_id_format(self, id_string: str) -> bool:
        """Check if ID follows valid format pattern."""
        import re
        return bool(re.match(r'^[a-zA-Z0-9_-]+$', id_string))

    def _has_content_or_is_variant(self, sense: Any) -> bool:
        """Check if sense has content (definition/gloss) or is a variant."""
        # Check if it's a variant sense
        if hasattr(sense, 'variant_of') and sense.variant_of:
            return True
        
        # Check if it has definition
        if hasattr(sense, 'definition') and sense.definition:
            return bool(sense.definition.strip()) if isinstance(sense.definition, str) else True
        
        # Check if it has gloss
        if hasattr(sense, 'gloss') and sense.gloss:
            return bool(sense.gloss.strip()) if isinstance(sense.gloss, str) else True
        
        return False

    def _validate_ipa(self, ipa_text: str) -> List[str]:
        """Validate IPA text according to project rules."""
        errors: List[str] = []
        if not ipa_text:
            return errors
        
        # Valid IPA characters for this project
        vowels = 'ɑæɒəɜɪiʊuʌeɛoɔ'
        consonants = 'bdfghjklmnprstwvzðθŋʃʒ'
        length_markers = 'ː'
        stress_markers = 'ˈˌ'
        special_symbols = 'ᵻ'
        valid_chars = vowels + consonants + length_markers + stress_markers + special_symbols + ' .'
        
        # R4.1.2: Check for invalid characters
        for i, char in enumerate(ipa_text):
            if char not in valid_chars:
                errors.append(f"Invalid IPA character: '{char}' at position {i + 1}")
        
        # R4.2.1: Check for double stress markers
        double_stress_patterns = ['ˈˈ', 'ˌˌ', 'ˈˌ', 'ˌˈ']
        for pattern in double_stress_patterns:
            if pattern in ipa_text:
                errors.append("Double stress markers not allowed")
                break
        
        # R4.2.2: Check for double length markers
        if 'ːː' in ipa_text:
            errors.append("Double length markers not allowed")
        
        return errors

    def _is_valid_relation_type(self, relation_type: str) -> bool:
        """Check if relation type is valid."""
        valid_types = {
            "synonym", "antonym", "hypernym", "hyponym", 
            "_component-lexeme", "variant", "compare"
        }
        return relation_type in valid_types

    def add_sense(self, sense: Union[Sense, Dict[str, Any]]) -> None:
        """
        Add a sense to the entry.

        Args:
            sense: Sense to add (can be Sense object or dict).
        """
        from app.models.sense import Sense
        # Handle both Sense objects and dictionaries
        if isinstance(sense, Sense):
            if not sense.id:
                raise ValidationError("Sense must have an ID")
        elif isinstance(sense, dict):
            # Dictionary
            if not sense.get('id'):
                raise ValidationError("Sense must have an ID")
            sense = Sense(**sense)
        else:
            raise ValidationError("Sense must be a Sense object or dictionary")

        self.senses.append(sense)

    def remove_sense(self, sense_id: str) -> bool:
        """
        Remove a sense from the entry.

        Args:
            sense_id: ID of the sense to remove.

        Returns:
            True if the sense was removed, False if it was not found.
        """
        for i, sense in enumerate(self.senses):
            # Handle both Sense objects and dictionaries
            if hasattr(sense, 'id'):
                # Sense object
                if sense.id == sense_id:
                    del self.senses[i]
                    return True
            elif isinstance(sense, dict):
                # Dictionary
                if sense.get('id') == sense_id:
                    del self.senses[i]
                    return True

        return False

    @property
    def headword(self) -> str:
        """
        Get the headword (lexical unit) for display.

        Returns:
            The headword text in the primary language.
        """
        # Default to 'en' if available, otherwise take the first available language
        if 'en' in self.lexical_unit:
            return self.lexical_unit['en']
        elif self.lexical_unit:
            return next(iter(self.lexical_unit.values()))
        return ""

    def variant_relations(self) -> List[Dict[str, Any]]:
        """
        Get variant relations for template access.
        
        Returns:
            List of variant relation dictionaries.
        """
        return self.get_variant_relations()

    def get_lexical_unit(self, lang: Optional[str] = None) -> str:
        """
        Get the lexical unit in the specified language.

        Args:
            lang: Language code to retrieve. If None, returns the first available.

        Returns:
            The lexical unit text in the specified language, or an empty string if not found.
        """
        # If a specific language is requested
        if lang:
            # Return the requested language or empty string if not found
            return self.lexical_unit.get(lang, "")

        # If no specific language is requested, return default
        if self.lexical_unit:
            # Default to primary language if available
            if 'en' in self.lexical_unit:
                return self.lexical_unit['en']
            # Otherwise return first available
            return next(iter(self.lexical_unit.values()))
        return ""

    def get_language_list(self) -> List[str]:
        """
        Get a list of languages available for this entry's lexical unit.

        Returns:
            List of language codes.
        """
        return list(self.lexical_unit.keys())

    def add_relation(self, relation_type: str, target_id: str) -> None:
        """
        Add a semantic relation to the entry.

        Args:
            relation_type: Type of relation (e.g., 'synonym', 'antonym').
            target_id: ID of the target entry.
        """
        self.relations.append(Relation(type=relation_type, ref=target_id))

    def add_etymology(self, etymology_type: str, source: str, form_lang: str, 
                      form_text: str, gloss_lang: str, gloss_text: str) -> None:
        """
        Add an etymology to the entry.

        Args:
            etymology_type: Type of etymology (e.g., 'borrowing', 'inheritance').
            source: Source language or etymological description.
            form_lang: Language code for the etymological form.
            form_text: Text of the etymological form.
            gloss_lang: Language code for the gloss.
            gloss_text: Text of the gloss/meaning.
        """
        form = {"lang": form_lang, "text": form_text}
        gloss = {"lang": gloss_lang, "text": gloss_text}
        etymology = Etymology(type=etymology_type, source=source, form=form, gloss=gloss)
        self.etymologies.append(etymology)

    def add_pronunciation(self, writing_system: str, form: str) -> None:
        """
        Add a pronunciation to the entry.

        Args:
            writing_system: Writing system code (e.g., 'seh-fonipa').
            form: Pronunciation form.
        """
        self.pronunciations[writing_system] = form

    def get_sense_by_id(self, sense_id: str) -> Optional[Any]:
        """
        Get a sense by ID.

        Args:
            sense_id: ID of the sense to get.

        Returns:
            Sense with the given ID, or None if not found.
        """
        for sense in self.senses:
            # Handle both Sense objects and dictionaries
            if hasattr(sense, 'id'):
                # Sense object
                if sense.id == sense_id:
                    return sense
            elif isinstance(sense, dict):
                # Dictionary
                if sense.get('id') == sense_id:
                    return sense

        return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the entry to a dictionary for serialization (round-trip safe).

        Returns:
            Dictionary representation of the entry with computed properties.
        """
        result = super().to_dict()

        # Always include date fields, even if None
        result['date_created'] = self.date_created if hasattr(self, 'date_created') else None
        result['date_modified'] = self.date_modified if hasattr(self, 'date_modified') else None

        # Note: headword is a computed property and should not be included in dict

        # Convert nested objects to dictionaries
        for attr_name in ['senses', 'relations', 'etymologies', 'variants']:
            if attr_name in result and result[attr_name]:
                converted_items = []
                for item in result[attr_name]:
                    if hasattr(item, 'to_dict'):
                        # It's a model object with to_dict method
                        converted_items.append(item.to_dict())
                    else:
                        # It's already a dict
                        converted_items.append(item)
                result[attr_name] = converted_items

        # Add variant relations derived from relations with variant-type traits
        result['variant_relations'] = self.get_variant_relations()

        return result

    def to_template_dict(self) -> Dict[str, Any]:
        """
        Convert the entry to a dictionary for template use, including computed properties.

        Returns:
            Dictionary representation of the entry with computed properties.
        """
        result = self.to_dict()
        
        # Add variant relations derived from relations with variant-type traits
        result['variant_relations'] = self.get_variant_relations()
        
        # Add component relations derived from _component-lexeme relations with complex-form-type traits
        result['component_relations'] = self.get_component_relations()

        return result

    def to_display_dict(self) -> Dict[str, Any]:
        """
        Convert the entry to a dictionary for display, simplifying multilingual fields.

        Returns:
            Dictionary representation of the entry for display.
        """
        result = self.to_dict()
        result['senses'] = [sense.to_display_dict() for sense in self.senses]
        return result

    def get_component_relations(self, dict_service=None) -> List[Dict[str, Any]]:
        """
        Extract component information from _component-lexeme relations with complex-form-type traits.
        These represent relationships where this entry is a subentry/complex form of a main entry.
        
        Args:
            dict_service: DictionaryService instance for enriching component data
        
        Returns:
            List of dictionaries containing component information extracted from relations.
            Each dictionary contains:
            - ref: Reference to the main entry
            - complex_form_type: The complex form type (Compound, Phrase, etc.)
            - is_primary: Whether this is a primary component
            - order: The component order (if present)
            - ref_lexical_unit: Human-readable text from main entry (if found)
            - ref_display_text: Display text from main entry (if found)
        """
        component_relations = []
        
        for relation in self.relations:
            try:
                # Check for _component-lexeme relations with complex-form-type traits
                if (hasattr(relation, 'type') and relation.type == '_component-lexeme' and
                    hasattr(relation, 'traits') and relation.traits and 
                    isinstance(relation.traits, dict) and 'complex-form-type' in relation.traits and
                    hasattr(relation, 'ref') and relation.ref):
                    
                    component_info = {
                        'ref': str(relation.ref),  # Ensure string
                        'complex_form_type': str(relation.traits['complex-form-type']),  # Ensure string
                        'is_primary': relation.traits.get('is-primary') == 'true',
                    }
                    
                    # Include order if available and valid
                    if (hasattr(relation, 'order') and relation.order is not None and 
                        isinstance(relation.order, (int, str))):
                        try:
                            component_info['order'] = int(relation.order)
                        except (ValueError, TypeError):
                            # Skip invalid order values
                            pass
                    
                    # Enrich with main entry information if dict_service is available
                    if dict_service:
                        try:
                            main_entry = dict_service.get_entry(component_info['ref'])
                            if main_entry:
                                # Extract lexical unit for display
                                if hasattr(main_entry, 'lexical_unit'):
                                    if isinstance(main_entry.lexical_unit, dict):
                                        # Multi-language lexical unit - extract first available
                                        for lang in ['en', 'pl', 'cs', 'sk']:
                                            if lang in main_entry.lexical_unit:
                                                component_info['ref_lexical_unit'] = main_entry.lexical_unit[lang]
                                                break
                                        if 'ref_lexical_unit' not in component_info:
                                            first_key = list(main_entry.lexical_unit.keys())[0]
                                            component_info['ref_lexical_unit'] = main_entry.lexical_unit[first_key]
                                    else:
                                        component_info['ref_lexical_unit'] = str(main_entry.lexical_unit)
                                
                                # Create display text with homograph number as subscript if present
                                display_text = component_info.get('ref_lexical_unit', component_info['ref'])
                                if hasattr(main_entry, 'homograph_number') and main_entry.homograph_number:
                                    # Use HTML subscript for consistency with other parts of the UI
                                    display_text += f'<sub style="font-size: 0.8em; color: #6c757d;">{main_entry.homograph_number}</sub>'
                                component_info['ref_display_text'] = display_text
                        except Exception as e:
                            # Log but don't fail - continue without enrichment
                            print(f"[Entry] Warning: Could not enrich component relation {component_info['ref']}: {e}")
                    
                    component_relations.append(component_info)
                    
            except Exception as e:
                # Log but continue processing other relations
                print(f"[Entry] Warning: Error processing component relation: {e}")
        
        # Sort by order if available
        component_relations.sort(key=lambda x: x.get('order', 0))
        
        return component_relations

    def component_relations(self) -> List[Dict[str, Any]]:
        """
        Get component relations for template access.
        Component relations represent relationships where this entry is a subentry/complex form.
        """
        return self.get_component_relations()

    def get_variant_relations(self, dict_service=None) -> List[Dict[str, Any]]:
        """
        Extract variant information from relations with variant-type traits.
        
        Args:
            dict_service: DictionaryService instance for enriching variant data
        
        Returns:
            List of dictionaries containing variant information extracted from relations.
            Each dictionary contains:
            - ref: Reference to the target entry
            - variant_type: The variant type from the trait value
            - type: The relation type
            - order: The relation order (if present)
            - ref_lexical_unit: Human-readable text from target entry (if found)
            - ref_display_text: Display text from target entry (if found)
        """
        variant_relations = []
        
        for relation in self.relations:
            try:
                # Ensure relation has required attributes and they're not None/Undefined
                if (hasattr(relation, 'traits') and relation.traits and 
                    isinstance(relation.traits, dict) and 'variant-type' in relation.traits and
                    hasattr(relation, 'ref') and relation.ref and
                    hasattr(relation, 'type') and relation.type):
                    
                    variant_info = {
                        'ref': str(relation.ref),  # Ensure string
                        'variant_type': str(relation.traits['variant-type']),  # Ensure string
                        'type': str(relation.type),  # Ensure string
                    }
                    
                    # Include order if available and valid
                    if (hasattr(relation, 'order') and relation.order is not None and 
                        isinstance(relation.order, (int, str))):
                        try:
                            variant_info['order'] = int(relation.order)
                        except (ValueError, TypeError):
                            # Skip invalid order values
                            pass
                    
                    # Enrich with target entry information if dict_service is available
                    if dict_service:
                        try:
                            target_entry = dict_service.get_entry(variant_info['ref'])
                            if target_entry:
                                variant_info['ref_lexical_unit'] = target_entry.get_lexical_unit()
                                variant_info['ref_display_text'] = target_entry.get_lexical_unit()
                        except Exception:
                            # If we can't find the target entry, leave it without enrichment
                            # The template will show an error marker for missing targets
                            pass
                        
                    variant_relations.append(variant_info)
            except (AttributeError, TypeError, KeyError) as e:
                # Skip relations that can't be processed
                continue
        
        # Sort by order if available, otherwise by ref
        try:
            variant_relations.sort(key=lambda x: (x.get('order', 999), x.get('ref_lexical_unit', x['ref'])))
        except (TypeError, KeyError):
            # If sorting fails, just return unsorted
            pass
        
        return variant_relations

    def find_sense_by_id(self, sense_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a sense by ID, including in related entries.

        Args:
            sense_id: ID of the sense to find.

        Returns:
            Sense with the given ID, or None if not found.
        """
        # First, try to find the sense in the current entry
        sense = self.get_sense_by_id(sense_id)
        if sense:
            return sense

        return None

    def get_reverse_variant_relations(self, dict_service=None) -> List[Dict[str, Any]]:
        """
        Find entries that are variants of this entry (reverse lookup).
        
        Args:
            dict_service: DictionaryService instance for searching entries
            
        Returns:
            List of dictionaries containing reverse variant information.
            Each dictionary contains:
            - ref: Reference from the variant entry (the entry that is a variant of this one)
            - variant_type: The variant type from the trait value  
            - type: The relation type
            - order: The relation order (if present)
            - direction: 'incoming' to indicate this is a reverse relation
        """
        if not dict_service:
            # If no service provided, we can't search - return empty list
            return []
            
        reverse_relations = []
        
        try:
            # Search all entries to find those with variant relations pointing to this entry
            all_entries, _ = dict_service.list_entries(limit=None)  # Get all entries
            
            for entry in all_entries:
                if entry.id == self.id:
                    continue  # Skip self
                    
                # Check if this entry has variant relations
                for relation in entry.relations:
                    try:
                        if (hasattr(relation, 'traits') and relation.traits and 
                            isinstance(relation.traits, dict) and 'variant-type' in relation.traits and
                            hasattr(relation, 'ref') and relation.ref and
                            hasattr(relation, 'type') and relation.type):
                            
                            # Check if the relation points to our current entry
                            if str(relation.ref) == self.id:
                                variant_info = {
                                    'ref': entry.id,  # The entry that IS a variant of this one
                                    'ref_lexical_unit': entry.get_lexical_unit(),  # Add human-readable text
                                    'ref_display_text': entry.get_lexical_unit(),  # Add display text for template
                                    'variant_type': str(relation.traits['variant-type']),
                                    'type': str(relation.type),
                                    'direction': 'incoming'  # Mark as reverse relation
                                }
                                
                                # Include order if available
                                if (hasattr(relation, 'order') and relation.order is not None and 
                                    isinstance(relation.order, (int, str))):
                                    try:
                                        variant_info['order'] = int(relation.order)
                                    except (ValueError, TypeError):
                                        pass
                                        
                                reverse_relations.append(variant_info)
                    except (AttributeError, TypeError, KeyError):
                        continue
                        
        except Exception as e:
            # If search fails, just return empty list - don't break the page
            pass
            
        # Sort by lexical unit for consistent display
        try:
            reverse_relations.sort(key=lambda x: (x.get('order', 999), x.get('ref_lexical_unit', x['ref'])))
        except (TypeError, KeyError):
            pass
            
        return reverse_relations

    def get_complete_variant_relations(self, dict_service=None) -> List[Dict[str, Any]]:
        """
        Get complete variant relations including both directions:
        - Outgoing: entries this entry is a variant of
        - Incoming: entries that are variants of this entry
        
        Args:
            dict_service: DictionaryService instance for searching entries
            
        Returns:
            List of all variant relations with direction markers
        """
        # Get outgoing relations (this entry IS a variant of others)
        outgoing = self.get_variant_relations(dict_service)
        for relation in outgoing:
            relation['direction'] = 'outgoing'
            
        # Get incoming relations (other entries ARE variants of this entry)  
        incoming = self.get_reverse_variant_relations(dict_service)
        
        # Combine both
        all_relations = outgoing + incoming
        
        # Sort by direction first (outgoing, then incoming), then by lexical unit
        try:
            all_relations.sort(key=lambda x: (
                0 if x.get('direction') == 'outgoing' else 1,
                x.get('order', 999), 
                x.get('ref_lexical_unit', x.get('ref', ''))
            ))
        except (TypeError, KeyError):
            pass
            
        return all_relations

    def _apply_pos_inheritance(self) -> None:
        """
        Apply part-of-speech inheritance logic.
        
        If the entry doesn't have an explicit grammatical_info (part of speech),
        inherit it from the senses if all senses have the same POS.
        """
        # Helper function to extract POS value from various formats
        def extract_pos_value(grammatical_info):
            if not grammatical_info:
                return ""
            if isinstance(grammatical_info, str):
                return grammatical_info.strip()
            elif isinstance(grammatical_info, dict):
                # Handle dict format (e.g., from form data with dots)
                pos_val = grammatical_info.get('part_of_speech', '')
                return pos_val.strip() if isinstance(pos_val, str) else ""
            else:
                return ""
        
        # Only apply inheritance if entry has no explicit POS or empty POS
        # Be more aggressive about detecting empty POS values
        entry_pos_value = extract_pos_value(self.grammatical_info)
        entry_has_pos = (
            entry_pos_value and 
            entry_pos_value not in ['', 'null', 'None', 'undefined']
        )
        
        if entry_has_pos:
            return  # Entry has explicit POS, don't override
        
        if not self.senses:
            return  # No senses to inherit from
        
        # Collect all unique POS values from senses
        sense_pos_values = set()
        for sense in self.senses:
            if hasattr(sense, 'grammatical_info') and sense.grammatical_info:
                pos_value = sense.grammatical_info.strip()
                if pos_value and pos_value not in ['', 'null', 'None', 'undefined']:
                    sense_pos_values.add(pos_value)
        
        # Only inherit if all senses have the same POS
        if len(sense_pos_values) == 1:
            inherited_pos = next(iter(sense_pos_values))
            self.grammatical_info = inherited_pos
            # Log this for debugging
            print(f"[DEBUG] Entry {self.id} inherited POS '{inherited_pos}' from senses")

    def _validate_pos_consistency(self, errors: List[str]) -> None:
        """
        Validate part-of-speech consistency between entry and senses.
        
        Args:
            errors: List to append validation errors to.
        """
        if not self.senses:
            return  # No senses to validate against
        
        # Helper function to extract POS value from various formats
        def extract_pos_value(grammatical_info):
            if not grammatical_info:
                return ""
            if isinstance(grammatical_info, str):
                return grammatical_info.strip()
            elif isinstance(grammatical_info, dict):
                # Handle dict format (e.g., from form data with dots)
                pos_val = grammatical_info.get('part_of_speech', '')
                return pos_val.strip() if isinstance(pos_val, str) else ""
            else:
                return ""
        
        # Get entry POS (string format)
        entry_pos = extract_pos_value(self.grammatical_info)
        
        # Collect all unique POS values from senses
        sense_pos_values = set()
        for sense in self.senses:
            if hasattr(sense, 'grammatical_info') and sense.grammatical_info:
                pos_value = sense.grammatical_info.strip()
                if pos_value:
                    sense_pos_values.add(pos_value)
        
        # If entry has no POS but senses do, check if senses are consistent
        if not entry_pos and sense_pos_values:
            if len(sense_pos_values) > 1:
                errors.append(f"Senses have inconsistent part-of-speech values: {', '.join(sorted(sense_pos_values))}. Please set the entry part-of-speech manually.")
        
        # If entry has POS and senses have POS, check for consistency
        elif entry_pos and sense_pos_values:
            if entry_pos not in sense_pos_values:
                errors.append(f"Entry part-of-speech '{entry_pos}' does not match any sense part-of-speech values: {', '.join(sorted(sense_pos_values))}")
            elif len(sense_pos_values) > 1:
                # Entry POS matches at least one sense, but senses are inconsistent
                errors.append(f"Senses have inconsistent part-of-speech values: {', '.join(sorted(sense_pos_values))}. Entry POS '{entry_pos}' matches some but not all senses.")

    def _get_or_classify_morph_type(self, existing_morph_type: Optional[str]) -> Optional[str]:
        """
        Get existing morph type or auto-classify based on lexical unit.
        
        Args:
            existing_morph_type: Existing morph type from LIFT data
            
        Returns:
            Morph type (existing if provided, otherwise auto-classified)
        """
        # If already set from LIFT data, preserve it
        if existing_morph_type and existing_morph_type.strip():
            return existing_morph_type.strip()
        
        # Auto-classify based on lexical unit
        if not self.lexical_unit:
            return 'stem'  # Default
            
        # Get the primary headword (usually English)
        headword = ''
        if 'en' in self.lexical_unit:
            headword = self.lexical_unit['en']
        elif self.lexical_unit:
            # Use first available language
            headword = next(iter(self.lexical_unit.values()))
            
        if not headword or not headword.strip():
            return 'stem'  # Default
            
        headword = headword.strip()
        
        # Classification logic (same as JavaScript)
        if ' ' in headword:
            return 'phrase'
        elif headword.endswith('-') and not headword.startswith('-'):
            return 'prefix'
        elif headword.startswith('-') and not headword.endswith('-'):
            return 'suffix'
        elif headword.startswith('-') and headword.endswith('-'):
            return 'infix'
        else:
            return 'stem'  # Default for regular words
