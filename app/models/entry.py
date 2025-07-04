"""
Entry model representing a dictionary entry in LIFT format.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from app.models.base import BaseModel
from app.utils.exceptions import ValidationError

if TYPE_CHECKING:
    from app.models.sense import Sense


class Form(BaseModel):
    """
    Represents a form in a LIFT entry.
    """

    def __init__(self, lang: str, text: str, **kwargs: Any):
        super().__init__(**kwargs)
        self.lang = lang
        self.text = text


class Gloss(BaseModel):
    """
    Represents a gloss in a LIFT entry.
    """

    def __init__(self, lang: str, text: str, **kwargs: Any):
        super().__init__(**kwargs)
        self.lang = lang
        self.text = text


class Etymology(BaseModel):
    """
    Represents an etymology in a LIFT entry.
    """

    def __init__(self, type: str, source: str, form: Union[Form, Dict[str, str]], gloss: Union[Gloss, Dict[str, str]], **kwargs: Any):
        super().__init__(**kwargs)
        self.type = type
        self.source = source
        self.form = Form(**form) if isinstance(form, dict) else form
        self.gloss = Gloss(**gloss) if isinstance(gloss, dict) else gloss

    def to_dict(self) -> Dict[str, Any]:
        """Convert etymology to dictionary with nested objects."""
        result = super().to_dict()
        
        # Convert nested objects
        if hasattr(self.form, 'to_dict'):
            result['form'] = self.form.to_dict()
        if hasattr(self.gloss, 'to_dict'):
            result['gloss'] = self.gloss.to_dict()
            
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

    def __init__(self, form: Union[Form, Dict[str, str]], **kwargs: Any):
        super().__init__(**kwargs)
        self.form = Form(**form) if isinstance(form, dict) else form

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

    def __init__(self, id_: Optional[str] = None, **kwargs: Any):
        """
        Initialize an entry.

        Args:
            id_: Unique identifier for the entry.
            **kwargs: Additional attributes to set on the entry.
        """

        # Extract complex structures before calling super to avoid double processing
        senses_data = kwargs.pop('senses', [])
        etymologies_data = kwargs.pop('etymologies', [])
        relations_data = kwargs.pop('relations', [])
        variants_data = kwargs.pop('variants', [])

        super().__init__(id_, **kwargs)
        self.lexical_unit: Dict[str, str] = kwargs.get('lexical_unit', {})
        self.citations: List[Dict[str, Any]] = kwargs.get('citations', [])
        self.pronunciations: Dict[str, str] = kwargs.get('pronunciations', {})
        self.grammatical_info: Optional[str] = kwargs.get('grammatical_info')
        self.notes: Dict[str, Union[str, Dict[str, str]]] = kwargs.get('notes', {})
        self.custom_fields: Dict[str, Any] = kwargs.get('custom_fields', {})
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

        # Handle relations
        self.relations: List[Relation] = []
        for relation_data in relations_data:
            if isinstance(relation_data, dict):
                self.relations.append(Relation(**relation_data))
            elif isinstance(relation_data, Relation):
                self.relations.append(relation_data)

        # Handle variants
        self.variants: List[Variant] = []
        for variant_data in variants_data:
            if isinstance(variant_data, dict):
                self.variants.append(Variant(**variant_data))
            elif isinstance(variant_data, Variant):
                self.variants.append(variant_data)

    def validate(self) -> bool:
        """
        Validate the entry.

        Returns:
            True if the entry is valid.

        Raises:
            ValidationError: If the entry is invalid.
        """
        errors = []

        # Validate required fields
        if not self.id:
            errors.append("Entry ID is required")

        if not self.lexical_unit:
            errors.append("Lexical unit is required")

        # Validate senses
        for i, sense in enumerate(self.senses):
            if not sense.id:
                errors.append(f"Sense at index {i} is missing an ID")

        if errors:
            raise ValidationError("Entry validation failed", errors)

        return True

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

    @property
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
        form = Form(lang=form_lang, text=form_text)
        gloss = Gloss(lang=gloss_lang, text=gloss_text)
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
        Convert the entry to a dictionary, including computed properties.

        Returns:
            Dictionary representation of the entry.
        """
        result = super().to_dict()

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

    def get_variant_relations(self) -> List[Dict[str, Any]]:
        """
        Extract variant information from relations with variant-type traits.
        
        Returns:
            List of dictionaries containing variant information extracted from relations.
            Each dictionary contains:
            - ref: Reference to the target entry
            - variant_type: The variant type from the trait value
            - type: The relation type
            - order: The relation order (if present)
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
                        
                    variant_relations.append(variant_info)
            except (AttributeError, TypeError, KeyError) as e:
                # Skip relations that can't be processed
                continue
        
        # Sort by order if available, otherwise by ref
        try:
            variant_relations.sort(key=lambda x: (x.get('order', 999), x['ref']))
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
                                # Get the lexical unit and format with homograph number
                                lexical_unit = entry.get_lexical_unit()
                                display_text = lexical_unit
                                if entry.homograph_number and entry.homograph_number > 1:
                                    # Add subscript homograph number
                                    display_text = f"{lexical_unit}₍{entry.homograph_number}₎"
                                
                                variant_info = {
                                    'ref': entry.id,  # The entry that IS a variant of this one
                                    'ref_lexical_unit': lexical_unit,  # Human-readable text without homograph
                                    'ref_display_text': display_text,  # Human-readable text with homograph if needed
                                    'ref_homograph_number': entry.homograph_number,  # Homograph number for styling
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
        outgoing = self.get_variant_relations()
        for relation in outgoing:
            relation['direction'] = 'outgoing'
            
            # Look up the target entry to get its lexical unit and homograph number
            if dict_service:
                try:
                    target_entry = dict_service.get_entry(relation['ref'])
                    if target_entry:
                        lexical_unit = target_entry.get_lexical_unit()
                        relation['ref_lexical_unit'] = lexical_unit
                        
                        # Create display text with homograph number if needed
                        display_text = lexical_unit
                        if target_entry.homograph_number and target_entry.homograph_number > 1:
                            display_text = f"{lexical_unit}₍{target_entry.homograph_number}₎"
                        relation['ref_display_text'] = display_text
                        relation['ref_homograph_number'] = target_entry.homograph_number
                except Exception:
                    # If lookup fails, just use the ref as display text
                    relation['ref_lexical_unit'] = relation['ref']
                    relation['ref_display_text'] = relation['ref']
                    relation['ref_homograph_number'] = None
            
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
