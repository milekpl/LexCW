"""
Kindle exporter for the Dictionary Writing System.

This module provides functionality for exporting dictionary entries to Kindle format.
"""

import os
import logging
import shutil
import tempfile
import subprocess
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.entry import Entry
from app.services.dictionary_service import DictionaryService
from app.exporters.base_exporter import BaseExporter
from app.utils.exceptions import ExportError


class KindleExporter(BaseExporter):
    """
    Exporter for Kindle dictionary format.
    
    This class handles exporting dictionary entries to Kindle format (.opf, .html),
    and optionally converting to .mobi if kindlegen is available.
    """
    
    def __init__(self, dictionary_service: DictionaryService):
        """
        Initialize a Kindle exporter.
        
        Args:
            dictionary_service: The dictionary service to use.
        """
        super().__init__(dictionary_service)
        self.logger = logging.getLogger(__name__)
    
    def export(self, output_path: str, entries: Optional[List[Entry]] = None, 
               title: str = "Dictionary", source_lang: str = "en", target_lang: str = "pl",
               author: str = "Dictionary Writing System", kindlegen_path: Optional[str] = None,
               inflections: Optional[Dict[str, Any]] = None) -> str:
        """
        Export entries to Kindle dictionary format.
        
        Args:
            output_path: Path to save the exported files.
            entries: List of entries to export. If None, all entries will be exported.
            title: Title of the dictionary.
            source_lang: Source language code.
            target_lang: Target language code.
            author: Author name for the dictionary.
            kindlegen_path: Path to the kindlegen executable (optional).
            inflections: Dictionary of inflection forms (optional).
            
        Returns:
            Path to the exported files.
            
        Raises:
            ExportError: If the export fails.
        """
        try:
            # Create export directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # If no entries provided, get all entries
            if entries is None:
                entries, _ = self.dictionary_service.list_entries(limit=100000)
            
            if not entries:
                raise ExportError("No entries to export")
            
            # Create a temporary directory for building the Kindle files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create the OPF file
                opf_path = os.path.join(temp_dir, "dictionary.opf")
                self._create_opf_file(opf_path, title, source_lang, target_lang, author)
                
                # Create the HTML content file
                html_path = os.path.join(temp_dir, "dictionary.html")
                self._create_html_file(html_path, entries, title, source_lang, target_lang, 
                                      inflections=inflections or {})
                
                # Copy files to output directory
                output_dir = os.path.splitext(output_path)[0]
                os.makedirs(output_dir, exist_ok=True)
                
                shutil.copy(opf_path, os.path.join(output_dir, "dictionary.opf"))
                shutil.copy(html_path, os.path.join(output_dir, "dictionary.html"))
                
                # Optionally convert to MOBI if kindlegen is available
                if kindlegen_path and os.path.exists(kindlegen_path):
                    try:
                        self._convert_to_mobi(os.path.join(output_dir, "dictionary.opf"), kindlegen_path)
                        self.logger.info("MOBI file created successfully")
                    except Exception as e:
                        self.logger.warning(f"Failed to convert to MOBI: {e}")
                
                return output_dir
            
        except Exception as e:
            self.logger.error(f"Error exporting to Kindle format: {e}", exc_info=True)
            raise ExportError(f"Failed to export to Kindle format: {e}") from e

    def _create_opf_file(self, opf_path: str, title: str, source_lang: str, 
                         target_lang: str, author: str) -> None:
        """
        Create the OPF file for the Kindle dictionary.
        
        Args:
            opf_path: Path to save the OPF file.
            title: Title of the dictionary.
            source_lang: Source language code.
            target_lang: Target language code.
            author: Author name for the dictionary.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        opf_content = f"""<?xml version="1.0" encoding="utf-8"?>
<package unique-identifier="uid">
    <metadata>
        <dc-metadata xmlns:dc="http://purl.org/metadata/dublin_core" xmlns:oebpackage="http://openebook.org/namespaces/oeb-package/1.0/">
            <dc:Title>{title} ({source_lang}-{target_lang})</dc:Title>
            <dc:Language>{source_lang}</dc:Language>
            <dc:Identifier id="uid">{source_lang}-{target_lang}-dictionary-{timestamp}</dc:Identifier>
            <dc:Creator>{author}</dc:Creator>
            <dc:Rights>Copyright (c) {datetime.now().year}</dc:Rights>
            <dc:Type>dictionary</dc:Type>
            <dc:Subject BASICCode="REF008000">Dictionaries</dc:Subject>
            <dc:Publisher>Dictionary Writing System</dc:Publisher>
            <dc:Date>{timestamp}</dc:Date>
            <x-metadata>
                <DictionaryInLanguage>{source_lang}</DictionaryInLanguage>
                <DictionaryOutLanguage>{target_lang}</DictionaryOutLanguage>
                <DefaultLookupIndex>headword</DefaultLookupIndex>
            </x-metadata>
        </dc-metadata>
    </metadata>
    <manifest>
        <item id="dictionary" href="dictionary.html" media-type="text/x-oeb1-document"/>
    </manifest>
    <spine>
        <itemref idref="dictionary"/>
    </spine>
