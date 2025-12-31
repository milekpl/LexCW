"""
LIFT XML namespace management utilities.

This module provides utilities for detecting, normalizing, and managing
namespaces in LIFT XML files to ensure consistent handling across the application.
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class LIFTNamespaceManager:
    """
    Manages LIFT namespace detection and normalization.

    The LIFT format can exist with or without namespace declarations.
    This class provides utilities to detect, normalize, and work with
    both variants consistently.
    """

    # Standard LIFT namespace URI
    LIFT_NAMESPACE = "http://fieldworks.sil.org/schemas/lift/0.13"
    FLEX_NAMESPACE = "http://fieldworks.sil.org/schemas/flex/0.1"

    # Namespace map for ElementTree operations
    NAMESPACE_MAP = {"lift": LIFT_NAMESPACE, "flex": FLEX_NAMESPACE}

    @classmethod
    def detect_namespaces(cls, xml_content: str) -> Dict[str, str]:
        """
        Detect namespaces used in LIFT XML content.

        Args:
            xml_content: XML content as string

        Returns:
            Dictionary mapping prefixes to namespace URIs
        """
        namespaces = {}

        # Check for default namespace declaration
        default_ns_match = re.search(r'xmlns\s*=\s*["\']([^"\']*)["\']', xml_content)
        if default_ns_match:
            namespaces[""] = default_ns_match.group(1)

        # Check for prefixed namespace declarations
        prefixed_ns_matches = re.findall(
            r'xmlns:(\w+)\s*=\s*["\']([^"\']*)["\']', xml_content
        )
        for prefix, uri in prefixed_ns_matches:
            namespaces[prefix] = uri

        return namespaces

    @classmethod
    def has_lift_namespace(cls, xml_content: str) -> bool:
        """
        Check if XML content uses LIFT namespace.

        Args:
            xml_content: XML content as string

        Returns:
            True if LIFT namespace is declared, False otherwise
        """
        namespaces = cls.detect_namespaces(xml_content)
        return cls.LIFT_NAMESPACE in namespaces.values()

    @classmethod
    def register_namespaces(cls, has_lift_namespace: bool = True) -> None:
        """
        Register namespaces with ElementTree for XPath operations.

        Args:
            has_lift_namespace: Whether to register LIFT namespace
        """
        if has_lift_namespace:
            for prefix, uri in cls.NAMESPACE_MAP.items():
                ET.register_namespace(prefix, uri)

    @classmethod
    def normalize_lift_xml(
        cls, xml_content: str, target_namespace: Optional[str] = None
    ) -> str:
        """
        Normalize LIFT XML to use consistent namespace.

        Args:
            xml_content: Original XML content
            target_namespace: Target namespace URI (None for no namespace, LIFT_NAMESPACE for standard)

        Returns:
            Normalized XML content
        """
        import logging
        logger = logging.getLogger(__name__)
        try:
            # Parse the XML
            if not xml_content or not xml_content.strip():
                logger.warning("Empty XML content passed to normalize_lift_xml")
                return xml_content

            root = ET.fromstring(xml_content)
            logger.debug(f"Successfully parsed XML for normalization, root tag: {root.tag}")

            if target_namespace == cls.LIFT_NAMESPACE:
                # Add LIFT namespace
                return cls._add_lift_namespace(root)
            elif target_namespace is None:
                # Remove all namespaces
                return cls._remove_namespaces(root)
            else:
                # Use custom namespace
                return cls._set_custom_namespace(root, target_namespace)

        except ET.ParseError as e:
            logger.error(f"Failed to parse XML for namespace normalization: {e}")
            logger.debug(f"XML content that failed: {xml_content[:500]}...")
            return xml_content  # Return original if parsing fails

    @classmethod
    def _add_lift_namespace(cls, root: ET.Element) -> str:
        """Add LIFT namespace to XML element tree."""
        # Register namespaces with ElementTree so it uses correct prefixes
        cls.register_namespaces(has_lift_namespace=True)

        # Convert all elements to use namespace (only if not already namespaced)
        cls._apply_namespace_to_tree(root, cls.LIFT_NAMESPACE)

        # Use tostring with proper namespace handling
        return ET.tostring(root, encoding="unicode")

    @classmethod
    def _remove_namespaces(cls, root: ET.Element) -> str:
        """Remove all namespaces from XML element tree."""
        for elem in root.iter():
            # Remove namespace from tag
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

            # Remove namespace declarations from attributes
            attrs_to_remove = []
            attrs_to_add = {}

            for key, value in elem.attrib.items():
                if key.startswith("xmlns"):
                    attrs_to_remove.append(key)
                elif "}" in key:
                    attrs_to_remove.append(key)
                    attrs_to_add[key.split("}", 1)[1]] = value

            for key in attrs_to_remove:
                del elem.attrib[key]

            elem.attrib.update(attrs_to_add)

        return ET.tostring(root, encoding="unicode")

    @classmethod
    def _set_custom_namespace(cls, root: ET.Element, namespace: str) -> str:
        """Set custom namespace on XML element tree."""
        # Register custom namespace
        ET.register_namespace('', namespace)

        cls._apply_namespace_to_tree(root, namespace)

        return ET.tostring(root, encoding="unicode")

    @classmethod
    def _apply_namespace_to_tree(cls, root: ET.Element, namespace: str) -> None:
        """Apply namespace to all elements in tree."""
        for elem in root.iter():
            if not elem.tag.startswith("{"):
                elem.tag = f"{{{namespace}}}{elem.tag}"

    @classmethod
    def get_xpath_with_namespace(cls, xpath: str, has_namespace: bool = True) -> str:
        """
        Convert XPath to use proper namespace declarations.

        Args:
            xpath: Original XPath expression
            has_namespace: Whether target XML uses namespaces

        Returns:
            XPath with appropriate namespace handling
        """
        if not has_namespace:
            # Remove any namespace prefixes
            return xpath.replace("lift:", "").replace("flex:", "")

        # Ensure lift: prefix is used for LIFT elements
        common_elements = [
            "entry",
            "sense",
            "example",
            "form",
            "text",
            "gloss",
            "definition",
            "lexical-unit",
            "pronunciation",
            "variant",
            "relation",
            "note",
            "grammatical-info",
        ]

        for element in common_elements:
            # Add lift: prefix if not already present
            xpath = re.sub(r"\b(?<!:)" + element + r"\b", f"lift:{element}", xpath)

        return xpath

    @classmethod
    def create_element_with_namespace(
        cls,
        tag: str,
        attrib: Optional[Dict[str, str]] = None,
        has_namespace: bool = True,
    ) -> ET.Element:
        """
        Create XML element with appropriate namespace.

        Args:
            tag: Element tag name
            attrib: Element attributes
            has_namespace: Whether to use LIFT namespace

        Returns:
            XML Element with proper namespace
        """
        if attrib is None:
            attrib = {}

        if has_namespace and not tag.startswith("{"):
            tag = f"{{{cls.LIFT_NAMESPACE}}}{tag}"

        return ET.Element(tag, attrib)

    @classmethod
    def get_namespace_info(cls, xml_content: str) -> Tuple[bool, Dict[str, str]]:
        """
        Get comprehensive namespace information from XML.

        Args:
            xml_content: XML content as string

        Returns:
            Tuple of (has_lift_namespace, namespace_map)
        """
        namespaces = cls.detect_namespaces(xml_content)
        has_lift_ns = cls.LIFT_NAMESPACE in namespaces.values()

        return has_lift_ns, namespaces


class XPathBuilder:
    """
    Builder for namespace-aware XPath expressions.
    """

    @staticmethod
    def entry(entry_id: Optional[str] = None, has_namespace: bool = True) -> str:
        """Build XPath for entry element."""
        prefix = "lift:" if has_namespace else ""
        if entry_id:
            return f"//{prefix}entry[@id='{entry_id}']"
        return f"//{prefix}entry"

    @staticmethod
    def sense(sense_id: Optional[str] = None, has_namespace: bool = True) -> str:
        """Build XPath for sense element."""
        prefix = "lift:" if has_namespace else ""
        if sense_id:
            return f"//{prefix}sense[@id='{sense_id}']"
        return f"//{prefix}sense"

    @staticmethod
    def lexical_unit(lang: Optional[str] = None, has_namespace: bool = True) -> str:
        """Build XPath for lexical-unit element."""
        prefix = "lift:" if has_namespace else ""
        base = f"//{prefix}lexical-unit"
        if lang:
            return f"{base}/{prefix}form[@lang='{lang}']"
        return base

    @staticmethod
    def form_text(lang: Optional[str] = None, has_namespace: bool = True) -> str:
        """Build XPath for form text content."""
        prefix = "lift:" if has_namespace else ""
        base = f"//{prefix}form"
        if lang:
            base += f"[@lang='{lang}']"
        return f"{base}/{prefix}text"
