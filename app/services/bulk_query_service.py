"""
Bulk Query Service - Query building and execution for bulk operations.

Provides condition parsing and execution for finding entries matching
complex criteria including field conditions, relational conditions,
and compound AND/OR conditions.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import logging
import re

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
