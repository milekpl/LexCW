"""Service for exporting LIFT files with custom ranges support."""

from __future__ import annotations
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from xml.dom import minidom

from app.services.ranges_service import RangesService
from app.database.basex_connector import BaseXConnector


class LIFTExportService:
    """Service for exporting LIFT files including custom ranges."""

    def __init__(self, db_connector: BaseXConnector, ranges_service: RangesService):
        """
        Initialize LIFT export service.

        Args:
            db_connector: BaseX database connector
            ranges_service: Ranges service for loading ranges
        """
        self.db_connector = db_connector
        self.ranges_service = ranges_service
        self.logger = logging.getLogger(__name__)

    def export_ranges_file(self, project_id: int, output_path: str) -> None:
        """
        Export ranges file including custom ranges.

        Args:
            project_id: Project ID for custom ranges
            output_path: Path to write the ranges XML file
        """
        # Load standard ranges
        standard_ranges = self._load_standard_ranges()

        # Load custom ranges
        custom_ranges = self._load_custom_ranges_for_export(project_id)

        # Merge custom ranges into standard ranges
        for range_name, elements in custom_ranges.items():
            if range_name not in standard_ranges:
                standard_ranges[range_name] = []
            standard_ranges[range_name].extend(elements)

        # Write XML
        self._write_ranges_xml(standard_ranges, output_path)

    def _load_standard_ranges(self) -> Dict[str, Any]:
        """
        Load standard ranges from the database.

        Returns:
            Dictionary of standard ranges
        """
        try:
            return self.ranges_service.get_all_ranges()
        except Exception as e:
            self.logger.error(f"Error loading standard ranges: {e}")
            return {}

    def _load_custom_ranges_for_export(self, project_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load custom ranges formatted for export.

        Args:
            project_id: Project ID

        Returns:
            Dictionary mapping range names to lists of range elements
        """
        from app.models.custom_ranges import CustomRange, CustomRangeValue

        custom_ranges = {}

        try:
            ranges = CustomRange.query.filter_by(project_id=project_id).all()
            for cr in ranges:
                elements = []
                for val in cr.values:
                    element = {
                        'id': val.value,
                        'guid': f'custom-{cr.id}-{val.id}',
                        'value': val.value,
                        'abbrev': val.label or val.value,
                        'description': {k: v for k, v in [('en', val.description)] if v},
                        'label': {k: v for k, v in [('en', val.label)] if v},
                        'custom': True
                    }
                    elements.append(element)
                custom_ranges[cr.range_name] = elements
        except Exception as e:
            self.logger.error(f"Error loading custom ranges for export: {e}")

        return custom_ranges

    def _write_ranges_xml(self, ranges: Dict[str, Any], output_path: str) -> None:
        """
        Write ranges dictionary to XML file.

        Args:
            ranges: Dictionary of ranges to write
            output_path: Path to write XML file
        """
        # Create root element
        root = ET.Element('lift-ranges')

        for range_name, range_data in ranges.items():
            range_elem = ET.SubElement(root, 'range')
            range_elem.set('id', range_name)

            # Add guid if available
            if 'guid' in range_data:
                range_elem.set('guid', range_data['guid'])

            # Add labels
            if 'description' in range_data and range_data['description']:
                for lang, text in range_data['description'].items():
                    label_elem = ET.SubElement(range_elem, 'label')
                    form_elem = ET.SubElement(label_elem, 'form')
                    form_elem.set('lang', lang)
                    text_elem = ET.SubElement(form_elem, 'text')
                    text_elem.text = text

            # Add elements
            if 'values' in range_data and range_data['values']:
                for element in range_data['values']:
                    self._add_range_element(range_elem, element)

        # Write to file with pretty formatting
        rough_string = ET.tostring(root, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent='  ')

        # Remove extra newlines
        lines = pretty_xml.split('\n')
        cleaned_lines = [line for line in lines if line.strip()]

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(cleaned_lines))

    def _add_range_element(self, parent: ET.Element, element_data: Dict[str, Any]) -> None:
        """
        Add a range element to the parent.

        Args:
            parent: Parent XML element
            element_data: Element data dictionary
        """
        elem = ET.SubElement(parent, 'range-element')
        elem.set('id', element_data.get('id', ''))
        elem.set('guid', element_data.get('guid', ''))

        if 'value' in element_data and element_data['value']:
            elem.set('value', element_data['value'])

        if 'parent' in element_data and element_data['parent']:
            elem.set('parent', element_data['parent'])

        # Add labels
        if 'label' in element_data and element_data['label']:
            for lang, text in element_data['label'].items():
                label_elem = ET.SubElement(elem, 'label')
                form_elem = ET.SubElement(label_elem, 'form')
                form_elem.set('lang', lang)
                text_elem = ET.SubElement(form_elem, 'text')
                text_elem.text = text

        # Add abbreviations
        if 'abbrev' in element_data and element_data['abbrev']:
            abbrev_elem = ET.SubElement(elem, 'abbrev')
            form_elem = ET.SubElement(abbrev_elem, 'form')
            form_elem.set('lang', 'en')  # Default to English
            text_elem = ET.SubElement(form_elem, 'text')
            text_elem.text = element_data['abbrev']

        # Add descriptions
        if 'description' in element_data and element_data['description']:
            for lang, text in element_data['description'].items():
                desc_elem = ET.SubElement(elem, 'description')
                form_elem = ET.SubElement(desc_elem, 'form')
                form_elem.set('lang', lang)
                text_elem = ET.SubElement(form_elem, 'text')
                text_elem.text = text

        # Add traits if present
        if 'traits' in element_data and element_data['traits']:
            for trait_name, trait_value in element_data['traits'].items():
                trait_elem = ET.SubElement(elem, 'trait')
                trait_elem.set('name', trait_name)
                trait_elem.set('value', trait_value)

        # Recursively add children
        if 'children' in element_data and element_data['children']:
            for child in element_data['children']:
                self._add_range_element(elem, child)