from __future__ import annotations

"""
Unified Bulk Service
====================

Consolidated implementation of the bulk operations stack (previously split
across bulk_operations_service / bulk_query_service / bulk_action_service /
bulk_rollback_service, which duplicated imports, helpers and DI wiring).

The legacy module names remain as thin re-export shims so existing imports
(API routes, tests, DI) keep working unchanged.
"""

import logging
from typing import List, Dict, Any, Optional, Set
from app.services.dictionary_service import DictionaryService
from app.services.workset_service import WorksetService
from app.services.operation_history_service import OperationHistoryService
from app.utils.exceptions import NotFoundError
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import re
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from app.utils.data_copier import DataCopier
from typing import Any, Optional
from uuid import uuid4
from datetime import datetime
from app.models.workset_models import db
from app.models.bulk_snapshot import BulkOperationSnapshot

logger = logging.getLogger(__name__)

@dataclass
class Condition:
    """Represents a single condition in a query."""
    field: str
    op: str
    value: Any = None
    related_type: Optional[str] = None
    target_in_field: Optional[str] = None
    condition: Optional[Condition] = None

@dataclass
class QueryFilter:
    """A complete query filter with conditions."""
    conditions: List[Condition] = field(default_factory=list)
    and_group: Optional[List[Condition]] = None
    or_group: Optional[List[Condition]] = None

class ActionType(str, Enum):
    """Types of bulk actions."""
    SET = 'set'
    CLEAR = 'clear'
    APPEND = 'append'
    PREPEND = 'prepend'
    ADD_RELATION = 'add_relation'
    REMOVE_RELATION = 'remove_relation'
    REPLACE_RELATION = 'replace_relation'
    COPY_FROM_RELATED = 'copy_from_related'
    PIPELINE = 'pipeline'