</package>
"""
        with open(opf_path, "w", encoding="utf-8") as f:
            f.write(opf_content)

    def _create_html_file(self, html_path: str, entries: List[Entry], title: str,
                         source_lang: str, target_lang: str,
                         inflections: Optional[Dict[str, List[str]]] = None) -> None:
        """
        Create the HTML content file for the Kindle dictionary.
        
        Args:
            html_path: Path to save the HTML file.
            entries: List of entries to include.
            title: Title of the dictionary.
            source_lang: Source language code.
            target_lang: Target language code.
            inflections: Dictionary of inflection forms.
        """
        if inflections is None:
            inflections = {}

        html_content = f"""
<!DOCTYPE html>
<html lang="{source_lang}">
<head>
    <meta charset="utf-8">
    <title>{title} ({source_lang}-{target_lang})</title>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .headword {{ font-weight: bold; font-size: 1.2em; }}
        .pronunciation {{ font-style: italic; color: #666; }}
        .pos {{ font-style: italic; color: #333; }}
        .sense {{ margin-left: 1em; }}
        .definition {{ margin-top: 0.5em; }}
        .example {{ font-style: italic; color: #444; margin-left: 1em; }}
    </style>
</head>
<body>
    <mbp:framesetstart name="dictionary"/>
"""
        
        # Add entries
        for entry in entries:
            headword = entry.lexical_unit.get(source_lang, "")
            if not headword:
                continue
            
            html_content += f'''
    <idx:entry name="{headword}" scriptable="yes" spell="yes">
        <div class="entry-container">
            <div class="headword">{headword}</div>
'''
            
            # Add inflections if available
            if inflections.get(headword):
                html_content += '''
            <idx:infl>
'''
                for infl in inflections[headword]:
                    html_content += f'                <idx:iform name="" value="{infl}"/>\n'
                html_content += '''
            </idx:infl>
'''
            
            # Add pronunciation
            if entry.pronunciations:
                for pronunciation in entry.pronunciations.values():
                    html_content += f'            <div class="pronunciation">[{pronunciation}]</div>\n'
            
            # Add senses
            for sense in entry.senses:
                html_content += '''
            <div class="sense">
'''
                # Add definition
                definition = ""
                if hasattr(sense, 'definitions') and sense.definitions:
                    definition = sense.definitions.get(target_lang, '')
                elif hasattr(sense, 'definition') and sense.definition:
                    definition = sense.definition
                if definition:
                    html_content += f'                <div class="definition">{definition}</div>\n'
                
                # Add examples
                examples = []
                if hasattr(sense, 'examples'):
                    examples = sense.examples
                for example in examples:
                    example_text = ""
                    if hasattr(example, 'form_text'):
                        example_text = example.form_text
                    elif hasattr(example, 'text'):
                        example_text = example.text
                    elif isinstance(example, dict):
                        example_text = example.get('form', {}).get(source_lang, '')
                    if example_text:
                        html_content += f'                <div class="example">{example_text}</div>\n'
                
                html_content += '''
            </div>
'''
            
            html_content += '''
        </div>
    </idx:entry>
'''
        
        html_content += """
</body>
</html>
"""
        
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _convert_to_mobi(self, opf_path: str, kindlegen_path: str) -> None:
        """
        Convert the dictionary to MOBI format using kindlegen.
        
        Args:
            opf_path: Path to the OPF file.
            kindlegen_path: Path to the kindlegen executable.
            
        Raises:
            ExportError: If the conversion fails.
        """
        try:
            subprocess.run([kindlegen_path, opf_path, "-c2", "-verbose"], check=True, capture_output=True, text=True)
            self.logger.info("Successfully converted to MOBI format")
        except FileNotFoundError:
            raise ExportError(f"kindlegen not found at {kindlegen_path}")
        except subprocess.CalledProcessError as e:
            self.logger.error(f"kindlegen failed with output:\n{e.stdout}\n{e.stderr}")
            raise ExportError(f"kindlegen conversion failed: {e.stderr}") from e
