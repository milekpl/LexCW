from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import re

@dataclass
class ElementConfig:
    """Configuration for how a LIFT element should be rendered."""
    lift_element: str
    display_order: int
    css_class: str
    prefix: str = ""
    suffix: str = ""
    visibility: str = "always"  # "always", "if-content", "never"
    children: List[ElementConfig] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []

class HTMLBuilder:
    """Builds HTML from LIFT XML elements according to display profile."""

    def __init__(self, profile_elements: List[ElementConfig]):
        self.profile_elements = sorted(profile_elements, key=lambda x: x.display_order)
        self.element_config_map = {config.lift_element: config for config in self.profile_elements}
        self.html_parts = []
        self.current_indent = 0

    def process_element(self, element: ET.Element, config: ElementConfig) -> str:
        """Process a single LIFT element according to its configuration."""
        if config.visibility == "never":
            return ""

        # Extract text content from the element
        text_content = self._extract_text_content(element)

        # Apply conditional visibility
        if config.visibility == "if-content" and not text_content.strip():
            return ""

        # Build HTML for this element
        html = f'<div class="{config.css_class}">'

        if config.prefix:
            html += f'<span class="prefix">{config.prefix}</span>'

        html += text_content

        if config.suffix:
            html += f'<span class="suffix">{config.suffix}</span>'

        html += '</div>'

        return html

    def _extract_text_content(self, element: ET.Element) -> str:
        """Extract text content from a LIFT element, handling nested structures."""
        if element.text and element.text.strip():
            return element.text.strip()

        # Handle nested elements
        content_parts = []
        for child in element:
            child_text = self._extract_text_content(child)
            if child_text:
                content_parts.append(child_text)

        return ' '.join(content_parts) if content_parts else ""

    def build_html(self, root: ET.Element) -> str:
        """Build HTML from the LIFT XML root element."""
        html_parts = []

        # Process elements in the order specified by the profile
        for config in self.profile_elements:
            # Find all matching elements in the XML
            elements = root.findall(f".//{config.lift_element}")
            for element in elements:
                element_html = self.process_element(element, config)
                if element_html:
                    html_parts.append(element_html)

        return '\n'.join(html_parts) if html_parts else "<div class='entry-empty'>No content to display</div>"

class LIFTToHTMLTransformer:
    """Transforms LIFT XML to HTML using display profile configurations."""

    def __init__(self):
        self.namespace_map = {
            'lift': 'urn:sil:lift:0.13',
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
        }

    def transform(self, lift_xml: str, element_configs: List[ElementConfig]) -> str:
        """Transform LIFT XML to HTML using the provided element configurations."""
        try:
            # Parse the XML
            root = self._parse_lift_xml(lift_xml)

            # Create HTML builder with the profile configurations
            html_builder = HTMLBuilder(element_configs)

            # Build and return the HTML
            return html_builder.build_html(root)

        except Exception as e:
            return f"<div class='entry-error'>Error rendering entry: {str(e)}</div>"

    def _parse_lift_xml(self, lift_xml: str) -> ET.Element:
        """Parse LIFT XML, handling namespaces."""
        # Remove namespace declarations to simplify parsing
        clean_xml = self._remove_namespaces(lift_xml)

        try:
            return ET.fromstring(clean_xml)
        except ET.ParseError as e:
            # Try parsing with namespaces if cleanup fails
            try:
                return ET.fromstring(lift_xml)
            except ET.ParseError:
                raise ValueError(f"Failed to parse LIFT XML: {str(e)}")

    def _remove_namespaces(self, xml_string: str) -> str:
        """Remove namespace declarations from XML to simplify parsing."""
        # Remove namespace declarations
        clean_xml = re.sub(r'\sxmlns(:[^=]+)?="[^"]+"', '', xml_string)
        # Remove namespace prefixes
        clean_xml = re.sub(r'<([a-z]+):', r'<\1', clean_xml)
        clean_xml = re.sub(r'</([a-z]+):', r'</\1', clean_xml)
        return clean_xml

    def extract_element_metadata(self, lift_xml: str) -> Dict[str, Any]:
        """Extract metadata about LIFT elements for documentation purposes."""
        try:
            root = self._parse_lift_xml(lift_xml)
            elements = {}

            # Find all unique element types
            for elem in root.iter():
                tag = elem.tag
                if tag not in elements:
                    elements[tag] = {
                        'tag': tag,
                        'attributes': list(elem.attrib.keys()),
                        'children': [],
                        'description': f"LIFT {tag} element"
                    }

                # Track child relationships
                for child in elem:
                    child_tag = child.tag
                    if child_tag not in elements[tag]['children']:
                        elements[tag]['children'].append(child_tag)

            return elements

        except Exception as e:
            return {'error': str(e)}