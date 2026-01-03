"""Search and listing service for dictionary operations."""

from __future__ import annotations
import logging
from typing import Dict, List, Optional, Tuple, Union, Any, Callable

from app.database.basex_connector import BaseXConnector
from app.database.mock_connector import MockDatabaseConnector
from app.models.entry import Entry
from app.parsers.lift_parser import LIFTParser
from app.services.entry_service import EntryService
from app.services.xml_processing_service import XMLProcessingService
from app.services.database_utils import get_db_name
from app.utils.exceptions import DatabaseError
from app.utils.xquery_builder import XQueryBuilder


logger = logging.getLogger(__name__)


class SearchService:
    """Service for searching and listing dictionary entries."""

    def __init__(
        self,
        db_connector: Union[BaseXConnector, MockDatabaseConnector],
        entry_service: Optional[EntryService] = None,
        xml_service: Optional[XMLProcessingService] = None,
        logger: Optional[logging.Logger] = None,
        facade: Optional[Any] = None,  # Reference to facade for count delegation
    ):
        """Initialize the search service.

        Args:
            db_connector: Database connector for accessing the BaseX database.
            entry_service: Optional entry service for related operations.
            xml_service: Optional XML processing service.
            logger: Optional logger instance.
            facade: Optional reference to the facade for count method delegation.
        """
        self.db_connector = db_connector
        self.entry_service = entry_service
        self.xml_service = xml_service or XMLProcessingService(logger=logger)
        self.logger = logger or logging.getLogger(__name__)
        self.xquery_builder = XQueryBuilder()
        self.lift_parser = LIFTParser(validate=False)
        self._facade = facade  # For count method delegation

    def search_entries(
        self,
        query: str = "",
        project_id: Optional[int] = None,
        fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        pos: Optional[str] = None,
        exact_match: Optional[bool] = False,
        case_sensitive: Optional[bool] = False,
    ) -> Tuple[List[Entry], int]:
        """Search for entries.

        Args:
            query: Search query.
            fields: Fields to search in (default: lexical_unit, glosses, definitions).
            limit: Maximum number of results to return.
            offset: Number of results to skip for pagination.
            pos: Part of speech to filter by (grammatical_info).
            exact_match: Whether to perform exact match instead of partial match.
            case_sensitive: Whether the search should be case-sensitive.

        Returns:
            Tuple of (list of Entry objects, total count).

        Raises:
            DatabaseError: If there is an error searching entries.
        """
        if not fields:
            fields = ["lexical_unit", "glosses", "definitions", "note"]

        try:
            db_name = get_db_name(self.db_connector, project_id, self.logger)

            if not db_name:
                raise DatabaseError("Database name not configured")

            # Use namespace-aware queries
            # Use facade's method if available (for test compatibility with patched _detect_namespace_usage)
            if self._facade is not None and hasattr(self._facade, '_detect_namespace_usage'):
                has_ns = self._facade._detect_namespace_usage()
            else:
                has_ns = self.xml_service.detect_namespace_usage(self.db_connector, db_name)
            entry_path = self.xquery_builder.get_element_path("entry", has_ns)
            prologue = self.xquery_builder.get_namespace_prologue(has_ns)

            # Build the search query conditions with namespace-aware paths
            conditions: List[str] = []
            q_escaped = query.replace("'", "''")  # Escape single quotes for XQuery

            if "lexical_unit" in fields:
                # Use namespace-aware paths throughout
                lexical_unit_path = self.xquery_builder.get_element_path(
                    "lexical-unit", has_ns
                )
                form_path = self.xquery_builder.get_element_path("form", has_ns)
                text_path = self.xquery_builder.get_element_path("text", has_ns)

                # Determine whether to use exact match or contains based on exact_match flag
                if exact_match:
                    if case_sensitive:
                        # Case-sensitive exact match
                        conditions.append(
                            f"(some $form in $entry/{lexical_unit_path}/{form_path}/{text_path} satisfies $form = '{q_escaped}')"
                        )
                    else:
                        # Case-insensitive exact match (using lower-case)
                        conditions.append(
                            f"(some $form in $entry/{lexical_unit_path}/{form_path}/{text_path} satisfies lower-case($form) = '{q_escaped.lower()}')"
                        )
                else:
                    if case_sensitive:
                        # Case-sensitive partial match
                        conditions.append(
                            f"(some $form in $entry/{lexical_unit_path}/{form_path}/{text_path} satisfies contains($form, '{q_escaped}'))"
                        )
                    else:
                        # Case-insensitive partial match (default behavior)
                        conditions.append(
                            f"(some $form in $entry/{lexical_unit_path}/{form_path}/{text_path} satisfies contains(lower-case($form), '{q_escaped.lower()}'))"
                        )

            if "glosses" in fields:
                sense_path = self.xquery_builder.get_element_path("sense", has_ns)
                gloss_path = self.xquery_builder.get_element_path("gloss", has_ns)
                text_path = self.xquery_builder.get_element_path("text", has_ns)

                if exact_match:
                    if case_sensitive:
                        conditions.append(
                            f"(some $gloss in $entry/{sense_path}/{gloss_path}/{text_path} satisfies $gloss = '{q_escaped}')"
                        )
                    else:
                        conditions.append(
                            f"(some $gloss in $entry/{sense_path}/{gloss_path}/{text_path} satisfies lower-case($gloss) = '{q_escaped.lower()}')"
                        )
                else:
                    if case_sensitive:
                        conditions.append(
                            f"(some $gloss in $entry/{sense_path}/{gloss_path}/{text_path} satisfies contains($gloss, '{q_escaped}'))"
                        )
                    else:
                        conditions.append(
                            f"(some $gloss in $entry/{sense_path}/{gloss_path}/{text_path} satisfies contains(lower-case($gloss), '{q_escaped.lower()}'))"
                        )

            if "definitions" in fields or "definition" in fields:
                sense_path = self.xquery_builder.get_element_path("sense", has_ns)
                definition_path = self.xquery_builder.get_element_path(
                    "definition", has_ns
                )
                form_path = self.xquery_builder.get_element_path("form", has_ns)
                text_path = self.xquery_builder.get_element_path("text", has_ns)

                if exact_match:
                    if case_sensitive:
                        conditions.append(
                            f"(some $def in $entry/{sense_path}/{definition_path}/{form_path}/{text_path} satisfies $def = '{q_escaped}')"
                        )
                    else:
                        conditions.append(
                            f"(some $def in $entry/{sense_path}/{definition_path}/{form_path}/{text_path} satisfies lower-case($def) = '{q_escaped.lower()}')"
                        )
                else:
                    if case_sensitive:
                        conditions.append(
                            f"(some $def in $entry/{sense_path}/{definition_path}/{form_path}/{text_path} satisfies contains($def, '{q_escaped}'))"
                        )
                    else:
                        conditions.append(
                            f"(some $def in $entry/{sense_path}/{definition_path}/{form_path}/{text_path} satisfies contains(lower-case($def), '{q_escaped.lower()}'))"
                        )

            if "note" in fields:
                # Search in both entry-level and sense-level notes
                note_path = self.xquery_builder.get_element_path("note", has_ns)
                form_path = self.xquery_builder.get_element_path("form", has_ns)
                text_path = self.xquery_builder.get_element_path("text", has_ns)
                sense_path = self.xquery_builder.get_element_path("sense", has_ns)

                # Entry-level notes
                if exact_match:
                    if case_sensitive:
                        entry_notes_condition = f"(some $note in $entry/{note_path}/{form_path}/{text_path} satisfies $note = '{q_escaped}')"
                    else:
                        entry_notes_condition = f"(some $note in $entry/{note_path}/{form_path}/{text_path} satisfies lower-case($note) = '{q_escaped.lower()}')"
                else:
                    if case_sensitive:
                        entry_notes_condition = f"(some $note in $entry/{note_path}/{form_path}/{text_path} satisfies contains($note, '{q_escaped}'))"
                    else:
                        entry_notes_condition = f"(some $note in $entry/{note_path}/{form_path}/{text_path} satisfies contains(lower-case($note), '{q_escaped.lower()}'))"

                # Sense-level notes
                if exact_match:
                    if case_sensitive:
                        sense_notes_condition = f"(some $note in $entry/{sense_path}/{note_path}/{form_path}/{text_path} satisfies $note = '{q_escaped}')"
                    else:
                        sense_notes_condition = f"(some $note in $entry/{sense_path}/{note_path}/{form_path}/{text_path} satisfies lower-case($note) = '{q_escaped.lower()}')"
                else:
                    if case_sensitive:
                        sense_notes_condition = f"(some $note in $entry/{sense_path}/{note_path}/{form_path}/{text_path} satisfies contains($note, '{q_escaped}'))"
                    else:
                        sense_notes_condition = f"(some $note in $entry/{sense_path}/{note_path}/{form_path}/{text_path} satisfies contains(lower-case($note), '{q_escaped.lower()}'))"

                conditions.append(
                    f"({entry_notes_condition} or {sense_notes_condition})"
                )

            # Safety check: if no conditions were added, return empty results
            if not conditions:
                self.logger.warning("No valid search fields provided: %s", fields)
                return [], 0

            # Add grammatical info (POS) condition if specified
            if pos:
                grammatical_info_path = self.xquery_builder.get_element_path("grammatical-info", has_ns)
                pos_condition = f"($entry/{grammatical_info_path}[@value = '{pos}'] or $entry//sense/{grammatical_info_path}[@value = '{pos}'])"
                # For POS filtering, we use 'and' to combine with other conditions
                search_condition = f"({' or '.join(conditions)}) and {pos_condition}"
            else:
                search_condition = " or ".join(conditions)

            # Get the total count first
            count_query = f"{prologue} count(for $entry in collection('{db_name}')//{entry_path} where {search_condition} return $entry)"
            count_result = self.db_connector.execute_query(count_query)
            total_count = int(count_result) if count_result else 0

            # Use XQuery position-based pagination (like in list_entries)
            pagination_expr = ""
            if limit is not None:
                start = offset + 1 if offset is not None else 1
                end = start + limit - 1
                pagination_expr = f"[position() = {start} to {end}]"
            elif offset is not None:
                start = offset + 1
                pagination_expr = f"[position() >= {start}]"

            lexical_unit_path_order = self.xquery_builder.get_element_path("lexical-unit", has_ns)
            form_path_order = self.xquery_builder.get_element_path("form", has_ns)
            text_path_order = self.xquery_builder.get_element_path("text", has_ns)

            # Define scoring for ordering: 1 for exact match, 2 for partial.
            # Use string() to ensure we compare atomic values.
            score_expr = f"""let $score := if (some $form in $entry/{lexical_unit_path_order}/{form_path_order}/{text_path_order}
                                        satisfies lower-case($form/string()) = '{q_escaped.lower()}')
                                   then 1
                                   else 2"""

            # Order by score, then by the lexical unit, then by entry id for consistent/deterministic sorting.
            order_by_expr = f"order by $score, $entry/{lexical_unit_path_order}/{form_path_order}[1]/{text_path_order}[1]/string(), $entry/@id"

            query_str = f"""
            {prologue}
            (for $entry in collection('{db_name}')//{entry_path}
            where {search_condition}
            {score_expr}
            {order_by_expr}
            return $entry){pagination_expr}
            """

            # Log the query for debugging
            self.logger.debug(f"Executing search query: {query_str}")

            result = self.db_connector.execute_query(query_str.strip())

            if not result:
                return [], total_count

            # Parse results
            entries = self.lift_parser.parse_string(result)

            # Additional validation to ensure pagination is correctly applied
            if limit is not None and len(entries) > limit:
                self.logger.debug(
                    f"Trimming results from {len(entries)} to {limit} entries"
                )
                entries = entries[:limit]

            return entries, total_count

        except DatabaseError:
            raise
        except Exception as e:
            self.logger.error("Error searching entries: %s", str(e))
            raise DatabaseError(f"Failed to search entries: {str(e)}") from e

    def list_entries(
        self,
        project_id: Optional[int] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        sort_by: str = "lexical_unit",
        sort_order: str = "asc",
        filter_text: str = "",
        total_count: Optional[int] = None,  # Pre-computed count from facade
    ) -> Tuple[List[Entry], int]:
        """List entries with filtering and sorting support.

        Args:
            project_id: Optional project ID to determine database.
            limit: Maximum number of entries to return.
            offset: Number of entries to skip.
            sort_by: Field to sort by (lexical_unit, id, etc.).
            sort_order: Sort order ("asc" or "desc").
            filter_text: Text to filter entries by.

        Returns:
            Tuple of (list of Entry objects, total count).

        Raises:
            DatabaseError: If there is an error listing entries.
        """
        try:
            db_name = get_db_name(self.db_connector, project_id, self.logger)

            self.logger.debug(
                "list_entries called with: limit=%s, offset=%s, sort_by=%s, "
                "sort_order=%s, filter_text=%s, db_name=%s",
                limit, offset, sort_by, sort_order, filter_text, db_name
            )

            # Sanitize filter_text to prevent injection issues
            if filter_text:
                filter_text = filter_text.replace("'", "''")

            # Get total count (use pre-computed count if provided, otherwise compute it)
            if total_count is not None:
                computed_total = total_count
            else:
                computed_total = self._count_entries_with_filter(filter_text, project_id=project_id)

            # Build list query using XQueryBuilder's build_all_entries_query as base
            has_ns = self.xml_service.detect_namespace_usage(self.db_connector, db_name)
            entry_path = self.xquery_builder.get_element_path("entry", has_ns)
            text_element = "text" if not has_ns else "lift:text"

            # Build the full query
            if filter_text:
                # Add filter for lexical_unit containing the filter text
                filter_condition = f"""[contains(translate(./lexical-unit/form/{text_element}, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{filter_text.lower()}')]"""
            else:
                filter_condition = ""

            # Build order by clause
            if sort_by == "lexical_unit":
                order_element = f"lexical-unit/form/{text_element}"
            elif sort_by == "id":
                order_element = "@id"
            else:
                order_element = f"lexical-unit/form/{text_element}"

            order_direction = "descending" if sort_order == "desc" else "ascending"

            # Build the full query
            list_query = f"""
            for $entry in collection('{db_name}')/{entry_path}{filter_condition}
            order by string($entry/{order_element}) {order_direction}
            return $entry
            """

            self.logger.debug("List query: %s", list_query)

            # Apply pagination
            if limit is not None:
                limit_clause = f" limit {limit}"
            else:
                limit_clause = ""

            if offset > 0:
                offset_clause = f" offset {offset}"
            else:
                offset_clause = ""

            paginated_query = list_query + limit_clause + offset_clause

            result_xml = self.db_connector.execute_query(paginated_query)

            # Parse results
            entries = []
            if result_xml:
                entries = self.lift_parser.parse_string(result_xml)

            return (entries, computed_total)

        except DatabaseError:
            raise
        except Exception as e:
            self.logger.error("Error listing entries: %s", str(e))
            raise DatabaseError(f"Failed to list entries: {str(e)}") from e

    def count_entries(
        self,
        project_id: Optional[int] = None,
        filter_text: Optional[str] = None
    ) -> int:
        """Count total or filtered entries."""
        return self._count_entries_with_filter(filter_text or "", project_id)

    def _count_entries_with_filter(
        self,
        filter_text: str,
        project_id: Optional[int] = None
    ) -> int:
        """Count entries that match the filter text.

        Does direct query - does NOT delegate to facade to avoid recursion issues.
        """

        try:
            db_name = get_db_name(self.db_connector, project_id, self.logger)

            if not db_name:
                return 0

            has_ns = self.xml_service.detect_namespace_usage(self.db_connector, db_name)
            entry_path = self.xquery_builder.get_element_path("entry", has_ns)
            text_element = "text" if not has_ns else "lift:text"

            if filter_text:
                # Sanitize filter_text
                escaped_filter = filter_text.replace("'", "''")
                count_query = f"""xquery count(collection('{db_name}')/{entry_path}[contains(translate(./lexical-unit/form/{text_element}, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{escaped_filter.lower()}')])"""
            else:
                count_query = f"xquery count(collection('{db_name}')/{entry_path})"

            result = self.db_connector.execute_query(count_query)

            if result:
                try:
                    return int(result.strip())
                except ValueError:
                    self.logger.warning("Could not parse count result: %s", result)

            return 0

        except DatabaseError:
            return 0
        except Exception as e:
            self.logger.warning("Error counting entries with filter: %s", e)
            return 0
