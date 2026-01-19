"""
HTML Exporter for the Lexicographic Curation Workbench.

This module provides functionality for exporting dictionary entries to HTML format
with alphabetical navigation (A.html, B.html, etc.) and a single CSS style.
"""

import os
import logging
import tempfile
import zipfile
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

from app.services.dictionary_service import DictionaryService
from app.services.css_mapping_service import CSSMappingService
from app.models.display_profile import DisplayProfile
from app.exporters.base_exporter import BaseExporter


# Letters that should have their own pages
ALPHABET = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'W']


class HTMLExporter(BaseExporter):
    """Exporter for HTML format with alphabetical navigation.

    Creates letter-indexed HTML files (A.html, B.html, etc.) with:
    - index.html with overview and letter navigation
    - Individual letter pages with entries starting with that letter
    - Single CSS file for consistent styling
    """

    def __init__(self, dictionary_service: DictionaryService, css_mapping_service: CSSMappingService):
        """Initialize the HTML exporter.

        Args:
            dictionary_service: The dictionary service to use.
            css_mapping_service: The CSS mapping service for rendering entries.
        """
        super().__init__(dictionary_service)
        self.css_service = css_mapping_service
        self.logger = logging.getLogger(__name__)

    def export(self, output_path: str, entries: Optional[List] = None,
               title: str = "Dictionary", profile_id: Optional[int] = None,
               column_layout: str = "single", show_subentries: bool = True) -> str:
        """Export entries to HTML format.

        Args:
            output_path: Path to save the exported ZIP file.
            entries: List of entries to export. If None, all entries will be exported.
            title: Title of the dictionary.
            profile_id: Display profile ID to use for rendering. If None, uses default profile.
            column_layout: Layout style - "single" or "two" columns.
            show_subentries: Whether to show subentries under main entry.

        Returns:
            Path to the exported ZIP file.
        """
        try:
            # If no entries provided, get all entries
            if entries is None:
                entries, _ = self.dictionary_service.list_entries(limit=100000)

            if not entries:
                raise ValueError("No entries to export")

            # Get display profile
            profile = self._get_profile(profile_id)

            # Create temporary directory for building HTML files
            with tempfile.TemporaryDirectory() as temp_dir:
                export_dir = os.path.join(temp_dir, "dictionary_export")
                os.makedirs(export_dir)
                os.makedirs(os.path.join(export_dir, "css"))

                # Generate CSS file with options
                css_path = os.path.join(export_dir, "css", "dictionary.css")
                self._generate_css(css_path, column_layout=column_layout,
                                   show_subentries=show_subentries)

                # Group entries by first letter
                entries_by_letter = self._group_entries_by_letter(entries)

                # Generate letter pages
                letter_pages = self._generate_letter_pages(
                    export_dir, entries_by_letter, profile,
                    column_layout=column_layout
                )

                # Generate index page
                self._generate_index_page(
                    os.path.join(export_dir, "index.html"),
                    entries_by_letter, letter_pages, column_layout=column_layout
                )

                # Create ZIP file
                self._create_zip(output_path, export_dir)

            self.logger.info(f"HTML export created: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Error exporting to HTML: {e}", exc_info=True)
            raise

    def _get_profile(self, profile_id: Optional[int]) -> Optional[DisplayProfile]:
        """Get the display profile to use for rendering."""
        from flask import current_app
        from app.models.workset_models import db

        if profile_id:
            return db.session.get(DisplayProfile, profile_id)

        default_profile = DisplayProfile.query.filter_by(is_default=True).first()
        if default_profile:
            return default_profile

        return DisplayProfile.query.first()

    def _group_entries_by_letter(self, entries: List) -> Dict[str, List]:
        """Group entries by their first letter."""
        groups = defaultdict(list)
        for entry in entries:
            headword = self._get_headword(entry)
            if headword:
                first_letter = headword[0].upper()
                if first_letter in ALPHABET:
                    groups[first_letter].append(entry)
                else:
                    groups[first_letter].append(entry)
        return dict(groups)

    def _get_headword(self, entry) -> str:
        """Extract headword from entry."""
        if hasattr(entry, 'lexical_unit') and entry.lexical_unit:
            for lang in ['en', 'pl', '*']:
                if lang in entry.lexical_unit:
                    return entry.lexical_unit[lang]
            return list(entry.lexical_unit.values())[0] if entry.lexical_unit else ""
        return ""

    def _generate_css(self, css_path: str, column_layout: str = "single",
                      show_subentries: bool = True) -> None:
        """Generate the CSS file with layout options."""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        # Column layout CSS
        if column_layout == "two":
            column_css = """
/* Two Column Layout */
.two-columns .entries-list {
    column-count: 2;
    column-gap: 2rem;
}

@media (max-width: 768px) {
    .two-columns .entries-list {
        column-count: 1;
    }
}
"""
        else:
            column_css = """
/* Single Column Layout */
.single-column .entries-list {
    display: flex;
    flex-direction: column;
    gap: 2rem;
}
"""

        # Subentry CSS
        if show_subentries:
            subentry_css = """
/* Subentry Styles */
.subentry {
    margin-left: 2rem;
    padding-left: 1rem;
    border-left: 2px solid #3498db;
    margin-top: 1rem;
}
"""
        else:
            subentry_css = """
/* Subentry Styles - Hidden */
.subentry {
    display: none;
}
"""

        css_content = f"""/* Dictionary Export Styles */
/* Generated: {timestamp} */
/* Layout: {column_layout} | Subentries: {'shown' if show_subentries else 'hidden'} */

/* Base Reset */
* {{
    box-sizing: border-box;
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 0;
    background-color: #f5f5f5;
    color: #333;
}}

/* Navigation */
.alphabet-nav {{
    background-color: #2c3e50;
    padding: 1rem;
    position: sticky;
    top: 0;
    z-index: 100;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}}

.alphabet-nav h1 {{
    margin: 0 0 0.5rem 0;
    color: white;
    font-size: 1.5rem;
    text-align: center;
}}

.alphabet-links {{
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0.25rem;
}}

.letter-link {{
    color: rgba(255,255,255,0.8);
    text-decoration: none;
    padding: 0.35rem 0.6rem;
    border-radius: 4px;
    font-size: 0.9rem;
    transition: all 0.2s ease;
}}

.letter-link:hover {{
    background-color: rgba(255,255,255,0.15);
    color: white;
}}

.letter-link.active {{
    background-color: #3498db;
    color: white;
}}

/* Container */
.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem 1rem;
}}
{column_css}

/* Entry Styles */
.entry {{
    background: white;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    break-inside: avoid;
    margin-bottom: 1rem;
}}

.entry:last-child {{
    margin-bottom: 0;
}}

/* Letter Heading */
.letter-heading {{
    font-size: 3rem;
    color: #2c3e50;
    margin: 0 0 0.5rem;
    border-bottom: 3px solid #3498db;
    padding-bottom: 0.5rem;
}}

.entry-count {{
    color: #666;
    margin-bottom: 2rem;
    font-size: 0.95rem;
}}

/* Index Page */
.letter-index {{
    background: white;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}}

.letter-index h2 {{
    margin-top: 0;
    color: #2c3e50;
}}

.letter-list {{
    list-style: none;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.5rem;
    margin: 1rem 0;
}}

.letter-list li a {{
    display: block;
    padding: 0.75rem 1rem;
    background: #f8f9fa;
    border-radius: 4px;
    text-decoration: none;
    color: #2c3e50;
    transition: all 0.2s ease;
}}

.letter-list li a:hover {{
    background: #3498db;
    color: white;
}}

/* Export Info */
.export-info {{
    margin-top: 3rem;
    padding-top: 1rem;
    border-top: 1px solid #ddd;
    color: #666;
    font-size: 0.85rem;
}}

/* Entry Content Styles */
.lift-entry-rendered {{
    font-size: 1rem;
}}

.lift-entry-rendered .lexical-unit {{
    font-style: italic;
}}

.lift-entry-rendered .grammatical-info {{
    color: #666;
    font-size: 0.9rem;
    margin-left: 0.5rem;
}}

.lift-entry-rendered .sense {{
    margin-top: 1rem;
}}

.lift-entry-rendered .definition {{
    margin-left: 1.5rem;
}}

.lift-entry-rendered .example {{
    margin-left: 2rem;
    font-style: italic;
    color: #555;
}}

.lift-entry-rendered .relation {{
    display: inline-block;
    margin: 0.25rem 0.5rem 0.25rem 0;
    padding: 0.2rem 0.5rem;
    background: #e8f4f8;
    border-radius: 4px;
    font-size: 0.9rem;
}}

.lift-entry-rendered .variant {{
    color: #666;
    font-size: 0.9rem;
}}

/* Sense numbering */
.lift-entry-rendered:has(.sense:nth-of-type(2)) .sense::before {{
    counter-increment: sense-counter;
    content: counter(sense-counter) ". ";
    font-weight: bold;
    margin-right: 0.5em;
}}

.lift-entry-rendered:has(.sense:nth-of-type(2)) {{
    counter-reset: sense-counter;
}}
{subentry_css}

/* Error State */
.entry-error {{
    color: #dc3545;
    padding: 1rem;
    background: #f8d7da;
    border-radius: 4px;
}}
"""

        with open(css_path, "w", encoding="utf-8") as f:
            f.write(css_content)

    def _generate_letter_pages(self, export_dir: str, entries_by_letter: Dict[str, List],
                                profile: Optional[DisplayProfile],
                                column_layout: str = "single") -> Dict[str, int]:
        """Generate HTML pages for each letter."""
        letter_counts = {}
        all_letters = sorted(set(entries_by_letter.keys()) | set(ALPHABET))

        for letter in all_letters:
            letter_entries = entries_by_letter.get(letter, [])
            letter_counts[letter] = len(letter_entries)

            self._create_letter_page(
                os.path.join(export_dir, f"{letter}.html"),
                letter, len(letter_entries), letter_entries, all_letters, profile,
                column_layout=column_layout
            )

        return letter_counts

    def _create_letter_page(self, html_path: str, letter: str, entry_count: int,
                            entries: List, all_letters: List[str],
                            profile: Optional[DisplayProfile],
                            column_layout: str = "single") -> None:
        """Create a single letter HTML page."""
        nav_html = self._generate_navigation(all_letters, letter)
        entries_html = self._render_entries(entries, profile)
        container_class = f"{column_layout}-columns"

        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dictionary - {letter}</title>
    <link rel="stylesheet" href="css/dictionary.css">