@dataclass
class BulkAction:
    """Represents a single bulk action."""
    action: str
    field: Optional[str] = None
    value: Any = None
    target_entry_id: Optional[str] = None
    from_field: Optional[str] = None
    to_field: Optional[str] = None
    relation_type: Optional[str] = None
    old_target: Optional[str] = None
    new_target: Optional[str] = None
    target_in_field: Optional[str] = None
    steps: Optional[List[BulkAction]] = None
    ranges: Optional[Dict[str, List[str]]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BulkAction':
        """Create from dictionary."""
        steps = None
        if data.get('steps'):
            steps = [cls.from_dict(s) for s in data['steps']]

        return cls(
            action=data.get('action', ''),
            field=data.get('field'),
            value=data.get('value'),
            target_entry_id=data.get('target_entry_id'),
            from_field=data.get('from_field'),
            to_field=data.get('to_field'),
            relation_type=data.get('relation_type'),
            old_target=data.get('old_target'),
            new_target=data.get('new_target'),
            target_in_field=data.get('target_in_field'),
            steps=steps,
            ranges=data.get('ranges')
        )

@dataclass
class RollbackResult:
    """Result of a rollback operation."""
    restored: int = 0
    failed: int = 0
    skipped: int = 0

class BulkOperationsService:
    """Service for atomic bulk operations on dictionary entries."""

    def __init__(self,
                 dictionary_service: DictionaryService,
                 workset_service: WorksetService,
                 history_service: Optional[OperationHistoryService] = None):
        """
        Initialize the BulkOperationsService.

        Args:
            dictionary_service: Service for dictionary entry operations.
            workset_service: Service for workset management.
            history_service: Optional service for recording operation history.
        """
        self.dictionary = dictionary_service
        self.workset = workset_service
        self.history = history_service

    def convert_traits(self, entry_ids: List[str], from_trait: str, to_trait: str) -> Dict[str, Any]:
        """
        Convert a trait value across multiple entries atomically.

        Args:
            entry_ids: List of entry IDs to modify.
            from_trait: Trait key to convert (e.g., 'part-of-speech').
            to_trait: New trait value to set.

        Returns:
            Dictionary containing:
                - 'results': List of result dicts for each entry
                - 'total': Total number of entries processed
        """
        results = []

        for entry_id in entry_ids:
            logger.debug("Processing entry_id=%s", entry_id)
            try:
                entry = self.dictionary.get_entry(entry_id)
                logger.debug("get_entry returned type=%s for %s", type(entry).__name__, entry_id)
            except NotFoundError:
                logger.debug("NotFoundError for %s", entry_id)
                results.append({
                    'id': entry_id,
                    'status': 'error',
                    'error': 'Entry not found'
                })
                continue
            except Exception as e:
                # Catch generic exceptions (e.g., DB issues) and record as an error result
                logger.error(f"Error fetching entry {entry_id}: {e}")
                err_msg = (e.args[0] if getattr(e, 'args', None) and len(e.args) > 0 else str(e))
                results.append({
                    'id': entry_id,
                    'status': 'error',
                    'error': err_msg
                })
                continue

            logger.debug("entry=%s, id(entry)=%s", entry, id(entry) if entry else None)
            try:
                if entry:
                    old_value = entry.traits.get(from_trait)
                    # Apply trait conversion
                    entry.convert_trait(from_trait, old_value, to_trait)
                    self.dictionary.update_entry(entry)
                    # update_entry returns None but modifies entry in place
                    results.append({
                        'id': entry_id,
                        'status': 'success',
                        'data': {'traits': entry.traits}
                    })

                    # Record operation for undo/redo
                    if self.history:
                        self.history.record_operation(
                            operation_type='bulk_trait_conversion',
                            data={
                                'entry_id': entry_id,
                                'trait': from_trait,
                                'old_value': old_value,
                                'new_value': to_trait
                            },
                            entry_id=entry_id
                        )
                else:
                    results.append({
                        'id': entry_id,
                        'status': 'error',
                        'error': 'Entry not found'
                    })
            except Exception as e:
                logger.error(f"Error converting trait for entry {entry_id}: {e}")
                err_msg = (e.args[0] if getattr(e, 'args', None) and len(e.args) > 0 else str(e))
                results.append({
                    'id': entry_id,
                    'status': 'error',
                    'error': err_msg
                })

        return {'results': results, 'total': len(results)}

    def update_pos_bulk(self, entry_ids: List[str], pos_tag: str) -> Dict[str, Any]:
        """
        Update part-of-speech tag across multiple entries.

        Args:
            entry_ids: List of entry IDs to modify.
            pos_tag: New POS tag (e.g., 'noun', 'verb').

        Returns:
            Dictionary containing:
                - 'results': List of result dicts for each entry
                - 'total': Total number of entries processed
        """
        results = []

        for entry_id in entry_ids:
            try:
                entry = self.dictionary.get_entry(entry_id)
            except NotFoundError:
                results.append({
                    'id': entry_id,
                    'status': 'error',
                    'error': 'Entry not found'
                })
                continue
            except Exception as e:
                logger.error(f"Error fetching entry {entry_id}: {e}")
                err_msg = (e.args[0] if getattr(e, 'args', None) and len(e.args) > 0 else str(e))
                results.append({
                    'id': entry_id,
                    'status': 'error',
                    'error': err_msg
                })
                continue

            try:
                if entry:
                    old_pos = entry.grammatical_info
                    # Apply POS update
                    entry.update_grammatical_info(pos_tag)
                    self.dictionary.update_entry(entry)
                    # update_entry returns None but modifies entry in place
                    results.append({
                        'id': entry_id,
                        'status': 'success',
                        'data': {'grammatical_info': entry.grammatical_info}
                    })

                    # Record operation for undo/redo
                    if self.history:
                        self.history.record_operation(
                            operation_type='bulk_pos_update',
                            data={
                                'entry_id': entry_id,
                                'old_value': old_pos,
                                'new_value': pos_tag
                            },
                            entry_id=entry_id
                        )
                else:
                    results.append({
                        'id': entry_id,
                        'status': 'error',
                        'error': 'Entry not found'
                    })
            except Exception as e:
                logger.error(f"Error updating POS for entry {entry_id}: {e}")
                err_msg = (e.args[0] if getattr(e, 'args', None) and len(e.args) > 0 else str(e))
                results.append({
                    'id': entry_id,
                    'status': 'error',
                    'error': err_msg
                })

        return {'results': results, 'total': len(results)}

class BulkQueryService:
    """Service for building and executing bulk queries."""

    # Valid operators for field conditions
    VALID_OPERATORS = {
        'equals', 'not_equals', 'contains', 'starts_with', 'ends_with',
        'regex', 'is_empty', 'is_not_empty', 'gt', 'lt', 'in'
    }

    # Field paths that can be queried (entry model paths)
    QUERYABLE_FIELDS = {
        'lexical_unit': 'lexical_unit/en',
        'lexical_unit.en': 'lexical_unit/en',
        'grammatical_info': 'grammatical_info/trait',
        'grammatical_info.trait': 'grammatical_info/trait',
        'traits': 'traits/*',
        'traits.*': 'traits/*',
        'sense': 'senses/*',
        'senses.*': 'senses/*',
        'senses.definition': 'senses/*/definition/*',
        'senses.gloss': 'senses/*/gloss/*',
        'senses.example': 'senses/*/examples/*',
    }

    def __init__(self, dictionary_service):
        """
        Initialize the BulkQueryService.

        Args:
            dictionary_service: DictionaryService instance for entry operations.
        """
        self.dictionary = dictionary_service

    def parse_condition(self, condition_data: Dict[str, Any]) -> Condition:
        """
        Parse a condition from JSON data.

        Args:
            condition_data: Condition dictionary with field, op, value keys.

        Returns:
            Condition object.

        Raises:
            ValueError: If condition is invalid.
        """
        # Handle compound conditions
        if 'and' in condition_data:
            and_group = []
            for c in condition_data['and']:
                and_group.append(self.parse_condition(c))
            return Condition(field='', op='and', value=and_group)

        if 'or' in condition_data:
            or_group = []
            for c in condition_data['or']:
                or_group.append(self.parse_condition(c))
            return Condition(field='', op='or', value=or_group)

        # Handle related conditions
        if 'related' in condition_data:
            related = condition_data['related']
            related_type = related.get('type')
            target_in_field = related.get('target_in_field')
            sub_condition = None
            if 'condition' in related:
                sub_condition = self.parse_condition(related['condition'])
            return Condition(
                field='',
                op='related',
                value=None,
                related_type=related_type,
                target_in_field=target_in_field,
                condition=sub_condition
            )

        # Regular field condition
        field = condition_data.get('field', '')
        op = condition_data.get('op', 'equals')
        value = condition_data.get('value')

        if not field:
            raise ValueError("Condition must have a 'field'")

        if op not in self.VALID_OPERATORS:
            raise ValueError(f"Invalid operator: {op}. Valid: {self.VALID_OPERATORS}")

        return Condition(field=field, op=op, value=value)

    def build_xquery(self, condition: Condition, entry_var: str = '$entry') -> Tuple[str, Dict[str, Any]]:
        """
        Build an XQuery expression from a condition.

        Args:
            condition: Condition to convert.
            entry_var: Variable name for entry in XQuery.

        Returns:
            Tuple of (xquery_where_clause, xquery_params_dict).
        """
        params = {}
        param_counter = [0]

        def next_param_name():
            param_counter[0] += 1
            return f'p{param_counter[0]}'

        def build_clause(cond: Condition) -> str:
            if cond.op == 'and':
                clauses = [build_clause(c) for c in cond.value]
                return f'({" and ".join(clauses)})'

            if cond.op == 'or':
                clauses = [build_clause(c) for c in cond.value]
                return f'({" or ".join(clauses)})'

            if cond.op == 'related':
                return build_related_clause(cond)

            # Regular field condition
            return build_field_clause(cond)

        def build_field_clause(cond: Condition) -> str:
            field_path = self._xquery_field_path(cond.field)
            param_name = next_param_name()
            params[param_name] = cond.value

            if cond.op == 'equals':
                return f'{entry_var}//*[local-name() = "{field_path}"][text() = ${param_name}]'
            elif cond.op == 'not_equals':
                return f'not({entry_var}//*[local-name() = "{field_path}"][text() = ${param_name}])'
            elif cond.op == 'contains':
                return f'{entry_var}//*[local-name() = "{field_path}"][contains(text(), ${param_name})]'
            elif cond.op == 'starts_with':
                return f'{entry_var}//*[local-name() = "{field_path}"][starts-with(text(), ${param_name})]'
            elif cond.op == 'ends_with':
                return f'{entry_var}//*[local-name() = "{field_path}"][ends-with(text(), ${param_name})]'
            elif cond.op == 'regex':
                # XQuery doesn't have native regex, use matches with flag
                return f'{entry_var}//*[local-name() = "{field_path}"][matches(text(), ${param_name})]'
            elif cond.op == 'is_empty':
                return f'not({entry_var}//*[local-name() = "{field_path}"][text()])'
            elif cond.op == 'is_not_empty':
                return f'{entry_var}//*[local-name() = "{field_path}"][text()]'
            elif cond.op == 'gt':
                return f'{entry_var}//*[local-name() = "{field_path}"][number(text()) > ${param_name}]'
            elif cond.op == 'lt':
                return f'{entry_var}//*[local-name() = "{field_path}"][number(text()) < ${param_name}]'
            elif cond.op == 'in':
                # Value is a list
                param_name_list = next_param_name()
                params[param_name_list] = cond.value
                return f'{entry_var}//*[local-name() = "{field_path}"][. = ${param_name_list}]'

            return 'true()'

        def build_related_clause(cond: Condition) -> str:
            """Build clause for related entry conditions."""
            if cond.target_in_field:
                # Look up target entry ID in a field
                target_path = self._xquery_field_path(cond.target_in_field)
                return f'{entry_var}/*[local-name() = "{target_path}"][@guid or @ref]'

            # Standard relation type lookup
            rel_type = cond.related_type or ''
            if cond.condition:
                sub_clause = build_clause(cond.condition)
                return f'{entry_var}/relation[@type = "{rel_type}"]/..[{sub_clause}]'

            return f'{entry_var}/relation[@type = "{rel_type}"]'

        return build_clause(condition), params

    def _xquery_field_path(self, field: str) -> str:
        """Convert field path to XQuery element names."""
        # Map field paths to XML element names
        mapping = {
            'lexical_unit': 'lexical-unit',
            'lexical_unit.en': 'form',
            'grammatical_info': 'grammatical-info',
            'grammatical_info.trait': 'grammatical-info',
            'sense': 'sense',
            'senses': 'sense',
            'senses.definition': 'definition',
            'senses.gloss': 'gloss',
            'senses.example': 'example',
            'examples': 'example',
            'pronunciation': 'pronunciation',
            'traits': 'trait',
        }

        # Handle array access like senses.0.definition
        parts = field.split('.')
        result = []
        for i, part in enumerate(parts):
            if part.isdigit():
                # Array index - skip in path, just indicate position
                continue
            if part in mapping:
                result.append(mapping[part])
            else:
                result.append(part)

        return '/'.join(result) if result else field

    def execute_query(
        self,
        condition: Condition,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[str], int]:
        """
        Execute a query and return matching entry IDs.

        Args:
            condition: Condition to match.
            limit: Maximum entries to return.
            offset: Pagination offset.

        Returns:
            Tuple of (entry_ids, total_count).
        """
        xquery_where, params = self.build_xquery(condition)

        db_name = self.dictionary.db_connector.database

        # Build full XQuery
        full_query = f"""
        let $entries := collection('{db_name}')/entry[{xquery_where}]
        let $total := count($entries)
        return concat(
            string($total),
            '|||',
            string-join(
                for $entry in $entries
                order by $entry/lexical-unit/form[1]/text[1]
                return string($entry/@id),
                '|||'
            )
        )
        """

        logger.debug(f"Executing bulk query: {full_query[:200]}...")
        logger.debug(f"Params: {params}")

        try:
            result = self.dictionary.db_connector.execute_query(full_query, params)

            if not result or not result.strip():
                return [], 0

            parts = result.split('|||')
            total = int(parts[0]) if parts[0] else 0
            entry_ids = parts[1:1 + limit] if len(parts) > 1 else []

            # Apply offset
            if offset > 0 and entry_ids:
                entry_ids = entry_ids[offset:offset + limit]
            elif offset > 0:
                entry_ids = []

            return entry_ids, total

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return [], 0

    def get_related_entries(
        self,
        entry_ids: List[str],
        relation_type: str
    ) -> Dict[str, List[str]]:
        """
        Get related entry IDs for each entry.

        Args:
            entry_ids: List of entry IDs.
            relation_type: Type of relation to follow.

        Returns:
            Dict mapping entry_id to list of related entry IDs.
        """
        if not entry_ids:
            return {}

        db_name = self.dictionary.db_connector.database

        # Build query for related entries
        placeholders = '|'.join([f"'${i}" for i in range(len(entry_ids))])
        param_dict = {f'p{i+1}': eid for i, eid in enumerate(entry_ids)}

        query = f"""
        for $entry in collection('{db_name}')/entry[@id = ({placeholders})]
        return concat(
            string($entry/@id),
            '|||',
            string-join(
                for $rel in $entry/relation[@type = "{relation_type}"]/@ref
                return string($rel),
                '|||'
            )
        )
        """

        try:
            result = self.dictionary.db_connector.execute_query(query, param_dict)

            related_map = {}
            if result and result.strip():
                for line in result.strip().split('\n'):
                    if '|||' in line:
                        parts = line.split('|||')
                        entry_id = parts[0]
                        related = parts[1:] if len(parts) > 1 else []
                        related_map[entry_id] = related

            return related_map

        except Exception as e:
            logger.error(f"Failed to get related entries: {e}")
            return {}

    def validate_condition(self, condition_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a condition structure.

        Args:
            condition_data: Condition to validate.

        Returns:
            Tuple of (is_valid, list_of_errors).
        """
        errors = []

        try:
            cond = self.parse_condition(condition_data)
            return True, []
        except ValueError as e:
            errors.append(str(e))
            return False, errors
        except Exception as e:
            errors.append(f"Invalid condition: {e}")
            return False, errors

    def query_entries(
        self,
        condition_data: Dict[str, Any],
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Query entries matching the specified conditions.

        Args:
            condition_data: Condition or conditions to match.
            limit: Maximum number of entries to return.
            offset: Number of entries to skip.

        Returns:
            Dict with 'total' count and 'entries' list.
        """
        try:
            # Handle compound conditions (and/or)
            if 'and' in condition_data or 'or' in condition_data:
                conditions = []
                if 'and' in condition_data:
                    for c in condition_data['and']:
                        conditions.append(self.parse_condition(c))
                    combined = Condition(
                        field='__and__',
                        op='and',
                        condition=Condition(field='__compound__', op='compound', value=conditions)
                    )
                else:
                    for c in condition_data['or']:
                        conditions.append(self.parse_condition(c))
                    combined = Condition(
                        field='__or__',
                        op='or',
                        condition=Condition(field='__compound__', op='compound', value=conditions)
                    )
                entries, total = self.execute_query(combined, limit, offset)
            else:
                # Single condition
                cond = self.parse_condition(condition_data)
                entries, total = self.execute_query(cond, limit, offset)

            return {
                'total': total,
                'entries': [e.to_dict() if hasattr(e, 'to_dict') else e for e in entries],
                'limit': limit,
                'offset': offset
            }

        except Exception as e:
            logger.error(f"Query entries failed: {e}")
            return {
                'total': 0,
                'entries': [],
                'error': str(e)
            }

class BulkActionService:
    """Service for executing bulk actions on entries."""

    # Fields that can be modified
    MODIFIABLE_FIELDS = {
        'lexical_unit': 'lexical_unit',
        'lexical_unit.en': 'lexical_unit',
        'grammatical_info': 'grammatical_info',
        'grammatical_info.trait': 'grammatical_info',
        'traits': 'traits',
        'senses': 'senses',
        'senses.*': 'senses',
        'senses.definition': 'senses_definition',
        'senses.gloss': 'senses_gloss',
        'senses.example': 'senses_example',
        'examples': 'examples',
        'pronunciation': 'pronunciation',
    }

    def __init__(self, dictionary_service):
        """
        Initialize the BulkActionService.

        Args:
            dictionary_service: DictionaryService instance.
        """
        self.dictionary = dictionary_service

    def validate_action(self, action: BulkAction) -> Tuple[bool, List[str]]:
        """
        Validate an action before execution.

        Args:
            action: Action to validate.

        Returns:
            Tuple of (is_valid, list_of_errors).
        """
        errors = []

        # Validate action type
        valid_actions = {a.value for a in ActionType}
        if action.action not in valid_actions:
            errors.append(f"Invalid action type: {action.action}")
            return False, errors

        # Validate field for field-modifying actions
        field_actions = {ActionType.SET.value, ActionType.CLEAR.value,
                        ActionType.APPEND.value, ActionType.PREPEND.value}
        if action.action in field_actions and not action.field:
            errors.append(f"Action '{action.action}' requires a field")

        # Validate relation actions
        relation_actions = {ActionType.ADD_RELATION.value, ActionType.REMOVE_RELATION.value}
        if action.action in relation_actions and not action.relation_type:
            errors.append(f"Action '{action.action}' requires relation_type")

        # Validate copy_from_related
        if action.action == ActionType.COPY_FROM_RELATED.value:
            if not action.from_field and not action.target_in_field:
                errors.append("copy_from_related requires from_field or target_in_field")
            if not action.to_field:
                errors.append("copy_from_related requires to_field")

        # Validate ranges if provided
        if action.ranges:
            errors.extend(self._validate_ranges(action))

        return len(errors) == 0, errors

    def _validate_ranges(self, action: BulkAction) -> List[str]:
        """Validate that action values are within allowed ranges.

        When ``action.ranges['range_id']`` is given, the value is checked against
        the dictionary's **actual LIFT range members** (the canonical source of
        truth, e.g. the ``part-of-speech`` range). The explicit ``allowed_values`` /
        ``allowed_types`` lists remain supported as a fallback for callers that
        supply their own lists.
        """
        errors: List[str] = []
        ranges = action.ranges or {}

        range_id = ranges.get('range_id')
        if range_id:
            member_values = self._canonical_range_values(range_id)
            if member_values is not None:  # None = range unknown/unresolvable → skip
                if action.value and action.value not in member_values:
                    errors.append(
                        f"Value '{action.value}' not in allowed values for range '{range_id}'"
                    )
                return errors

        if ranges.get('allowed_values'):
            if action.value and action.value not in ranges['allowed_values']:
                errors.append(f"Value '{action.value}' not in allowed values: {ranges['allowed_values']}")

        if ranges.get('allowed_types'):
            if action.relation_type and action.relation_type not in ranges['allowed_types']:
                errors.append(f"Relation type '{action.relation_type}' not in allowed types")

        return errors

    def _canonical_range_values(self, range_id: str) -> Optional[Set[str]]:
        """Resolve the member values of a LIFT range from the dictionary.

        Returns a set of member values, or ``None`` when the range cannot be
        resolved (dictionary unavailable, range unknown, or a lookup error) — the
        caller then skips the canonical check rather than blocking bulk actions.
        """
        dictionary = getattr(self, 'dictionary', None)
        if dictionary is None:
            return None
        try:
            getter = getattr(dictionary, 'get_lift_ranges', None)
            if not callable(getter):
                return None
            lift_ranges = getter() or {}
        except Exception as e:
            logger.debug("Could not load LIFT ranges for validation: %s", e)
            return None

        range_data = lift_ranges.get(range_id) if isinstance(lift_ranges, dict) else None
        if range_data is None:
            return None
        if not isinstance(range_data, dict):
            # Some parsers may return a bare list of elements for the range.
            elements = range_data if isinstance(range_data, list) else []
        else:
            elements = range_data.get('values') or range_data.get('elements') or []

        values: Set[str] = set()
        for element in elements:
            if not isinstance(element, dict):
                continue
            for key in ('value', 'id', 'abbrev'):
                v = element.get(key)
                if v:
                    values.add(str(v))
        return values or None

    def execute_action(
        self,
        entry_id: str,
        action: BulkAction,
        related_entries: Optional[Dict[str, Any]] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute a single action on an entry.

        Args:
            entry_id: Entry ID to modify.
            action: Action to execute.
            related_entries: Optional dict of related entry data for cross-entry ops.
            dry_run: If True, only return what would change.

        Returns:
            Result dict with status, entry_id, and change details.
        """
        try:
            entry = self.dictionary.get_entry(entry_id)
            if not entry:
                return {
                    'entry_id': entry_id,
                    'status': 'error',
                    'error': 'Entry not found'
                }

            # Store original state for diff
            original = DataCopier().copy(entry.to_dict())

            # Execute action based on type
            if action.action == ActionType.SET.value:
                result = self._action_set(entry, action)
            elif action.action == ActionType.CLEAR.value:
                result = self._action_clear(entry, action)
            elif action.action == ActionType.APPEND.value:
                result = self._action_append(entry, action)
            elif action.action == ActionType.PREPEND.value:
                result = self._action_prepend(entry, action)
            elif action.action == ActionType.ADD_RELATION.value:
                result = self._action_add_relation(entry, action, related_entries)
            elif action.action == ActionType.REMOVE_RELATION.value:
                result = self._action_remove_relation(entry, action)
            elif action.action == ActionType.REPLACE_RELATION.value:
                result = self._action_replace_relation(entry, action)
            elif action.action == ActionType.COPY_FROM_RELATED.value:
                result = self._action_copy_from_related(entry, action, related_entries)
            elif action.action == ActionType.PIPELINE.value:
                return self._action_pipeline(entry_id, action, related_entries, dry_run)
            else:
                return {
                    'entry_id': entry_id,
                    'status': 'error',
                    'error': f"Unknown action: {action.action}"
                }

            if dry_run:
                # Return diff without saving
                new_state = entry.to_dict()
                return {
                    'entry_id': entry_id,
                    'status': 'would_change',
                    'changes': self._compute_diff(original, new_state),
                    'dry_run': True
                }

            # Actually save the entry
            if result['status'] == 'changed':
                self.dictionary.update_entry(entry)

            return result

        except Exception as e:
            logger.error(f"Action execution failed for {entry_id}: {e}")
            return {
                'entry_id': entry_id,
                'status': 'error',
                'error': str(e)
            }

    def preview_action(
        self,
        entry_id: str,
        action_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Preview what would change without applying modifications.

        Args:
            entry_id: Entry ID to preview.
            action_data: Action dict with type, field, value, etc.

        Returns:
            Preview dict with change details.
        """
        try:
            # Build action object from dict
            action = BulkAction(
                action=action_data.get('type', 'set'),
                field=action_data.get('field'),
                value=action_data.get('value'),
                relation_type=action_data.get('relation_type'),
            )

            # Validate action
            errors = self.validate_action(action)
            if errors:
                return {
                    'id': entry_id,
                    'would_change': False,
                    'error': '; '.join(errors)
                }

            # Get entry without modifying
            entry = self.dictionary.get_entry(entry_id)
            if not entry:
                return {
                    'id': entry_id,
                    'would_change': False,
                    'error': 'Entry not found'
                }

            # Get current value
            current_value = self._get_field_value(entry, action.field)

            # Compute what would change
            would_change = True
            change_description = ''

            if action.action == ActionType.SET.value:
                new_value = action.value
                if current_value == new_value:
                    would_change = False
                else:
                    change_description = f"Would change {action.field} from '{current_value}' to '{new_value}'"
            elif action.action == ActionType.CLEAR.value:
                if current_value is None or current_value == '':
                    would_change = False
                else:
                    change_description = f"Would clear {action.field} (currently: '{current_value}')"
            elif action.action in (ActionType.APPEND.value, ActionType.PREPEND.value):
                new_value = str(current_value or '') + str(action.value) if action.action == ActionType.APPEND.value else str(action.value) + str(current_value or '')
                change_description = f"Would change {action.field} from '{current_value}' to '{new_value}'"
            elif action.action == ActionType.ADD_RELATION.value:
                change_description = f"Would add {action.relation_type or 'relation'} to target"
            elif action.action == ActionType.REMOVE_RELATION.value:
                change_description = f"Would remove {action.relation_type or 'relation'} relation"
            else:
                change_description = f"Would apply {action.action} to {action.field}"

            return {
                'id': entry_id,
                'would_change': would_change,
                'current_value': current_value,
                'new_value': action.value if action.action == ActionType.SET.value else None,
                'change_description': change_description
            }

        except Exception as e:
            logger.error(f"Preview failed for {entry_id}: {e}")
            return {
                'id': entry_id,
                'would_change': False,
                'error': str(e)
            }

    def _action_set(self, entry, action: BulkAction) -> Dict[str, Any]:
        """Execute set action."""
        field = action.field
        old_value = self._get_field_value(entry, field)
        self._set_field_value(entry, field, action.value)

        return {
            'entry_id': entry.id,
            'status': 'changed',
            'field': field,
            'old_value': old_value,
            'new_value': action.value
        }

    def _action_clear(self, entry, action: BulkAction) -> Dict[str, Any]:
        """Execute clear action."""
        field = action.field
        old_value = self._get_field_value(entry, field)
        self._set_field_value(entry, field, None)

        return {
            'entry_id': entry.id,
            'status': 'changed',
            'field': field,
            'old_value': old_value,
            'new_value': None
        }

    def _action_append(self, entry, action: BulkAction) -> Dict[str, Any]:
        """Execute append action."""
        field = action.field
        current = self._get_field_value(entry, field) or ''
        new_value = str(current) + str(action.value)
        self._set_field_value(entry, field, new_value)

        return {
            'entry_id': entry.id,
            'status': 'changed',
            'field': field,
            'old_value': current,
            'new_value': new_value
        }

    def _action_prepend(self, entry, action: BulkAction) -> Dict[str, Any]:
        """Execute prepend action."""
        field = action.field
        current = self._get_field_value(entry, field) or ''
        new_value = str(action.value) + str(current)
        self._set_field_value(entry, field, new_value)

        return {
            'entry_id': entry.id,
            'status': 'changed',
            'field': field,
            'old_value': current,
            'new_value': new_value
        }

    def _action_add_relation(
        self,
        entry,
        action: BulkAction,
        related_entries: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute add_relation action."""
        # Resolve target entry ID
        target_id = action.target_entry_id

        # Handle ${related.id} template
        if target_id and target_id.startswith('${') and related_entries:
            target_id = related_entries.get('id', target_id)

        if not target_id:
            return {
                'entry_id': entry.id,
                'status': 'error',
                'error': 'No target entry ID for relation'
            }

        # Check if relation already exists
        existing = entry.get_related_entries_by_type(action.relation_type)
        if any(r.ref == target_id for r in existing):
            return {
                'entry_id': entry.id,
                'status': 'skipped',
                'reason': 'Relation already exists'
            }

        # Add relation
        entry.add_relation(action.relation_type, target_id)

        return {
            'entry_id': entry.id,
            'status': 'changed',
            'relation_type': action.relation_type,
            'target_id': target_id,
            'action': 'added'
        }

    def _action_remove_relation(self, entry, action: BulkAction) -> Dict[str, Any]:
        """Execute remove_relation action."""
        target_id = action.target_entry_id

        if not target_id:
            return {
                'entry_id': entry.id,
                'status': 'error',
                'error': 'No target entry ID for relation'
            }

        # Remove relation
        removed = entry.remove_relation(action.relation_type, target_id)

        if removed:
            return {
                'entry_id': entry.id,
                'status': 'changed',
                'relation_type': action.relation_type,
                'target_id': target_id,
                'action': 'removed'
            }
        else:
            return {
                'entry_id': entry.id,
                'status': 'skipped',
                'reason': 'Relation not found'
            }

    def _action_replace_relation(self, entry, action: BulkAction) -> Dict[str, Any]:
        """Execute replace_relation action."""
        old_id = action.old_target
        new_id = action.new_target

        if not old_id or not new_id:
            return {
                'entry_id': entry.id,
                'status': 'error',
                'error': 'Both old_target and new_target required'
            }

        # Check if old relation exists
        existing = entry.get_related_entries_by_type(action.relation_type)
        if not any(r.ref == old_id for r in existing):
            return {
                'entry_id': entry.id,
                'status': 'skipped',
                'reason': 'Old relation not found'
            }

        # Replace relation
        entry.remove_relation(action.relation_type, old_id)
        entry.add_relation(action.relation_type, new_id)

        return {
            'entry_id': entry.id,
            'status': 'changed',
            'relation_type': action.relation_type,
            'old_target': old_id,
            'new_target': new_id
        }

    def _action_copy_from_related(
        self,
        entry,
        action: BulkAction,
        related_entries: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute copy_from_related action."""
        # Get source value
        source_value = None

        if action.target_in_field and related_entries:
            # Get value from related entry
            related_entry = related_entries.get('entry')
            if related_entry:
                source_value = self._get_field_value(related_entry, action.from_field)

        if source_value is None:
            return {
                'entry_id': entry.id,
                'status': 'skipped',
                'reason': 'No source value found'
            }

        # Get current target value
        current_target = self._get_field_value(entry, action.to_field)

        # Skip if target already has same value
        if current_target == source_value:
            return {
                'entry_id': entry.id,
                'status': 'skipped',
                'reason': 'Target already has same value'
            }

        # Copy value
        self._set_field_value(entry, action.to_field, source_value)

        return {
            'entry_id': entry.id,
            'status': 'changed',
            'from_field': action.from_field,
            'to_field': action.to_field,
            'old_value': current_target,
            'new_value': source_value
        }

    def _action_pipeline(
        self,
        entry_id: str,
        action: BulkAction,
        related_entries: Optional[Dict[str, Any]] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Execute pipeline of actions."""
        if not action.steps:
            return {
                'entry_id': entry_id,
                'status': 'error',
                'error': 'Pipeline has no steps'
            }

        results = []
        current_related = related_entries

        for i, step in enumerate(action.steps):
            result = self.execute_action(entry_id, step, current_related, dry_run)
            results.append({
                'step': i + 1,
                'action': step.action,
                'result': result
            })

            # Update related entries if step modified relations
            if step.action == ActionType.ADD_RELATION.value and result['status'] == 'changed':
                # Re-fetch entry to get updated relations
                entry = self.dictionary.get_entry(entry_id)
                if entry and step.relation_type:
                    related = entry.get_related_entries_by_type(step.relation_type)
                    if related:
                        current_related = {
                            'id': related[0].ref,
                            'entry': self.dictionary.get_entry(related[0].ref)
                        }

        return {
            'entry_id': entry_id,
            'status': 'completed',
            'steps': len(action.steps),
            'results': results
        }

    def _get_field_value(self, entry, field: str) -> Any:
        """Get field value from entry using dotted path."""
        parts = field.split('.')
        obj = entry

        for part in parts:
            if part.isdigit():
                # Array index
                if hasattr(obj, '__getitem__') and len(obj) > int(part):
                    obj = obj[int(part)]
                else:
                    return None
            elif hasattr(obj, part):
                obj = getattr(obj, part)
            elif isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                return None

        # Handle special cases
        if hasattr(obj, 'to_dict'):
            obj = obj.to_dict()
        elif hasattr(obj, '__iter__') and not isinstance(obj, str):
            obj = list(obj)

        return obj

    def _set_field_value(self, entry, field: str, value: Any) -> None:
        """Set field value on entry using dotted path."""
        parts = field.split('.')
        obj = entry
        parent = None
        last_part = parts[-1]

        # Navigate to parent
        for part in parts[:-1]:
            if part.isdigit():
                if hasattr(obj, '__getitem__'):
                    obj = obj[int(part)]
                else:
                    return
            elif hasattr(obj, part):
                parent = obj
                obj = getattr(obj, part)
                if hasattr(obj, 'to_dict'):
                    obj = obj.to_dict()
            else:
                return

        # Set value
        if hasattr(obj, last_part):
            if last_part == 'trait' and hasattr(obj, 'value'):
                # Handle grammatical_info trait
                obj.value = value
            elif hasattr(obj, last_part):
                setattr(obj, last_part, value)

    def _compute_diff(self, original: Dict, new: Dict) -> List[Dict]:
        """Compute diff between two entry dicts."""
        changes = []

        def compare(orig, nev, path=''):
            if isinstance(orig, dict) and isinstance(nev, dict):
                for key in set(orig.keys()) | set(nev.keys()):
                    opath = f'{path}.{key}' if path else key
                    if key not in orig:
                        changes.append({
                            'field': opath,
                            'old_value': None,
                            'new_value': nev[key]
                        })
                    elif key not in nev:
                        changes.append({
                            'field': opath,
                            'old_value': orig[key],
                            'new_value': None
                        })
                    elif orig[key] != nev[key]:
                        if not isinstance(orig[key], (dict, list)):
                            changes.append({
                                'field': opath,
                                'old_value': orig[key],
                                'new_value': nev[key]
                            })
                        else:
                            compare(orig[key], nev[key], opath)
            elif isinstance(orig, list) and isinstance(nev, list):
                if orig != nev:
                    changes.append({
                        'field': path,
                        'old_value': orig,
                        'new_value': nev
                    })

        compare(original, new)
        return changes

class BulkRollbackService:
    """Snapshot entry state before bulk ops and restore on rollback."""

    def __init__(self, dictionary_service: Optional[DictionaryService] = None):
        self._dictionary_service = dictionary_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @staticmethod
    def generate_op_id() -> str:
        """Generate a unique, human-readable operation ID."""
        ts = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
        short = uuid4().hex[:8]
        return f'bulk-{ts}-{short}'

    def record_snapshot(self, bulk_op_id: str, entry_data: dict) -> bool:
        """Persist a single entry snapshot under *bulk_op_id*.

        Returns True if a snapshot was recorded, False if the entry lacked an id.
        """
        entry_id = entry_data.get('id')
        if not entry_id:
            logger.warning('record_snapshot skipped entry with no id')
            return False

        # Upsert: remove old snapshot for this (op, entry) pair, then insert.
        BulkOperationSnapshot.query.filter_by(
            bulk_op_id=bulk_op_id,
            entry_id=entry_id,
        ).delete()
        db.session.flush()

        snap = BulkOperationSnapshot(
            bulk_op_id=bulk_op_id,
            entry_id=entry_id,
            snapshot=entry_data,
        )
        db.session.add(snap)
        db.session.commit()
        return True

    def record_bulk_op_snapshots(self, bulk_op_id: str,
                                 entry_ids: list[str]) -> int:
        """Snapshot every entry in *entry_ids* under *bulk_op_id*.

        Returns the number of successful snapshots.
        """
        count = 0
        for eid in entry_ids:
            data = self._snapshot_entry(eid)
            if data is not None:
                if self.record_snapshot(bulk_op_id, data):
                    count += 1
        return count

    def _snapshot_entry(self, entry_id: str) -> Optional[dict]:
        """Fetch a single entry and return its dict representation."""
        if not self._dictionary_service:
            return None
        try:
            entry = self._dictionary_service.get_entry(entry_id)
            if entry is None:
                return None
            return self._get_entry_snapshot(entry)
        except Exception as exc:
            logger.error('snapshot failed for entry %s: %s', entry_id, exc)
            return None

    def rollback(self, bulk_op_id: str) -> dict:
        """Restore every entry snapshotted under *bulk_op_id*.

        Returns dict with keys ``restored``, ``failed``, ``skipped``.
        """
        rows = self._get_snapshots(bulk_op_id)
        result = RollbackResult()

        for row in rows:
            entry_id = row['entry_id']
            snapshot = row['snapshot']

            try:
                self._restore_entry(snapshot)
                result.restored += 1
                logger.info('rollback: restored entry %s', entry_id)
            except LookupError:
                result.skipped += 1
                logger.warning('rollback: entry %s not found, skipping', entry_id)
            except Exception as exc:
                logger.error('rollback: failed to restore entry %s: %s',
                             entry_id, exc)
                result.failed += 1

        # Clean up snapshots
        self.delete_snapshots(bulk_op_id)

        return {
            'restored': result.restored,
            'failed': result.failed,
            'skipped': result.skipped,
            'total': len(rows),
        }

    def delete_snapshots(self, bulk_op_id: str) -> None:
        """Remove all snapshots for a bulk operation."""
        BulkOperationSnapshot.query.filter_by(
            bulk_op_id=bulk_op_id,
        ).delete()
        db.session.commit()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_entry_snapshot(self, entry) -> Optional[dict]:
        """Get a snapshot dict from an entry object."""
        if hasattr(entry, 'to_dict'):
            return entry.to_dict()
        if isinstance(entry, dict):
            return entry
        return None

    def _restore_entry(self, snapshot: dict) -> None:
        """Write snapshot data back to the database.

        Raises:
            KeyError: If the snapshot has no id.
            LookupError: If the entry does not exist in the database.
        """
        if not self._dictionary_service:
            return
        entry_id = snapshot.get('id')
        if not entry_id:
            raise KeyError('Snapshot has no id')
        entry = self._dictionary_service.get_entry(entry_id)
        if entry is None:
            raise LookupError(f'Entry {entry_id} not found')
        entry.update_from_dict(snapshot)
        self._dictionary_service.update_entry(entry)

    def _get_snapshots(self, bulk_op_id: str) -> list[dict]:
        """Return all snapshot rows for a bulk operation as plain dicts."""
        rows = BulkOperationSnapshot.query.filter_by(
            bulk_op_id=bulk_op_id,
        ).order_by(BulkOperationSnapshot.id).all()
        return [
            {
                'entry_id': r.entry_id,
                'snapshot': r.snapshot,
                'created_utc': r.created_utc.isoformat() if r.created_utc else None,
            }
            for r in rows
        ]

class BulkService(BulkOperationsService, BulkActionService, BulkQueryService, BulkRollbackService):
    """Unified facade over the four bulk concerns.

    One instance exposes querying (BulkQueryService), action-based edits
    (BulkActionService), atomic bulk operations (BulkOperationsService) and
    snapshot rollback (BulkRollbackService). All consumers can inject this
    single service instead of four parallel ones.
    """

    def __init__(self, dictionary_service=None, workset_service=None, history_service=None):
        BulkOperationsService.__init__(self, dictionary_service, workset_service, history_service)
        BulkActionService.__init__(self, dictionary_service)
        BulkQueryService.__init__(self, dictionary_service)
        BulkRollbackService.__init__(self, dictionary_service)
