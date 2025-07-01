#!/usr/bin/env python3

"""
Query Builder service for dynamic query construction and validation.
Implements workbench-oriented query functionality.
"""

from __future__ import annotations

from typing import Dict, Any, List, Union
import logging
import uuid
import re
from datetime import datetime

from app.models.workset import WorksetQuery, QueryFilter, Workset
from app.services.workset_service import WorksetService
from app.api.entries import get_dictionary_service

logger = logging.getLogger(__name__)


class SavedQuery:
    """Saved query model."""
    
    def __init__(self, id_: str, name: str, description: str, query: Dict[str, Any], created_at: datetime):
        self.id = id_
        self.name = name
        self.description = description
        self.query = query
        self.created_at = created_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'query': self.query,
            'created_at': self.created_at.isoformat()
        }


class CrossReference:
    """Represents a cross-reference to another query element."""
    
    def __init__(self, element_index: int, field: str):
        self.element_index = element_index
        self.field = field
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'element_reference',
            'element_index': self.element_index,
            'field': self.field
        }


class QueryBuilderService:
    """Service for dynamic query building and validation."""
    
    def __init__(self):
        self._saved_queries: Dict[str, SavedQuery] = {}
        self._cross_ref_pattern = re.compile(r'\[ELEMENT\s+(\d+):([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\]')
    
    def validate_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate query syntax and estimate performance."""
        try:
            validation_errors = []
            
            # Parse cross-references first
            filters = self._parse_cross_references(query_data.get('filters', []))
            
            # Validate cross-references
            cross_ref_errors = self._validate_cross_references(filters)
            validation_errors.extend(cross_ref_errors)
            
            # Validate filters
            for i, filter_data in enumerate(filters):
                if not isinstance(filter_data, dict):
                    validation_errors.append(f"Filter {i+1}: Invalid filter format")
                    continue
                
                field = filter_data.get('field')
                operator = filter_data.get('operator')
                value = filter_data.get('value')
                
                # Validate field - comprehensive LIFT schema fields
                valid_fields = [
                # Entry-level fields
                'lexical_unit', 'lexical_unit.lang', 'headword',
                    'grammatical_info', 'pos', 'pronunciation', 'pronunciation.ipa',
                'citation', 'note', 'custom_field',
                
                # Etymology fields  
                'etymology.source', 'etymology.type', 'etymology.form', 'etymology.gloss',
                
                # Relation fields
                'relation.type', 'relation.ref', 'relation.target',
                
                # Variant fields
                'variant.form', 'variant.type',
                
                # Sense-level fields
                'sense.definition', 'sense.gloss', 'sense.grammatical_info',
                'sense.semantic_domain', 'sense.note', 'sense.custom_field',
                
                # Example fields
                'sense.example', 'sense.example.translation',
                
                # Cross-entry comparison fields
                'similar_headword', 'contains_headword', 'normalized_headword',
                'duplicate_candidate', 'compound_component'
            ]
                if field not in valid_fields:
                    validation_errors.append(f"Filter {i+1}: Invalid field '{field}'")
                
                # Validate operator
                valid_operators = [
                    # Basic string operators
                    'equals', 'contains', 'starts_with', 'ends_with',
                    'regex', 'not_equals', 'not_contains',
                    
                    # Numerical operators
                    'greater_than', 'less_than', 'greater_equal', 'less_equal',
                    
                    # List operators
                    'in', 'not_in', 'contains_any', 'contains_all',
                    
                    # Similarity operators for duplicate detection
                    'similar_to', 'levenshtein_distance', 'phonetic_similar',
                    'normalized_equals', 'fuzzy_match',
                    
                    # Cross-entry comparison operators
                    'headword_contained_in', 'contains_as_component',
                    'shares_root_with', 'same_pos_as',
                    
                    # Existence operators
                    'exists', 'not_exists', 'is_empty', 'is_not_empty'
                ]
                if operator not in valid_operators:
                    validation_errors.append(f"Filter {i+1}: Invalid operator '{operator}'")
                
                # Validate value
                if value is None or value == '':
                    validation_errors.append(f"Filter {i+1}: Value cannot be empty")
            
            # Validate sort options
            sort_by = query_data.get('sort_by')
            if sort_by and sort_by not in ['lexical_unit', 'pos', 'created_at', 'updated_at']:
                validation_errors.append(f"Invalid sort field: {sort_by}")
            
            sort_order = query_data.get('sort_order', 'asc')
            if sort_order not in ['asc', 'desc']:
                validation_errors.append(f"Invalid sort order: {sort_order}")
            
            # Get real estimate by actually querying the database
            try:
                search_params = self._build_search_params(filters)
                dict_service = get_dictionary_service()
                
                # Use the same search logic as preview but just get the count
                if search_params.get('advanced_query'):
                    # For advanced queries, do a limited search to estimate
                    entries, estimated_count = dict_service.search_entries(
                        search_params.get('query', ''),
                        fields=search_params.get('fields'),
                        limit=1000,  # Large limit to get better count estimate
                        offset=0
                    )
                else:
                    # For basic queries, use standard search
                    entries, estimated_count = dict_service.search_entries(
                        search_params.get('query', ''),
                        fields=search_params.get('fields'),
                        limit=1000,
                        offset=0
                    )
                
                # Estimate performance based on result count and query complexity
                filter_count = len(filters)
                if estimated_count > 5000 or filter_count > 5:
                    performance_score = 'slow'
                elif estimated_count > 1000 or filter_count > 2:
                    performance_score = 'medium'
                else:
                    performance_score = 'fast'
                    
            except Exception as e:
                logger.warning(f"Failed to get real estimate, using fallback: {e}")
                # Fallback to conservative estimate
                estimated_count = 50
                performance_score = 'medium'
            
            return {
                'valid': len(validation_errors) == 0,
                'estimated_count': estimated_count,
                'performance_score': performance_score,
                'validation_errors': validation_errors
            }
            
        except Exception as e:
            logger.error(f"Error validating query: {e}")
            return {
                'valid': False,
                'estimated_count': 0,
                'performance_score': 'unknown',
                'validation_errors': [str(e)]
            }
    
    def preview_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get preview results for query using real dictionary service."""
        try:
            limit = min(query_data.get('limit', 5), 20)  # Cap at 20 for performance
            
            # Get dictionary service for real searches
            dict_service = get_dictionary_service()
            
            # Build real search query from filters
            search_params = self._build_search_params(query_data.get('filters', []))
            
            # Execute real search - use the same logic as validation for consistency
            entries, total_count = dict_service.search_entries(
                search_params.get('query', ''),
                fields=search_params.get('fields'),
                limit=limit,
                offset=0
            )
            
            # Convert entries to dict format for JSON serialization
            preview_entries = []
            for entry in entries:
                if hasattr(entry, 'to_dict'):
                    preview_entries.append(entry.to_dict())
                else:
                    preview_entries.append(entry)
            
            return {
                'preview_entries': preview_entries,
                'total_count': total_count,
                'search_params': search_params,  # For debugging
                'query_debug': {
                    'filters_count': len(query_data.get('filters', [])),
                    'search_query': search_params.get('query', ''),
                    'search_fields': search_params.get('fields', []),
                    'advanced_query': search_params.get('advanced_query', False)
                }
            }
            
        except Exception as e:
            logger.error(f"Error previewing query: {e}")
            return {
                'preview_entries': [],
                'total_count': 0,
                'error': str(e)
            }
    
    def _build_search_params(self, filters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build search parameters from query filters."""
        if not filters:
            # If no filters, return a query that will match all entries
            return {
                'query': '',  # Empty query searches all
                'fields': ['lexical_unit', 'definitions', 'glosses'], 
                'advanced_query': False
            }
        
        # Simple text search for basic queries
        basic_text_queries = []
        advanced_filters = {}
        fields_to_search = []
        is_advanced = False
        
        for filter_data in filters:
            field = filter_data.get('field', '')
            operator = filter_data.get('operator', '')
            value = filter_data.get('value', '')
            
            # Handle basic text searches
            if operator in ['contains', 'equals', 'starts_with'] and field in ['lexical_unit', 'headword']:
                if operator == 'contains':
                    basic_text_queries.append(value)
                elif operator == 'equals':
                    basic_text_queries.append(f'"{value}"')
                elif operator == 'starts_with':
                    basic_text_queries.append(f'{value}*')
                fields_to_search.append('lexical_unit')
                
            elif field.startswith('sense.'):
                # Sense-level searches
                sense_field = field.replace('sense.', '')
                if sense_field in ['definition', 'gloss']:
                    basic_text_queries.append(value)
                    fields_to_search.extend(['definitions', 'glosses'])
                else:
                    advanced_filters[field] = {'operator': operator, 'value': value}
                    is_advanced = True
                    
            elif operator in ['similar_to', 'normalized_equals', 'fuzzy_match', 'levenshtein_distance']:
                # Advanced similarity operators
                advanced_filters[field] = {'operator': operator, 'value': value}
                is_advanced = True
                
            else:
                # Other advanced filters
                advanced_filters[field] = {'operator': operator, 'value': value}
                is_advanced = True
        
        # Combine basic text queries
        combined_query = ' '.join(basic_text_queries) if basic_text_queries else ''
        
        return {
            'query': combined_query,
            'fields': list(set(fields_to_search)) if fields_to_search else ['lexical_unit', 'definitions', 'glosses'],
            'filters': advanced_filters,
            'advanced_query': is_advanced
        }
    
    def save_query(self, save_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save a named query for reuse."""
        try:
            query_id = str(uuid.uuid4())
            
            saved_query = SavedQuery(
                id_=query_id,
                name=save_data['name'],
                description=save_data.get('description', ''),
                query=save_data['query'],
                created_at=datetime.now()
            )
            
            self._saved_queries[query_id] = saved_query
            
            logger.info(f"Saved query: {save_data['name']}")
            
            return {
                'success': True,
                'query_id': query_id,
                'name': save_data['name']
            }
            
        except Exception as e:
            logger.error(f"Error saving query: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_saved_queries(self) -> Dict[str, Any]:
        """Get list of saved queries."""
        try:
            queries = []
            for saved_query in self._saved_queries.values():
                queries.append({
                    'id': saved_query.id,
                    'name': saved_query.name,
                    'description': saved_query.description,
                    'created_at': saved_query.created_at.isoformat()
                })
            
            # Sort by creation date (newest first)
            queries.sort(key=lambda q: q['created_at'], reverse=True)
            
            return {'queries': queries}
            
        except Exception as e:
            logger.error(f"Error getting saved queries: {e}")
            return {'queries': []}
    
    def execute_query(self, execute_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute query and create workset."""
        try:
            # Convert query to WorksetQuery format
            query_dict = execute_data['query']
            filters = []
            
            for filter_data in query_dict.get('filters', []):
                filters.append(QueryFilter(
                    field=filter_data['field'],
                    operator=filter_data['operator'],
                    value=filter_data['value']
                ))
            
            workset_query = WorksetQuery(
                filters=filters,
                sort_by=query_dict.get('sort_by'),
                sort_order=query_dict.get('sort_order', 'asc')
            )
            
            # Create workset using workset service
            workset_service = WorksetService()
            workset = workset_service.create_workset(
                name=execute_data['workset_name'],
                query=workset_query
            )
            
            logger.info(f"Created workset '{workset.name}' with {workset.total_entries} entries")
            
            return {
                'success': True,
                'workset_id': workset.id,
                'entry_count': workset.total_entries,
                'workset_name': workset.name
            }
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _parse_cross_references(self, filters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse cross-reference syntax in filter values."""
        parsed_filters = []
        
        for filter_data in filters:
            parsed_filter = filter_data.copy()
            value = filter_data.get('value', '')
            
            if isinstance(value, str):
                # Check for cross-reference pattern
                match = self._cross_ref_pattern.match(value.strip())
                if match:
                    try:
                        element_index = int(match.group(1))
                        field = match.group(2)
                        parsed_filter['value'] = {
                            'type': 'element_reference',
                            'element_index': element_index,
                            'field': field
                        }
                    except (ValueError, IndexError):
                        # Keep original value if parsing fails
                        pass
            
            parsed_filters.append(parsed_filter)
        
        return parsed_filters
    
    def _validate_cross_references(self, filters: List[Dict[str, Any]]) -> List[str]:
        """Validate cross-references in filters."""
        errors = []
        
        for i, filter_data in enumerate(filters):
            value = filter_data.get('value')
            
            # Check for invalid cross-reference syntax (starts with [ELEMENT but didn't parse)
            if isinstance(value, str) and value.strip().startswith('[ELEMENT'):
                # This should have been parsed if it was valid
                errors.append(f"Filter {i+1}: Invalid cross-reference syntax '{value}'")
                continue
            
            if isinstance(value, dict) and value.get('type') == 'element_reference':
                element_index = value.get('element_index')
                field = value.get('field')
                
                # Check if referenced element exists (1-based indexing)
                if element_index < 1 or element_index > len(filters):
                    errors.append(f"Filter {i+1}: Element {element_index} does not exist")
                    continue
                
                # Check for self-reference
                if element_index == i + 1:  # Convert to 1-based
                    errors.append(f"Filter {i+1}: Cannot reference itself")
                    continue
                
                # Check if referenced field is valid
                valid_fields = [
                    'lexical_unit', 'lexical_unit.lang', 'headword',
                    'grammatical_info', 'pos', 'pronunciation', 'pronunciation.ipa',
                    'citation', 'note', 'custom_field',
                    'etymology.source', 'etymology.type', 'etymology.form', 'etymology.gloss',
                    'relation.type', 'relation.ref', 'relation.target',
                    'variant.form', 'variant.type',
                    'sense.definition', 'sense.gloss', 'sense.grammatical_info',
                    'sense.semantic_domain', 'sense.note', 'sense.custom_field',
                    'sense.example', 'sense.example.translation',
                    'similar_headword', 'contains_headword', 'normalized_headword',
                    'duplicate_candidate', 'compound_component'
                ]
                
                if field not in valid_fields:
                    errors.append(f"Filter {i+1}: Invalid referenced field '{field}'")
        
        # Check for circular dependencies
        circular_errors = self._detect_circular_dependencies(filters)
        errors.extend(circular_errors)
        
        return errors
    
    def _detect_circular_dependencies(self, filters: List[Dict[str, Any]]) -> List[str]:
        """Detect circular dependencies in cross-references."""
        errors = []
        dependencies = {}
        
        # Build dependency graph
        for i, filter_data in enumerate(filters):
            value = filter_data.get('value')
            if isinstance(value, dict) and value.get('type') == 'element_reference':
                element_index = value.get('element_index')
                dependencies[i + 1] = element_index  # Use 1-based indexing
        
        # Check for cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: int) -> bool:
            if node in rec_stack:
                return True
            if node in visited:
                return False
            
            visited.add(node)
            rec_stack.add(node)
            
            if node in dependencies:
                if has_cycle(dependencies[node]):
                    return True
            
            rec_stack.remove(node)
            return False
        
        for node in dependencies:
            if has_cycle(node):
                errors.append(f"Circular dependency detected involving element {node}")
                break
        
        return errors
    
    def _plan_execution_order(self, filters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Plan execution order to resolve dependencies."""
        # Parse cross-references first to understand dependencies
        parsed_filters = self._parse_cross_references(filters)
        
        # Build dependency graph
        dependencies = {}
        
        for i, filter_data in enumerate(parsed_filters):
            value = filter_data.get('value')
            if isinstance(value, dict) and value.get('type') == 'element_reference':
                element_index = value.get('element_index')
                dependencies[i] = element_index - 1  # Convert to 0-based
        
        # Simple topological sort
        visited = set()
        execution_order = []
        
        def visit(node: int):
            if node in visited:
                return
            visited.add(node)
            
            # Visit dependencies first
            if node in dependencies:
                visit(dependencies[node])
            
            execution_order.append({
                'original_index': node,
                'filter': parsed_filters[node]
            })
        
        for i in range(len(parsed_filters)):
            visit(i)
        
        return execution_order
    
    def get_available_references(self, filters: List[Dict[str, Any]], current_index: int) -> List[Dict[str, Any]]:
        """Get available element references for a given filter position."""
        available_refs = []
        
        for i, filter_data in enumerate(filters):
            # Only show elements before current position
            if i < current_index:
                field = filter_data.get('field', '')
                available_refs.append({
                    'index': i + 1,  # 1-based indexing for display
                    'field': field,
                    'display': f'Element {i + 1}: {field}'
                })
        
        return available_refs
    
    def format_cross_reference_display(self, cross_ref: Dict[str, Any]) -> str:
        """Format cross-reference for display."""
        if cross_ref.get('type') == 'element_reference':
            element_index = cross_ref.get('element_index')
            field = cross_ref.get('field')
            return f'[ELEMENT {element_index}:{field}]'
        return str(cross_ref)