</head>
<body>
    <nav class="alphabet-nav">
        <h1>Dictionary</h1>
        <div class="alphabet-links">
{nav_html}
        </div>
    </nav>

    <main class="container {container_class}">
        <h1 class="letter-heading">{letter}</h1>
        <p class="entry-count">{entry_count} entries</p>
        <div class="entries-list">
{entries_html}
        </div>
    </main>
</body>
</html>'''

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _generate_navigation(self, all_letters: List[str], current_letter: str) -> str:
        """Generate the alphabet navigation HTML."""
        lines = []
        index_class = "active" if current_letter == "Index" else ""
        lines.append(f'            <a href="index.html" class="letter-link {index_class}">Index</a>')

        for letter in sorted(all_letters):
            active_class = "active" if letter == current_letter else ""
            lines.append(f'            <a href="{letter}.html" class="letter-link {active_class}">{letter}</a>')

        return "\n".join(lines)

    def _render_entries(self, entries: List, profile: Optional[DisplayProfile]) -> str:
        """Render entries to HTML."""
        html_parts = []

        for entry in entries:
            try:
                entry_xml = self._get_entry_xml(entry)
                if not entry_xml:
                    continue

                if profile:
                    rendered = self.css_service.render_entry(entry_xml, profile, self.dictionary_service)
                else:
                    rendered = self._basic_render_entry(entry)

                html_parts.append(f'            <div class="entry"><div class="lift-entry-rendered">{rendered}</div></div>')

            except Exception as e:
                self.logger.warning(f"Failed to render entry: {e}")
                html_parts.append(f'            <div class="entry entry-error">Error rendering entry: {e}</div>')

        return "\n".join(html_parts)

    def _get_entry_xml(self, entry) -> str:
        """Get XML representation of an entry."""
        if hasattr(entry, 'xml') and entry.xml:
            return entry.xml

        if hasattr(entry, 'to_lift_xml'):
            return entry.to_lift_xml()

        entry_id = getattr(entry, 'id', None) or getattr(entry, 'guid', None)
        if entry_id:
            try:
                from app.services.xml_entry_service import XMLEntryService
                xml_service = XMLEntryService()
                entry_data = xml_service.get_entry(entry_id)
                return entry_data.get('xml', '')
            except Exception as e:
                self.logger.debug(f"Could not get XML for entry {entry_id}: {e}")

        return ''

    def _basic_render_entry(self, entry) -> str:
        """Basic rendering of an entry without CSS mapping."""
        parts = []

        headword = self._get_headword(entry)
        if headword:
            parts.append(f'<span class="lexical-unit">{headword}</span>')

        if hasattr(entry, 'pronunciations') and entry.pronunciations:
            for lang, pron in entry.pronunciations.items():
                parts.append(f' <span class="pronunciation">/{pron}/</span>')

        if hasattr(entry, 'senses') and entry.senses:
            first_sense = entry.senses[0] if entry.senses else None
            if first_sense and hasattr(first_sense, 'grammatical_info'):
                gi = first_sense.grammatical_info
                if gi and hasattr(gi, 'value'):
                    parts.append(f' <span class="entry-pos">{gi.value}</span>')

        if hasattr(entry, 'senses') and entry.senses:
            for sense in entry.senses:
                sense_parts = []

                if hasattr(sense, 'definitions') and sense.definitions:
                    for lang, defn in sense.definitions.items():
                        sense_parts.append(f'<span class="definition">{defn}</span>')
                elif hasattr(sense, 'definition') and sense.definition:
                    sense_parts.append(f'<span class="definition">{sense.definition}</span>')

                if sense_parts:
                    parts.append(f'<div class="sense">{" ".join(sense_parts)}</div>')

        return " ".join(parts)

    def _generate_index_page(self, html_path: str, entries_by_letter: Dict[str, List],
                             letter_pages: Dict[str, int],
                             column_layout: str = "single") -> None:
        """Generate the index page."""
        all_letters = sorted(set(entries_by_letter.keys()) | set(ALPHABET))
        nav_html = self._generate_navigation(all_letters, "Index")

        letter_list_items = []
        for letter in all_letters:
            count = letter_pages.get(letter, 0)
            letter_list_items.append(f'                <li><a href="{letter}.html">{letter}</a> ({count})</li>')
        letter_list_html = "\n".join(letter_list_items)

        total_entries = sum(len(entries) for entries in entries_by_letter.values())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        container_class = f"{column_layout}-columns"

        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dictionary Export</title>
    <link rel="stylesheet" href="css/dictionary.css">
</head>
<body>
    <nav class="alphabet-nav">
        <h1>Dictionary</h1>
        <div class="alphabet-links">
{nav_html}
        </div>
    </nav>

    <main class="container {container_class}">
        <div class="letter-index">
            <h2>Browse by Letter</h2>
            <ul class="letter-list">
{letter_list_html}
            </ul>
        </div>

        <div class="export-info">
            <p>Generated: {timestamp}</p>
            <p>Total entries: {total_entries}</p>
        </div>
    </main>
</body>
</html>'''

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _create_zip(self, output_path: str, export_dir: str) -> None:
        """Create a ZIP file from the export directory."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(export_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, export_dir)
                    zipf.write(file_path, arcname)
