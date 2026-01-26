"""
Sense model representing a sense in a dictionary entry.
"""

from typing import Dict, List, Any, Optional, Union
from app.models.base import BaseModel
from app.utils.exceptions import ValidationError


class Sense(BaseModel):
    """
    Sense model representing a sense in a dictionary entry.
    
    Attributes:
        id: Unique identifier for the sense.
        glosses: Dictionary mapping language codes to gloss text.
        definitions: Dictionary mapping language codes to definition text.
        grammatical_info: Grammatical information for the sense.
        examples: List of example objects for the sense.
        relations: List of semantic relations to other senses.
        notes: Dictionary mapping note types to note content.
        custom_fields: Dictionary of custom fields for the sense.
        illustrations: List of illustration dictionaries with 'href' and optional 'label' (multilingual).
    """
    
    def __init__(self, id_: Optional[str] = None, **kwargs):
        """
        Initialize a sense.
        
        LIFT format: flat structure {lang: text} for glosses and definitions.
        
        Args:
            id_: Unique identifier for the sense.
            **kwargs: Additional attributes to set on the sense.
        """
        # Initialize attributes - LIFT FLAT FORMAT {lang: text}
        self.glosses: dict[str, str] = kwargs.pop('glosses', {})
        self.definitions: dict[str, str] = kwargs.pop('definitions', {})
        self.grammatical_info = kwargs.pop('grammatical_info', None)
        self.grammatical_traits: dict[str, str] | None = kwargs.pop('grammatical_traits', None)
        self.examples = kwargs.pop('examples', [])
        self.relations = kwargs.pop('relations', [])
        self.variant_relations = kwargs.pop('variant_relations', [])
        self.notes = kwargs.pop('notes', {})
        self.custom_fields = kwargs.pop('custom_fields', {})
        self.traits: dict[str, str] = kwargs.pop('traits', {})
        self.illustrations: list[dict[str, Any]] = kwargs.pop('illustrations', [])

        # Internal storage for fields with special typing/behavior
        # domain_type is now a list of strings (supports multiple values)
        self._domain_type_value: list[str] = []
        self._semantic_domains_value: Optional[List[str]] = None
        
        # LIFT 0.13: Literal meaning field - stores literal meaning of compounds/idioms (multitext) - Day 28
        literal_meaning_value = kwargs.pop('literal_meaning', None)
        if isinstance(literal_meaning_value, dict):
            self.literal_meaning: Optional[Dict[str, str]] = literal_meaning_value
        else:
            self.literal_meaning: Optional[Dict[str, str]] = None

        exemplar_value = kwargs.pop('exemplar', None)
        self.exemplar: Optional[Dict[str, str]] = exemplar_value if isinstance(exemplar_value, dict) else None

        scientific_name_value = kwargs.pop('scientific_name', None)
        self.scientific_name: Optional[Dict[str, str]] = (
            scientific_name_value if isinstance(scientific_name_value, dict) else None
        )
        
        # LIFT-aligned fields: usage_type (list) and domain_type (single value)
        # usage_type supports multiple values and is stored as a list
        usage_type_value = kwargs.pop('usage_type', [])
        if isinstance(usage_type_value, str):
            # If it's a string, split semicolon-separated LIFT format into list
            self.usage_type: list[str] = [v.strip() for v in usage_type_value.split(';') if v.strip()]
        elif isinstance(usage_type_value, list):
            self.usage_type: list[str] = usage_type_value
        else:
            self.usage_type: list[str] = []

        # semantic_domains should contain only semantic-domain-ddp4 trait values (list of strings)
        # Handle semantic domains from parser OR from constructor (both should go to same field)
        semantic_domains_value = kwargs.pop('semantic_domains', None)
        if isinstance(semantic_domains_value, str):
            self.semantic_domains = [semantic_domains_value.strip()] if semantic_domains_value.strip() else None
        elif isinstance(semantic_domains_value, list):
            # Filter out empty values and normalize - this handles the case from the failing test
            non_empty_values = [v.strip() for v in semantic_domains_value if isinstance(v, str) and v.strip()]
            self.semantic_domains = non_empty_values if non_empty_values else None
        elif semantic_domains_value is None:
            self.semantic_domains = None
        else:
            # Convert non-string/non-list values to a single-item list
            str_value = str(semantic_domains_value) if semantic_domains_value else None
            if str_value and str_value.strip():
                self.semantic_domains = [str_value.strip()]
            else:
                self.semantic_domains = None

        # Handle domain_type - always treat as a list of values at sense level.
        domain_type_value = kwargs.pop('domain_type', None)
        if isinstance(domain_type_value, list):
            # Filter out empty values and strip whitespace
            self._domain_type_value = [v.strip() for v in domain_type_value if isinstance(v, str) and v.strip()]
        elif isinstance(domain_type_value, str):
            val = domain_type_value.strip()
            # Accept semicolon-separated values as well
            if ';' in val:
                self._domain_type_value = [v.strip() for v in val.split(';') if v.strip()]
            else:
                self._domain_type_value = [val] if val else []
        elif domain_type_value is None:
            self._domain_type_value = []
        else:
            str_value = str(domain_type_value).strip()
            self._domain_type_value = [str_value] if str_value else []

        # Now call super() with remaining kwargs (after handling our custom params)
        super().__init__(id_, **kwargs)

    @property
    def domain_type(self) -> list[str]:
        """Return the domain-type values as a list of strings (empty list if none)."""
        return list(self._domain_type_value)

    @domain_type.setter
    def domain_type(self, value: Optional[Union[str, List[str]]]):
        if value is None:
            self._domain_type_value = []
        elif isinstance(value, list):
            # Filter out empty values and strip whitespace
            self._domain_type_value = [v.strip() for v in value if isinstance(v, str) and v.strip()]
        elif isinstance(value, str):
            val = value.strip()
            if ';' in val:
                self._domain_type_value = [v.strip() for v in val.split(';') if v.strip()]
            else:
                self._domain_type_value = [val] if val else []
        else:
            str_value = str(value).strip()
            self._domain_type_value = [str_value] if str_value else []

    @property
    def semantic_domains(self) -> Optional[List[str]]:
        """Return semantic domains."""
        return self._semantic_domains_value

    @semantic_domains.setter
    def semantic_domains(self, value: Optional[List[str]]):
        self._semantic_domains_value = value

    def validate(self) -> bool:
        """
        Validate the sense using the centralized validation system and enforce that at least one gloss or definition is non-empty.
        Returns:
            True if the sense is valid.
        Raises:
            ValidationError: If the sense is invalid.
        """
        from app.services.validation_engine import ValidationEngine

        # Check for at least one non-empty gloss or definition
        # LIFT flat format: values are strings, not dicts
        has_nonempty_gloss = any(
            isinstance(val, str) and val.strip()
            for val in self.glosses.values()
        )
        has_nonempty_definition = any(
            isinstance(val, str) and val.strip()
            for val in self.definitions.values()
        )
        if not (has_nonempty_gloss or has_nonempty_definition):
            raise ValidationError(
                "Sense must have at least one non-empty gloss or definition."
            )

        # Use centralized validation system as before
        sense_data = {
            'id': 'temp_entry_id',
            'lexical_unit': {'en': 'temp'},
            'senses': [self.to_dict()]
        }
        engine = ValidationEngine()
        result = engine.validate_entry(sense_data)

        # Collect all relevant errors (sense-specific and any that could apply to this sense)
        sense_errors = []
        for error in result.errors:
            if (
                'sense' in error.rule_id.lower() or
                'senses[0]' in error.message or
                'Sense at index 0' in error.message or
                error.rule_id.startswith('R2.')
            ):
                sense_errors.append(error.message)

        sense_dict = self.to_dict()
        if not sense_dict.get('id') or (isinstance(sense_dict['id'], str) and not sense_dict['id'].strip()):
            sense_errors.append("Sense ID is required and must be non-empty")

        if sense_errors:
            raise ValidationError("Sense validation failed", sense_errors)

        return True
    
    def add_example(self, example: Dict[str, Any]) -> None:
        """
        Add an example to the sense.
        
        Args:
            example: Example to add.
        """
        self.examples.append(example)
    
    def remove_example(self, example_id: str) -> bool:
        """
        Remove an example from the sense.
        
        Args:
            example_id: ID of the example to remove.
            
        Returns:
            True if the example was removed, False if it was not found.
        """
        for i, example in enumerate(self.examples):
            if example.get('id') == example_id:
                del self.examples[i]
                return True
        
        return False
    
    def add_relation(self, relation_type: str, target_id: str) -> None:
        """
        Add a semantic relation to the sense.

        Args:
            relation_type: Type of relation (e.g., 'synonym', 'antonym').
            target_id: ID of the target sense.
        """
        self.relations.append({
            'type': relation_type,
            'ref': target_id
        })

    def add_variant_relation(self, variant_type: str, target_id: str, **kwargs) -> None:
        """
        Add a variant relation to the sense.
        Variant relations link this sense to variant forms (e.g., archaic, colloquial).

        Args:
            variant_type: Type of variant (e.g., 'archaic', 'colloquial', 'dialect').
            target_id: ID of the target entry.
            **kwargs: Additional optional fields (e.g., 'comment', 'trait').
        """
        relation = {
            'type': variant_type,
            'ref': target_id
        }
        if kwargs:
            relation.update(kwargs)
        self.variant_relations.append(relation)

    def remove_variant_relation(self, target_id: str) -> bool:
        """
        Remove a variant relation by target ID.

        Args:
            target_id: ID of the target entry to remove.

        Returns:
            True if removed, False if not found.
        """
        for i, rel in enumerate(self.variant_relations):
            if rel.get('ref') == target_id:
                del self.variant_relations[i]
                return True
        return False

    def add_bidirectional_relation(self, relation_type: str, target_id: str, source_id: str, dict_service=None) -> None:
        """
        Add a bidirectional semantic relation (both forward and reverse).

        Args:
            relation_type: Type of relation (e.g., 'synonim', 'antonim').
            target_id: ID of the target sense.
            source_id: ID of the source sense (for the reverse relation).
            dict_service: Dictionary service to access ranges if needed.
        """
        from app.utils.bidirectional_relations import is_relation_bidirectional, get_reverse_relation_type
        from app.models.entry import Entry
        from app.models.sense import Sense

        # Add the forward relation
        self.add_relation(relation_type, target_id)

        # Check if this relation type should be bidirectional
        if is_relation_bidirectional(relation_type, dict_service):
            # For symmetric relations (like synonyms), use the same relation type
            if relation_type in ['synonim', 'antonim', 'Porównaj', 'porownaj']:
                reverse_relation_type = relation_type
            else:
                # For asymmetric but bidirectional relations, get the reverse type
                reverse_relation_type = get_reverse_relation_type(relation_type)

            # Add the reverse relation - we need to find the target sense object to add the relation
            # This is normally done at a higher level where both objects are available
            # In most cases, this method is called from the UI level where both objects exist
    
    def enrich_relations_with_display_text(self, dict_service=None) -> list[dict]:
        """
        Enrich sense relations with display text from target senses.

        Args:
            dict_service: Dictionary service to look up target entries/senses

        Returns:
            List of enriched relation dictionaries with ref_display_text and ref_gloss
        """
        if not dict_service or not self.relations:
            return self.relations

        enriched_relations = []

        for relation in self.relations:
            enriched = relation.copy()

            try:
                ref = relation.get('ref', '')
                if not ref:
                    enriched_relations.append(enriched)
                    continue

                # Use targeted XQuery to find entry containing this sense
                # The ref can be either "entry_id_sense_id" or just "sense_id"
                # Try to find entry by querying for sense with this ID
                db = dict_service.db_connector
                if db:
                    # XQuery to find entry containing a sense with the given ID
                    query = f"""
                        for $entry in collection('dictionary')//entry
                        where $entry//sense[@id='{ref}']
                        return $entry
                    """
                    result = db.execute_query(query)

                    if result:
                        import re
                        from app.parsers.lift_parser import LIFTParser

                        parser = LIFTParser()
                        entry_matches = re.findall(r'<entry[^>]*>.*?</entry>', result, re.DOTALL)

                        for entry_xml in entry_matches:
                            try:
                                target_entry = parser.parse_entry(entry_xml)

                                # Find the sense with matching ID
                                for sense in target_entry.senses:
                                    if sense.id == ref or (hasattr(sense, 'id_') and sense.id_ == ref):
                                        target_sense = sense
                                        break
                                else:
                                    continue

                                # Get headword from entry
                                enriched['ref_display_text'] = target_entry.get_lexical_unit()
                                enriched['ref_entry_id'] = target_entry.id

                                # Get gloss or definition from sense
                                if target_sense.glosses:
                                    first_gloss = next(iter(target_sense.glosses.values()), '')
                                    enriched['ref_gloss'] = first_gloss
                                elif target_sense.definitions:
                                    first_def = next(iter(target_sense.definitions.values()), '')
                                    enriched['ref_gloss'] = first_def

                                break  # Found the entry, no need to continue
                            except Exception:
                                continue

            except Exception:
                # If resolution fails, just use the relation as-is
                pass

            enriched_relations.append(enriched)

        return enriched_relations
    
    def add_definition(self, language: str, text: str) -> None:
        """
        Add a definition to the sense in LIFT flat format.
        Args:
            language: Language code (e.g., 'en', 'pl').
            text: Definition text.
        """
        self.definitions[language] = text
    
    def add_gloss(self, language: str, text: str) -> None:
        """
        Add a gloss to the sense in LIFT flat format.
        Args:
            language: Language code (e.g., 'en', 'pl').
            text: Gloss text.
        """
        self.glosses[language] = text
    
    @property
    def definition(self) -> dict[str, str]:
        """
        Get the full multilingual definition dict for display or serialization.
        LIFT flat format: {lang: text}
        Returns:
            The full definitions dict (lang -> text).
        """
        return self.definitions

    @definition.setter
    def definition(self, value: dict[str, dict[str, str]]) -> None:
        """
        Set the full multilingual definitions dict.
        Args:
            value: Dict of definitions by language.
        """
        if isinstance(value, dict):
            self.definitions = value
    
    @property
    def gloss(self) -> dict[str, str]:
        """
        Get the full multilingual gloss dict for display or serialization.
        LIFT flat format: {lang: text}
        Returns:
            The full glosses dict (lang -> text).
        """
        return self.glosses

    @gloss.setter
    def gloss(self, value: dict[str, str]) -> None:
        """
        Set the full multilingual glosses dict.
        LIFT flat format: {lang: text}
        Args:
            value: Dict of glosses by language.
        """
        if isinstance(value, dict):
            self.glosses = value
    
    def get_definition(self, lang: Optional[str] = None) -> str:
        """
        Get the definition in the specified language.
        LIFT flat format: values are strings directly.
        
        Args:
            lang: Language code to retrieve. If None, returns the default.
            
        Returns:
            The definition text in the specified language, or empty string if not found.
        """
        if lang:
            return self.definitions.get(lang, '')
        # Return first available definition or call property
        if self.definitions:
            return next(iter(self.definitions.values()), '')
        return ''
    
    def get_gloss(self, lang: Optional[str] = None) -> str:
        """
        Get the gloss in the specified language.
        LIFT flat format: values are strings directly.
        
        Args:
            lang: Language code to retrieve. If None, returns the default.
            
        Returns:
            The gloss text in the specified language, or empty string if not found.
        """
        if lang:
            return self.glosses.get(lang, '')
        # Return first available gloss or call property
        if self.glosses:
            return next(iter(self.glosses.values()), '')
        return ''
    
    def get_available_definition_languages(self) -> List[str]:
        """
        Get a list of languages available for definitions.
        
        Returns:
            List of language codes.
        """
        return list(self.definitions.keys())
    
    def get_available_gloss_languages(self) -> List[str]:
        """
        Get a list of languages available for glosses.
        
        Returns:
            List of language codes.
        """
        return list(self.glosses.keys())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the sense to a dictionary, including computed properties.
        
        Returns:
            Dictionary representation of the sense.
        """
        result = super().to_dict()
        
        # Convert Example objects to dicts
        if 'examples' in result and result['examples']:
            result['examples'] = [
                ex.to_dict() if hasattr(ex, 'to_dict') else ex 
                for ex in result['examples']
            ]
        
        # Add computed properties for template compatibility
        result['definition'] = self.definition
        result['gloss'] = self.gloss

        # Sense-level fields
        result['usage_type'] = self.usage_type
        result['domain_type'] = self.domain_type
        
        # LIFT 0.13: Include subsenses (recursive)
        if hasattr(self, 'subsenses') and self.subsenses:
            result['subsenses'] = [
                subsense.to_dict() if isinstance(subsense, Sense) else subsense
                for subsense in self.subsenses
            ]
        else:
            result['subsenses'] = []
        
        # LIFT 0.13: Include reversals - Day 24-25
        if hasattr(self, 'reversals') and self.reversals:
            result['reversals'] = self.reversals
        else:
            result['reversals'] = []

        # Sense-level variant relations
        if hasattr(self, 'variant_relations') and self.variant_relations:
            result['variant_relations'] = self.variant_relations
        else:
            result['variant_relations'] = []

        # LIFT 0.13: Include annotations - Day 26-27
        if hasattr(self, 'annotations') and self.annotations:
            result['annotations'] = self.annotations
        else:
            result['annotations'] = []
        
        # LIFT 0.13: FieldWorks Standard Custom Fields - Day 28
        if hasattr(self, 'exemplar') and self.exemplar:
            result['exemplar'] = self.exemplar
        else:
            result['exemplar'] = None
        
        if hasattr(self, 'scientific_name') and self.scientific_name:
            result['scientific_name'] = self.scientific_name
        else:
            result['scientific_name'] = None

        if hasattr(self, 'literal_meaning') and self.literal_meaning:
            result['literal_meaning'] = self.literal_meaning
        else:
            result['literal_meaning'] = None

        # Include semantic_domains in the serialized dictionary for LIFT generation
        if hasattr(self, 'semantic_domains') and self.semantic_domains is not None:
            result['semantic_domains'] = self.semantic_domains
        else:
            result['semantic_domains'] = None

        return result

    def to_display_dict(self) -> Dict[str, Any]:
        """
        Convert the sense to a dictionary for display, simplifying multilingual fields.
        LIFT flat format: values are strings directly (not nested dicts with 'text' key).
        """
        result = super().to_dict()

        # Convert Example objects to dicts
        if 'examples' in result and result['examples']:
            result['examples'] = [
                ex.to_dict() if hasattr(ex, 'to_dict') else ex 
                for ex in result['examples']
            ]

        # Simplify definition - LIFT flat format {lang: text}
        definition_text = ''
        if self.definitions:
            if 'en' in self.definitions:
                val = self.definitions['en']
                # Handle both flat (string) and nested (dict with 'text') formats for compatibility
                definition_text = val if isinstance(val, str) else val.get('text', '')
            elif self.definitions:
                first_lang = next(iter(self.definitions))
                val = self.definitions[first_lang]
                definition_text = val if isinstance(val, str) else val.get('text', '')
        result['definition'] = definition_text

        # Simplify gloss - LIFT flat format {lang: text}
        gloss_text = ''
        if self.glosses:
            if 'en' in self.glosses:
                val = self.glosses['en']
                # Handle both flat (string) and nested (dict with 'text') formats for compatibility
                gloss_text = val if isinstance(val, str) else val.get('text', '')
            elif self.glosses:
                first_lang = next(iter(self.glosses))
                val = self.glosses[first_lang]
                gloss_text = val if isinstance(val, str) else val.get('text', '')
        result['gloss'] = gloss_text

        return result
