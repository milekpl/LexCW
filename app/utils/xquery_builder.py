"""
XQuery builder utilities for LIFT database operations.

This module provides utilities for building namespace-aware XQuery expressions
for LIFT XML operations in BaseX database.
"""

from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class XQueryBuilder:
    """
    Builder for LIFT-specific XQuery queries with proper namespace handling.
    """

    # LIFT namespace constants
    LIFT_NAMESPACE = "http://fieldworks.sil.org/schemas/lift/0.13"
    FLEX_NAMESPACE = "http://fieldworks.sil.org/schemas/flex/0.1"

    @staticmethod
    def get_namespace_prologue(has_lift_namespace: bool = True) -> str:
        """
        Get XQuery prologue with namespace declarations.

        Args:
            has_lift_namespace: Whether to include LIFT namespace declarations

        Returns:
            XQuery prologue string
        """
        if has_lift_namespace:
            return f"""
            declare namespace lift = "{XQueryBuilder.LIFT_NAMESPACE}";
            declare namespace flex = "{XQueryBuilder.FLEX_NAMESPACE}";
            """
        return ""

    @staticmethod
    def get_element_path(element_name: str, has_namespace: bool = True) -> str:
        """
        Get element path with appropriate namespace prefix.

        Args:
            element_name: Name of the element
            has_namespace: Whether to use namespace prefix

        Returns:
            Element path string
        """
        if has_namespace:
            return f"lift:{element_name}"
        return element_name

    @staticmethod
    def build_entry_by_id_query(
        entry_id: str, db_name: str, has_namespace: bool = True
    ) -> str:
        """
        Build query to retrieve entry by ID.

        Args:
            entry_id: ID of the entry to retrieve
            db_name: Name of the database
            has_namespace: Whether XML uses namespaces

        Returns:
            Complete XQuery string
        """
        prologue = XQueryBuilder.get_namespace_prologue(has_namespace)
        entry_path = XQueryBuilder.get_element_path("entry", has_namespace)

        return f"""{prologue}
        for $entry in collection('{db_name}')//{entry_path}[@id="{entry_id}"]
        return $entry
        """

    @staticmethod
    def build_all_entries_query(
        db_name: str,
        has_namespace: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """
        Build query to retrieve all entries with optional pagination.

        Args:
            db_name: Name of the database
            has_namespace: Whether XML uses namespaces
            limit: Maximum number of entries to return
            offset: Number of entries to skip

        Returns:
            Complete XQuery string
        """
        prologue = XQueryBuilder.get_namespace_prologue(has_namespace)
        entry_path = XQueryBuilder.get_element_path("entry", has_namespace)

        query = f"""{prologue}
        for $entry in collection('{db_name}')//{entry_path}
        """

        if offset:
            query += f"\n        where position() > {offset}"

        query += "\n        return $entry"

        if limit:
            query = f"({query})[position() <= {limit}]"

        return query

    @staticmethod
    def build_search_query(
        search_term: str,
        db_name: str,
        has_namespace: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """
        Build query to search entries.

        Args:
            search_term: Term to search for
            db_name: Name of the database
            has_namespace: Whether XML uses namespaces
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Complete XQuery string
        """
        prologue = XQueryBuilder.get_namespace_prologue(has_namespace)
        entry_path = XQueryBuilder.get_element_path("entry", has_namespace)

        query = f"""{prologue}
        for $entry in collection('{db_name}')//{entry_path}
        where contains(string($entry), "{search_term}")
        """

        if offset:
            query += f"\n        and position() > {offset}"

        query += "\n        return $entry"

        if limit:
            query = f"({query})[position() <= {limit}]"

        return query

    @staticmethod
    def build_count_entries_query(
        db_name: str, has_namespace: bool = True, search_term: Optional[str] = None
    ) -> str:
        """
        Build query to count entries.

        Args:
            db_name: Name of the database
            has_namespace: Whether XML uses namespaces
            search_term: Optional search term to filter entries

        Returns:
            Complete XQuery string
        """
        prologue = XQueryBuilder.get_namespace_prologue(has_namespace)
        entry_path = XQueryBuilder.get_element_path("entry", has_namespace)

        base_query = f"collection('{db_name}')//{entry_path}"

        if search_term:
            query = f"""{prologue}
            count(for $entry in {base_query}
                  where contains(string($entry), "{search_term}")
                  return $entry)
            """
        else:
            query = f"""{prologue}
            count({base_query})
            """

        return query

    @staticmethod
    def build_insert_entry_query(
        entry_xml: str, db_name: str, has_namespace: bool = True
    ) -> str:
        """
        Build query to insert new entry.

        Args:
            entry_xml: XML string of the entry to insert
            db_name: Name of the database
            has_namespace: Whether XML uses namespaces

        Returns:
            Complete XQuery string
        """
        prologue = XQueryBuilder.get_namespace_prologue(has_namespace)
        lift_path = XQueryBuilder.get_element_path("lift", has_namespace)

        return f"""{prologue}
        insert node {entry_xml} into collection('{db_name}')//{lift_path}
        """

    @staticmethod
    def build_update_entry_query(
        entry_id: str, entry_xml: str, db_name: str, has_namespace: bool = True
    ) -> str:
        """
        Build query to update existing entry.

        Args:
            entry_id: ID of the entry to update
            entry_xml: New XML content for the entry
            db_name: Name of the database
            has_namespace: Whether XML uses namespaces

        Returns:
            Complete XQuery string
        """
        prologue = XQueryBuilder.get_namespace_prologue(has_namespace)
        entry_path = XQueryBuilder.get_element_path("entry", has_namespace)

        return f"""{prologue}
        replace node collection('{db_name}')//{entry_path}[@id="{entry_id}"]
        with {entry_xml}
        """

    @staticmethod
    def build_delete_entry_query(
        entry_id: str, db_name: str, has_namespace: bool = True
    ) -> str:
        """
        Build query to delete entry.

        Args:
            entry_id: ID of the entry to delete
            db_name: Name of the database
            has_namespace: Whether XML uses namespaces

        Returns:
            Complete XQuery string
        """
        prologue = XQueryBuilder.get_namespace_prologue(has_namespace)
        entry_path = XQueryBuilder.get_element_path("entry", has_namespace)

        return f"""{prologue}
        delete node collection('{db_name}')//{entry_path}[@id="{entry_id}"]
        """

    @staticmethod
    def build_statistics_query(db_name: str, has_namespace: bool = True) -> str:
        """
        Build query to get database statistics.

        Args:
            db_name: Name of the database
            has_namespace: Whether XML uses namespaces

        Returns:
            Complete XQuery string
        """
        prologue = XQueryBuilder.get_namespace_prologue(has_namespace)
        entry_path = XQueryBuilder.get_element_path("entry", has_namespace)
        sense_path = XQueryBuilder.get_element_path("sense", has_namespace)
        example_path = XQueryBuilder.get_element_path("example", has_namespace)

        return f"""{prologue}
        let $entries := collection('{db_name}')//{entry_path}
        let $senses := collection('{db_name}')//{sense_path}
        let $examples := collection('{db_name}')//{example_path}
        return
        <statistics>
          <entries>{{count($entries)}}</entries>
          <senses>{{count($senses)}}</senses>
          <examples>{{count($examples)}}</examples>
        </statistics>
        """

    @staticmethod
    def build_advanced_search_query(
        criteria: Dict[str, Any],
        db_name: str,
        has_namespace: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """
        Build advanced search query with multiple criteria.

        Args:
            criteria: Dictionary of search criteria
            db_name: Name of the database
            has_namespace: Whether XML uses namespaces
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Complete XQuery string
        """
        prologue = XQueryBuilder.get_namespace_prologue(has_namespace)
        entry_path = XQueryBuilder.get_element_path("entry", has_namespace)

        conditions = []

        # Build conditions based on criteria
        if "lexical_unit" in criteria:
            lexical_unit_path = XQueryBuilder.get_element_path(
                "lexical-unit", has_namespace
            )
            conditions.append(
                f'contains($entry//{lexical_unit_path}, "{criteria["lexical_unit"]}")'
            )

        if "sense_gloss" in criteria:
            gloss_path = XQueryBuilder.get_element_path("gloss", has_namespace)
            conditions.append(
                f'contains($entry//{gloss_path}, "{criteria["sense_gloss"]}")'
            )

        if "grammatical_info" in criteria:
            grammatical_info_path = XQueryBuilder.get_element_path(
                "grammatical-info", has_namespace
            )
            conditions.append(
                f'$entry//{grammatical_info_path}[@value="{criteria["grammatical_info"]}"]'
            )

        if "example_text" in criteria:
            example_path = XQueryBuilder.get_element_path("example", has_namespace)
            conditions.append(
                f'contains($entry//{example_path}, "{criteria["example_text"]}")'
            )

        where_clause = " and ".join(conditions) if conditions else "true()"

        query = f"""{prologue}
        for $entry in collection('{db_name}')//{entry_path}
        where {where_clause}
        """

        if offset:
            query += f"\n        and position() > {offset}"

        query += "\n        return $entry"

        if limit:
            query = f"({query})[position() <= {limit}]"

        return query

    @staticmethod
    def build_get_lift_ranges_query(db_name: str, has_namespace: bool = True) -> str:
        """
        Build query to retrieve all LIFT ranges.

        Args:
            db_name: Name of the database
            has_namespace: Whether XML uses namespaces

        Returns:
            Complete XQuery string
        """
        prologue = XQueryBuilder.get_namespace_prologue(has_namespace)
        lift_ranges_path = XQueryBuilder.get_element_path("lift-ranges", has_namespace)

        # Find the lift-ranges element, wherever it may be.
        # It could be in the main document or a separate ranges document.
        return f"""{prologue}
        collection('{db_name}')//{lift_ranges_path}
        """

    @staticmethod
    def build_range_query(
        range_name: str, db_name: str, has_namespace: bool = True
    ) -> str:
        """
        Build query to retrieve range definitions.

        Args:
            range_name: Name of the range to retrieve
            db_name: Name of the database
            has_namespace: Whether XML uses namespaces

        Returns:
            Complete XQuery string
        """
        # Note: Ranges are typically stored in a separate document
        return f"""
        for $range in doc('{db_name}/ranges.xml')//range[@id="{range_name}"]
        return $range
        """

    @staticmethod
    def escape_xquery_string(text: str) -> str:
        """
        Escape special characters in XQuery string literals.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for use in XQuery
        """
        # Replace special characters, handle & first to avoid double-escaping
        return (
            text.replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    @staticmethod
    def build_entries_by_grammatical_info_query(
        grammatical_info: str,
        db_name: str,
        has_namespace: bool = True,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """
        Build query to retrieve entries by grammatical information.

        Args:
            grammatical_info: Grammatical information to filter by
            db_name: Name of the database
            has_namespace: Whether XML uses namespaces
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Complete XQuery string
        """
        prologue = XQueryBuilder.get_namespace_prologue(has_namespace)
        entry_path = XQueryBuilder.get_element_path("entry", has_namespace)
        sense_path = XQueryBuilder.get_element_path("sense", has_namespace)
        gi_path = XQueryBuilder.get_element_path("grammatical-info", has_namespace)

        query = f"""{prologue}
        for $entry in collection('{db_name}')//{entry_path}
        where $entry/{sense_path}/{gi_path}[@value="{grammatical_info}"]
        """

        if offset:
            query += f"\n        and position() > {offset}"

        query += "\n        return $entry"

        if limit:
            query = f"({query})[position() <= {limit}]"

        return query

    @staticmethod
    def build_related_entries_query(
        entry_id: str,
        db_name: str,
        has_namespace: bool = True,
        relation_type: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """
        Build query to retrieve related entries.

        Args:
            entry_id: ID of the entry to get related entries for
            db_name: Name of the database
            has_namespace: Whether XML uses namespaces
            relation_type: Optional type of relation to filter by
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Complete XQuery string
        """
        prologue = XQueryBuilder.get_namespace_prologue(has_namespace)
        entry_path = XQueryBuilder.get_element_path("entry", has_namespace)
        relation_path = XQueryBuilder.get_element_path("relation", has_namespace)
        
        relation_condition = f'[@type="{relation_type}"]' if relation_type else ''

        query = f"""{prologue}
        let $entry_relations := collection('{db_name}')//{entry_path}[@id="{entry_id}"]/{relation_path}{relation_condition}/@ref
        for $related in collection('{db_name}')//{entry_path}[@id = $entry_relations]
        """

        if offset:
            query += f"\n        where position() > {offset}"

        query += "\n        return $related"

        if limit:
            query = f"({query})[position() <= {limit}]"

        return query
