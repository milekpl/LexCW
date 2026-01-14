from __future__ import annotations
from typing import Dict, Tuple, Any
from app.models.search_query import SearchQuery, SearchFilter

class DynamicQueryBuilder:
    """
    Dynamic query builder for generating database-specific queries.
    Supports both XQuery (for BaseX/LIFT data) and SQL (for PostgreSQL).
    """
    
    def __init__(self, dialect: str) -> None:
        self.dialect = dialect

    def build_query(self, query: SearchQuery) -> Tuple[str, Dict[str, Any]]:
        """
        Build a query string and parameters based on the search query.
        
        Args:
            query: SearchQuery object containing search criteria
            
        Returns:
            Tuple of (query_string, parameters_dict)
        """
        if self.dialect == "postgresql":
            return self._build_sql_query(query)
        elif self.dialect == "xquery":
            return self._build_xquery(query)
        else:
            raise NotImplementedError(f"Dialect {self.dialect} not supported")
    
    def _build_sql_query(self, query: SearchQuery) -> Tuple[str, Dict[str, Any]]:
        """Build SQL query for PostgreSQL."""
        # Keep existing SQL logic for corpus searches
        return "SELECT * FROM entries WHERE lexical_unit_text LIKE %(keyword_1)s", {"keyword_1": f"%{query.keywords[0]}%"}
    
    def _build_xquery(self, query: SearchQuery) -> Tuple[str, Dict[str, Any]]:
        """
        Build XQuery for BaseX LIFT database.
        
        Generates XQuery expressions to search within LIFT XML structure.
        """
        params: Dict[str, Any] = {}
        conditions: list[str] = []
        param_counter = 1
        
        # Handle keyword searches in lexical-unit forms
        for i, keyword in enumerate(query.keywords, 1):
            param_name = f"keyword{i}"
            params[param_name] = keyword
            conditions.append(f"$entry/lexical-unit/form/text[contains(., ${param_name})]")
        
        # Handle field-specific filters
        for filter_item in query.filters:
            param_name = f"param{param_counter}"
            params[param_name] = filter_item.value
            
            xpath_condition = self._build_xpath_condition(filter_item, param_name)
            if xpath_condition:
                conditions.append(xpath_condition)
            
            param_counter += 1
        
        # Build the complete XQuery
        if conditions:
            where_clause = " and ".join(conditions)
            xquery = f'''for $entry in collection("lift")//entry
where {where_clause}
return $entry'''
        else:
            # No conditions - return all entries
            xquery = '''for $entry in collection("lift")//entry
return $entry'''
        
        return xquery, params
    
    def _build_xpath_condition(self, filter_item: SearchFilter, param_name: str) -> str:
        """
        Build XPath condition for a specific filter.
        
        Maps field names to appropriate LIFT XML paths.
        """
        field_mappings = {
            "sense.definition": f"$entry/sense/definition/form/text[contains(., ${param_name})]",
            "grammatical-info.value": f"$entry/sense/grammatical-info/@value = ${param_name}",
            "etymology.source": f"$entry/etymology/@source[contains(., ${param_name})]",
            "relation.type": f"$entry/relation[@type = ${param_name}]",
            "variant.form": f"$entry/variant/form/text[contains(., ${param_name})]",
            "note.type": f"$entry/note[@type = ${param_name}]",
            "pronunciation.form": f"$entry/pronunciation/form/text[contains(., ${param_name})]",
            "citation.form": f"$entry/citation/form/text[contains(., ${param_name})]",
        }
        
        if filter_item.field in field_mappings:
            if filter_item.operator == "contains":
                # For contains operations, the mapping already includes contains()
                return field_mappings[filter_item.field]
            elif filter_item.operator == "equals":
                # For equals operations, adjust the mapping
                base_path = field_mappings[filter_item.field]
                if "contains(" in base_path:
                    # Replace contains with exact match
                    return base_path.replace(f"[contains(., ${param_name})]", f"[. = ${param_name}]")
                else:
                    # Already an exact match
                    return base_path
        
        # If field not found in mappings, return empty string (will be filtered out)
        return ""
