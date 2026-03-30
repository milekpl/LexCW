"""
XML normalization utilities for roundtrip testing.

Provides functions to normalize XML content for comparison during
roundtrip tests, with special handling for LIFT format.
"""

import re
from datetime import datetime
from typing import Optional, Tuple

from lxml import etree


# LIFT namespace constant
LIFT_NS = "http://fieldworks.sil.org/schemas/lift/0.13"


def normalize_whitespace(xml_string: str) -> str:
    """
    Normalize whitespace in XML content.

    Collapses multiple consecutive whitespace characters to a single space,
    trims leading and trailing whitespace from text content.

    Args:
        xml_string: The XML string to normalize.

    Returns:
        The XML string with normalized whitespace.
    """
    if not xml_string:
        return xml_string

    # Parse the XML with blank text removal
    parser = etree.XMLParser(remove_blank_text=True)
    try:
        tree = etree.fromstring(xml_string.encode(), parser)
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Invalid XML: {e}") from e

    # Normalize whitespace in text nodes recursively
    def normalize_text(elem: etree._Element) -> None:
        for child in elem:
            if isinstance(child.tag, str):  # Skip comments and processing instructions
                normalize_text(child)

        # Normalize this element's text content
        if elem.text:
            elem.text = ' '.join(elem.text.split())
        if elem.tail:
            elem.tail = ' '.join(elem.tail.split())

    normalize_text(tree)

    # Serialize back to string
    return etree.tostring(tree, encoding='unicode', xml_declaration=False)


def canonicalize_xml(xml_string: str, with_comments: bool = False) -> str:
    """
    Canonicalize XML using exclusive C14N.

    Exclusive canonicalization produces a physically-equivalent canonical
    form of XML that is suited for digital signature and comparison purposes.

    Args:
        xml_string: The XML string to canonicalize.
        with_comments: Whether to include comments in canonicalization.

    Returns:
        The canonicalized XML string.
    """
    if not xml_string:
        return xml_string

    parser = etree.XMLParser(remove_blank_text=True)
    try:
        tree = etree.fromstring(xml_string.encode(), parser)
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Invalid XML: {e}") from e

    # Perform exclusive C14N canonicalization
    # The empty prefix list means no namespaces are prefixed in the output
    canonical = etree.tostring(
        tree,
        method='c14n',
        exclusive=True,
        with_comments=with_comments
    )

    return canonical.decode('utf-8')


def normalize_lift_xml(xml_string: str) -> str:
    """
    Normalize LIFT-specific content for roundtrip testing.

    This function:
    - Handles the LIFT namespace
    - Normalizes date/time values to a canonical form
    - Removes or normalizes timestamp attributes

    Args:
        xml_string: The LIFT XML string to normalize.

    Returns:
        The normalized LIFT XML string.
    """
    if not xml_string:
        return xml_string

    parser = etree.XMLParser(remove_blank_text=True)
    try:
        tree = etree.fromstring(xml_string.encode(), parser)
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Invalid XML: {e}") from e

    def normalize_date(element: etree._Element) -> None:
        """Normalize date-related attributes to canonical form."""
        # Check for date/time attributes
        date_attrs = ['date', 'created', 'modified', 'last-modified']
        for attr_name in date_attrs:
            if attr_name in element.attrib:
                date_val = element.attrib[attr_name]
                try:
                    # Parse and reformat to canonical ISO format
                    parsed = _parse_date(date_val)
                    element.attrib[attr_name] = parsed
                except (ValueError, TypeError):
                    # Keep original if parsing fails
                    pass

        for child in element:
            if isinstance(child.tag, str):
                normalize_date(child)

    def normalize_guid(element: etree._Element) -> None:
        """Normalize GUID attributes to lowercase."""
        guid_attrs = ['guid', 'id', 'owner']
        for attr_name in guid_attrs:
            if attr_name in element.attrib:
                element.attrib[attr_name] = element.attrib[attr_name].lower()

        for child in element:
            if isinstance(child.tag, str):
                normalize_guid(child)

    # Apply normalizations
    normalize_date(tree)
    normalize_guid(tree)

    return etree.tostring(tree, encoding='unicode', xml_declaration=False)


