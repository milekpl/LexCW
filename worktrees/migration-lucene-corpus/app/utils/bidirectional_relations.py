"""
Utility functions for handling bidirectional lexical relations.
"""

from typing import Dict, Any, Optional
from app.services.dictionary_service import DictionaryService


def is_relation_bidirectional(relation_type: str, dict_service: Optional[DictionaryService] = None) -> bool:
    """
    Determine if a lexical relation type is bidirectional based on LIFT ranges.
    By default, ALL lexical relations EXCEPT _component-lexeme are bidirectional.
    The _component-lexeme relations are special and unidirectional by design.

    Args:
        relation_type: The type of relation (e.g., 'synonim', 'antonim', '_component-lexeme')
        dict_service: Dictionary service to access ranges if needed

    Returns:
        True if the relation type is bidirectional (all except _component-lexeme), False otherwis
    """
    # _component-lexeme relations are the only ones that are intentionally unidirectional
    if relation_type == '_component-lexeme':
        return False

    # All other lexical relations are bidirectional by default
    return True


def get_reverse_relation_type(relation_type: str, dict_service: Optional[DictionaryService] = None) -> str:
    """
    Get the reverse relation type for bidirectional relations.

    For antisymmetrical relations (like hiperonim/hiponim), this returns the opposite relation type.
    For symmetrical relations (like synonim), this returns the same relation type.

    Args:
        relation_type: The original relation type
        dict_service: Dictionary service to access ranges if available

    Returns:
        The reverse relation type
    """
    # If we have access to dict_service, we can dynamically determine from ranges
    if dict_service is not None:
        try:
            ranges = dict_service.get_lift_ranges()
            if 'lexical-relation' in ranges:
                relation_values = ranges['lexical-relation'].get('values', [])

                for rel_value in relation_values:
                    if rel_value.get('id') == relation_type:
                        # Check if this relation has a reverse-label defined
                        reverse_labels = rel_value.get('reverse_labels', {})
                        if reverse_labels:
                            # If it has reverse labels, determine the reverse relation type from ranges
                            # This would typically be some kind of reverse mapping based on the ranges
                            # For now, we'll map the common antisymmetrical relations:
                            antisymmetrical_mapping = {
                                'hiperonim': 'hiponim',  # hypernym -> hyponym
                                'hiponim': 'hiperonim',  # hyponym -> hypernym
                                'holonim': 'meronim',    # holonym -> meronym
                                'meronim': 'holonim',    # meronym -> holonym
                                'Part': 'Whole',         # part -> whole (from ranges)
                                'Whole': 'Part',         # whole -> part
                                'Przypadek': 'Generic',  # specific -> generic (from ranges)
                                'Generic': 'Przypadek',  # generic -> specific
                            }
                            return antisymmetrical_mapping.get(relation_type, relation_type)

        except Exception:
            # If we can't access ranges, fall back to hardcoded mappings
            pass

    # Default hardcoded mappings as fallback
    antisymmetrical_mapping = {
        'hiperonim': 'hiponim',  # hypernym -> hyponym
        'hiponim': 'hiperonim',  # hyponym -> hypernym
        'holonim': 'meronim',    # holonym -> meronym
        'meronim': 'holonim',    # meronym -> holonym
        'causes': 'is_caused_by',  # causes -> is caused by
    }

    # For symmetrical relations like synonim, antonim, Porównaj, return the same type
    return antisymmetrical_mapping.get(relation_type, relation_type)


def add_bidirectional_relation(
    source_obj: Any, 
    target_obj: Any, 
    relation_type: str, 
    target_id: str,
    source_id: str,
    dict_service: Optional[DictionaryService] = None
) -> None:
    """
    Add a relation from source to target and optionally the reverse relation from target to source.
    
    Args:
        source_obj: The source object (entry or sense) that has the relation
        target_obj: The target object (entry or sense) that is related to
        relation_type: Type of relation to add
        target_id: ID of the target object
        source_id: ID of the source object 
        dict_service: Dictionary service to access ranges if needed
    """
    # Add the forward relation
    source_obj.add_relation(relation_type, target_id)
    
    # Check if this relation type should be bidirectional
    if is_relation_bidirectional(relation_type, dict_service):
        # For symmetric relations (like synonyms), use the same relation type
        if relation_type in ['synonim', 'antonim', 'Porównaj', 'porownaj']:
            reverse_relation_type = relation_type
        else:
            # For asymmetric but bidirectional relations, get the reverse type
            reverse_relation_type = get_reverse_relation_type(relation_type)
        
        # Add the reverse relation
        target_obj.add_relation(reverse_relation_type, source_id)