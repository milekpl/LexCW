"""XML processing and namespace utilities for dictionary services."""

from __future__ import annotations
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Union, Any

from app.parsers.lift_parser import LIFTParser
from app.utils.namespace_manager import LIFTNamespaceManager
from app.utils.xquery_builder import XQueryBuilder


logger = logging.getLogger(__name__)


class XMLProcessingService:
    """Service for XML processing and namespace handling."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.lift_parser = LIFTParser(validate=False)
        self.namespace_manager = LIFTNamespaceManager()
        self.query_builder = XQueryBuilder()
        self._has_namespace: Optional[bool] = None

    def prepare_entry_xml(self, entry: 'Entry') -> str:
        """Generate XML string for an entry, stripping namespaces.

        Args:
            entry: Entry object to convert to XML.

        Returns:
            XML string without namespace prefixes.

        Raises:
            ValueError: If entry element cannot be found in generated XML.
        """
        entry_xml_full = self.lift_parser.generate_lift_string([entry])
        root = ET.fromstring(entry_xml_full)
        entry_elem_ns = root.find(".//lift:entry", self.lift_parser.NSMAP)
        if entry_elem_ns is None:
            entry_elem_ns = root.find(".//entry")  # fallback

        if entry_elem_ns is None:
            raise ValueError("Failed to find entry element in generated XML")

        # Strip namespaces from tags and attributes
        for elem in entry_elem_ns.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]
            for key in list(elem.attrib.keys()):
                if "}" in key:
                    new_key = key.split("}", 1)[1]
                    elem.attrib[new_key] = elem.attrib.pop(key)
                if key.startswith("xmlns"):
                    del elem.attrib[key]

        return ET.tostring(entry_elem_ns, encoding="unicode")

    def detect_namespace_usage(
        self,
        db_connector: Union['BaseXConnector', object],
        db_name: Optional[str] = None,
        project_id: Optional[int] = None
    ) -> bool:
        """Check if the dictionary database uses namespaces.

        Caches the result to avoid repeated queries.

        Args:
            db_connector: Database connector for executing queries.
            db_name: Optional database name (uses connector.database if not provided).
            project_id: Optional project ID for database resolution.

        Returns:
            True if the database uses namespaces, False otherwise.
        """
        # Return cached value if available
        if self._has_namespace is not None:
            return self._has_namespace

        try:
            if not db_name:
                db_name = getattr(db_connector, 'database', None)

            if not db_name:
                self._has_namespace = False
                return False

            # Use namespace-aware query to check for root <lift> element with namespace
            test_query = f"""declare namespace lift = "{self.namespace_manager.LIFT_NAMESPACE}";
            exists(collection('{db_name}')//lift:lift)"""

            result = db_connector.execute_query(test_query)
            if result:
                result = result.strip()

            self._has_namespace = (result and result.lower() == "true")
            return self._has_namespace
        except Exception as e:
            self.logger.warning("Error detecting namespace usage: %s", e)
            self._has_namespace = False
            return False

    def detect_namespace_usage_in_db(
        self,
        db_connector: Union['BaseXConnector', object],
        db_name: str
    ) -> bool:
        """Check if a specific database uses namespaces.

        Args:
            db_connector: Database connector for executing queries.
            db_name: Name of the database to check.

        Returns:
            True if the database uses namespaces, False otherwise.
        """
        try:
            # Use namespace-aware query to check for root <lift> element with namespace
            test_query = f"""declare namespace lift = "{self.namespace_manager.LIFT_NAMESPACE}";
            exists(collection('{db_name}')//lift:lift)"""

            result = db_connector.execute_query(test_query)
            if result:
                result = result.strip()

            return (result and result.lower() == "true")
        except Exception as e:
            self.logger.warning("Error detecting namespace usage in DB %s: %s", db_name, e)
            return False

    def build_entry_query(
        self,
        entry_id: str,
        db_name: str,
        has_namespace: bool = False
    ) -> str:
        """Build XQuery for retrieving entry by ID.

        Args:
            entry_id: The entry ID to query for.
            db_name: Database name.
            has_namespace: Whether entries use namespaces.

        Returns:
            XQuery string for retrieving the entry.
        """
        return self.query_builder.build_entry_by_id_query(
            entry_id, db_name, has_namespace=has_namespace
        )

    def build_insert_query(
        self,
        entry_xml: str,
        db_name: str,
        has_namespace: bool = False
    ) -> str:
        """Build XQuery for inserting an entry.

        Args:
            entry_xml: XML string of the entry.
            db_name: Database name.
            has_namespace: Whether entries use namespaces.

        Returns:
            XQuery string for inserting the entry.
        """
        return self.query_builder.build_insert_entry_query(
            entry_xml, db_name, has_namespace=has_namespace
        )

    def build_update_query(
        self,
        entry_id: str,
        entry_xml: str,
        db_name: str,
        has_namespace: bool = False
    ) -> str:
        """Build XQuery for updating an entry.

        Args:
            entry_id: The entry ID to update.
            entry_xml: New XML string for the entry.
            db_name: Database name.
            has_namespace: Whether entries use namespaces.

        Returns:
            XQuery string for updating the entry.
        """
        return self.query_builder.build_update_entry_query(
            entry_id, entry_xml, db_name, has_namespace=has_namespace
        )

    def build_delete_query(
        self,
        entry_id: str,
        db_name: str,
        has_namespace: bool = False
    ) -> str:
        """Build XQuery for deleting an entry.

        Args:
            entry_id: The entry ID to delete.
            db_name: Database name.
            has_namespace: Whether entries use namespaces.

        Returns:
            XQuery string for deleting the entry.
        """
        return self.query_builder.build_delete_entry_query(
            entry_id, db_name, has_namespace=has_namespace
        )

    def reset_namespace_cache(self) -> None:
        """Reset the namespace detection cache.

        Call this when the database content changes significantly.
        """
        self._has_namespace = None