def _parse_date(date_str: str) -> str:
    """
    Parse a date string and return canonical ISO format.

    Handles various date formats commonly found in LIFT files.

    Args:
        date_str: The date string to parse.

    Returns:
        The date in canonical ISO format (YYYY-MM-DD).
    """
    if not date_str:
        return date_str

    # Common date formats to try
    formats = [
        '%Y-%m-%dT%H:%M:%S.%fZ',  # ISO with microseconds
        '%Y-%m-%dT%H:%M:%SZ',      # ISO without microseconds
        '%Y-%m-%dT%H:%M:%S%z',     # ISO with timezone
        '%Y-%m-%d',                # Date only
        '%Y-%m-%d %H:%M:%S',       # Date with time
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(date_str, fmt)
            # Return in canonical format
            return parsed.strftime('%Y-%m-%d')
        except ValueError:
            continue

    # If no format matched, return original
    return date_str


def xmls_equal(xml1: str, xml2: str,
               normalize_whitespace_first: bool = True,
               use_canonicalization: bool = True) -> Tuple[bool, Optional[str]]:
    """
    Compare two XML strings for equality.

    Performs normalization before comparison and returns detailed
    information about any differences found.

    Args:
        xml1: First XML string.
        xml2: Second XML string.
        normalize_whitespace_first: Whether to normalize whitespace before comparison.
        use_canonicalization: Whether to use C14N canonicalization for comparison.

    Returns:
        Tuple of (is_equal, diff_details) where diff_details is None if equal
        or a string describing the differences.
    """
    if xml1 == xml2:
        return True, None

    if not xml1 or not xml2:
        diff = "One or both XML strings are empty"
        return False, diff

    # Parse both XML strings
    try:
        tree1 = etree.fromstring(xml1.encode())
        tree2 = etree.fromstring(xml2.encode())
    except etree.XMLSyntaxError as e:
        return False, f"Invalid XML: {e}"

    # Normalize if requested
    if normalize_whitespace_first:
        try:
            xml1 = normalize_whitespace(xml1)
            tree1 = etree.fromstring(xml1.encode())
        except (ValueError, etree.XMLSyntaxError) as e:
            return False, f"Cannot normalize xml1: {e}"

        try:
            xml2 = normalize_whitespace(xml2)
            tree2 = etree.fromstring(xml2.encode())
        except (ValueError, etree.XMLSyntaxError) as e:
            return False, f"Cannot normalize xml2: {e}"

    # Use canonicalization for comparison
    if use_canonicalization:
        try:
            canon1 = canonicalize_xml(xml1)
            canon2 = canonicalize_xml(xml2)
        except (ValueError, etree.XMLSyntaxError) as e:
            return False, f"Cannot canonicalize XML: {e}"

        if canon1 == canon2:
            return True, None

        # Detailed diff
        diff = _generate_diff_details(canon1, canon2)
        return False, diff

    # Fallback to element-by-element comparison
    if _elements_equal(tree1, tree2):
        return True, None

    diff = _generate_diff_details(
        etree.tostring(tree1, encoding='unicode'),
        etree.tostring(tree2, encoding='unicode')
    )
    return False, diff


def _elements_equal(el1: etree._Element, el2: etree._Element) -> bool:
    """
    Recursively compare two XML elements for equality.

    Args:
        el1: First element.
        el2: Second element.

    Returns:
        True if elements are equivalent.
    """
    if el1.tag != el2.tag:
        return False

    if el1.text != el2.text:
        return False

    if el1.tail != el2.tail:
        return False

    if set(el1.attrib.keys()) != set(el2.attrib.keys()):
        return False

    for key in el1.attrib:
        if el1.attrib[key] != el2.attrib[key]:
            return False

    if len(el1) != len(el2):
        return False

    for child1, child2 in zip(el1, el2):
        if not _elements_equal(child1, child2):
            return False

    return True


def _generate_diff_details(canon1: str, canon2: str) -> str:
    """
    Generate human-readable difference details.

    Args:
        canon1: First canonicalized XML string.
        canon2: Second canonicalized XML string.

    Returns:
        String describing the differences.
    """
    lines1 = canon1.split('\n')
    lines2 = canon2.split('\n')

    diff_lines = []
    max_lines = max(len(lines1), len(lines2))

    for i in range(max_lines):
        line1 = lines1[i] if i < len(lines1) else '<missing>'
        line2 = lines2[i] if i < len(lines2) else '<missing>'

        if line1 != line2:
            diff_lines.append(f"Line {i + 1}:")
            diff_lines.append(f"  - {line1[:100]}{'...' if len(line1) > 100 else ''}")
            diff_lines.append(f"  + {line2[:100]}{'...' if len(line2) > 100 else ''}")

    if not diff_lines:
        return "XML structures differ but content appears equivalent"

    return '\n'.join(diff_lines) if diff_lines else "XML strings differ"
